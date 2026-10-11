# Neverclick 0.4.1 — Computer-vision pipeline reverse-engineering report

> **Artifact availability.** `neverclick.exe`, `ghidra/neverclick-decomp.c` (= `decomp` below) and the
> objdump disassembly dump `notes/scratch-vision/disasm.txt` (= `disasm` below) have been removed from this
> tree. Citations using those keys refer to removed files and cannot be re-opened; the analysis and
> reconstructed pipeline remain authoritative.

Scope: `extracted/app/neverclick.exe` (4.5 MB, MSVC x64, namespace `nvr`), static analysis only
(Ghidra decompilation `ghidra/neverclick-decomp.c` = `decomp` below, objdump disassembly
`notes/scratch-vision/disasm.txt` = `disasm`, PE parsing with pefile). Function addresses are
image VAs (`FUN_x @ 0x…`). Anything inferred rather than proven is marked **[INFERENCE]**.

---

## 1. Summary (TL;DR)

**There is no neural-network model.** Neverclick 0.4.1's "Neverclick Vision" is a hand-written
**classical computer-vision pipeline running as D3D11 compute shaders**, plus a CPU post-pass:

1. **Capture** per monitor: DXGI Desktop Duplication (primary) or GDI `BitBlt` (fallback) →
   BGRA8 `ID3D11Texture2D`, per-monitor rotation correction (`TextureOps::Rotate`).
2. **GPU edge pipeline** (7 embedded HLSL compute shaders, all sharing cbuffer
   `PipelineConstants`): downscale → contrast → Sobel → non-max suppression → threshold →
   dilate → optional boolean downsample. Debug build can dump every stage as BMP.
3. **CPU connected-component labeling** (union-find, PPL-parallel) over the boolean mask →
   bounding boxes, area/size filtering, optional `removeHallucinations` corner-color filter.
4. A separate **GPU template matcher** (`GpuTemplateMatcher::searchAll`, 8th shader, cbuffer
   `TemplateMatchConstants`) locates **window/taskbar/desktop icons** in the same captures via
   12-pixel probe SAD matching — used for icon-click hints.
5. **onnxruntime.dll is shipped but 100 % inert.** `OrtGetApiBase` is imported by ordinal and
   called exactly once from a CRT static initializer; the returned `OrtApi*` global
   (`0x1402e0478`) is **never read anywhere in the binary**. No session, tensor, or ORT API
   call exists. There is no `.onnx` file, no model blob in resources, no model file loaded at
   runtime. The author's "small model" phrasing refers to this classical pipeline; the
   `detectionModel` config (`Balanced`/`Narrow`/`UltraNarrow`/`Wide`) selects **dilation-radius
   presets**, not NN weights.
6. **Cadence**: purely event-driven — global `WH_KEYBOARD_LL` hotkey hook → main wndproc →
   tool activation → session driver → `HintCoordinator::run` → `VisionProvider::run`, one
   capture→detect→return pass per activation. No vision timer, no polling loop.

`zlib1.dll` is used only for gzip'd `hotkey-config.json.gz` (save+load) and a base64→gunzip
image loader; the zlib-looking byte sequences in `.rdata`/`.rsrc` are ordinary PNG IDAT chunks
of icon PNGs (verified by decompression + PNG structure parse). The previously-flagged
`extracted/model-candidates/rc_1033_1033_270376.bin` is the **256×256 32-bpp DIB of ICON
resource id 1** (size 270,376 matches the resource directory entry exactly) — not a model.

Files extracted by this work: 8 compiled DXBC shaders → `notes/scratch-vision/dxbc/`
(the actual "model" artifacts; see §3). **No `extracted/model/` directory was created because no
model file exists in any shipped binary.**

---

## 2. Data flow (end-to-end)

```mermaid
flowchart TD
    A[Global WH_KEYBOARD_LL hook\nFUN_1400235c0] -->|WM 0x501| B[Main wndproc FUN_1400612c0]
    B --> C[ActiveToolManager::arm FUN_1400e7f80\n-> invoke closure -> msg 0x50c]
    C --> D[Session driver FUN_1401e1620\n-> HintCoordinator::run FUN_1401f2510]
    D -->|provider dispatch FUN_1401e47c0\ncase 8 = FNV("VisionProvider")| E[VisionProvider::run FUN_1401f5f70]
    E -->|FOV rect + detection params| F[FUN_140116020 -> FUN_140118360\nselect sources intersecting FOV+10px]
    F --> G[FUN_1401160e0 per monitor]
    G --> H{source+0xa0?}
    H -->|0| I[DDA capture FUN_140129ec0\nAcquireNextFrame, ACCESS_LOST recovery]
    H -->|nonzero| J[GDI BitBlt capture FUN_140034280\nGetDC(NULL), SRCCOPY, BGRA8 upload]
    I --> K[TextureOps::Rotate FUN_14012f5e0\nper-monitor DXGI_MODE_ROTATION]
    J --> K
    K --> L[7 compute passes FUN_1401160e0\ndownscale/contrast/sobel/nms/threshold/dilate/bool_ds]
    L --> M[Staging readback:\nbool mask label_w x label_h\nBGRA color scaled_w x scaled_h]
    M --> N[CPU union-find labeling FUN_14012e510\narea filter 3..200000 px]
    N --> O[removeHallucinations FUN_14012e060\ncorner-color filter, probes {0,2,5,10}]
    G -->|same step| P[GpuTemplateMatcher::searchAll FUN_1401311c0\nicon needles, 12 probes SAD]
    O --> E
    P --> E
    E -->|HintProviderResult boxes| D
```

Per-invocation detail inside `VisionProvider::run(FovMode)` (`FUN_1401f5f70 @ 0x1401f5f70`,
decomp 414709–415648):

1. **FOV resolution** (414720–414975): `GetForegroundWindow`; if it is a system/shell window
   (`FUN_140039640`: `GetShellWindow`/`GetDesktopWindow`, class `Shell_TrayWnd`,
   `Shell_SecondaryTrayWnd`, `Windows.UI.Core.CoreWindow`, `Progman`, `WorkerW`) the effective
   mode is forced to 2 (AllMonitors). Mode 0 (Window): FOV = DWM extended-frame rect of the
   foreground window (`FUN_14003d330` = `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)`)
   after the "relevant window" predicate `FUN_1401f5ae0` (visible, not cloaked — attr 0xd,
   not iconic, frame area ≥ 2 px, non-empty title); fallback to stored rect. Mode 1 (Monitor):
   FOV = rect of monitor containing the foreground window (`FUN_140102210` =
   `MonitorFromWindow(MONITOR_DEFAULTTONEAREST)`). Mode 2 (AllMonitors): full virtual-desktop
   rect.
2. **Params**: `FUN_1401f5ea0 @ 0x1401f5ea0` (414662) expands the 8-byte vision config
   `{detectionModel:int, removeHallucinations:byte}` (read from `config+0x170`, or a live
   override at `provider+0x38` when `provider+0x40` is set) into a **15-dword parameter blob**
   (exact contents in §4.2).
3. `FUN_140116020 @ 0x140116020` (232904) → `FUN_140118360 @ 0x140118360` (234395) selects the
   capture sources whose desktop rect (`source+0xe8..0xf4`) intersects the FOV rect grown by
   **10 px**, then `FUN_1401160e0 @ 0x1401160e0` (232958–233831) runs the per-monitor pipeline.
4. Boxes returned as 0x50-byte records `{capture-rect, offsets, float scale, vector<Box>}`;
   `run` translates boxes from capture-local to screen coordinates, applies window-mode
   filtering, the window-edge hallucination filter, the min-size filter, clamps to the capture
   rect, and assembles `HintProviderResult`.

---

## 3. Model findings — there is no model; the "weights" are HLSL shaders

### 3.1 ONNX Runtime is dead code (proven)

* `neverclick.exe` imports `onnxruntime.dll` **by ordinal 1 only** (`OrtGetApiBase`), IAT slot
  `0x140236440` (`objdump -p`, import table).
* `FUN_140005050 @ 0x140005050` (decomp 3139–3152) calls `OrtGetApiBase()`, then
  `GetApi(0x13)` (API version 19) and stores the result to global `_DAT_1402e0478`:
  `puVar1 = (undefined8 *)OrtGetApiBase(); _DAT_1402e0478 = (*(code *)*puVar1)(0x13);`
  disasm 4604–4611 (`mov %rax,0x2db409(%rip) # 0x1402e0478`).
* **That global has exactly one reference in the entire image — the write.** Verified three
  ways: (a) whole-decompilation needle search over all 467,283 lines (split into <4 MB chunks),
  (b) raw byte scan of every PE section for rip-relative displacements resolving to
  `0x1402e0478` (imm lengths 0/1/2/4/8) — only the write instruction at `0x14000506b` matched,
  (c) absolute 8/4-byte pointer search — zero hits. Therefore no ORT function can ever be
  invoked (every ORT C-API call must dereference the `OrtApi*`).
* `FUN_140005050` has **no code callers**; it is the first entry of the CRT `.CRT$XCU`
  initializer array (pointer at file 0x235558; array spans VA `0x1402364d0–0x1402366f0`, walked
  by `_initterm` in `FUN_1401ff130 @ 0x1401ff130`, decomp part_03:60826). Sibling initializers:
  `RegisterWindowMessageW(L"TaskbarCreated")` etc. (decomp 3128–3300).
* Full-decomp grep: **zero** occurrences of `CreateSession`, `SessionOptions`, `RunOptions`,
  `CreateTensor`, `GetTensorMutableData`, `SetIntraOpNumThreads`, `OrtEnv`,
  `ExecutionProvider`, `CPUExecutionProvider`, `CUDAExecutionProvider`. No dynamic loading
  either (no `GetProcAddress("OrtGetApiBase")`; the string does not exist).

### 3.2 No model bytes anywhere

* No `.onnx`/weights/checkpoint filename in any ASCII or wide string; no magic-scan hit
  (`ir_version`, `ai.onnx`, conv2d/YOLO/nanodet patterns) in any of the four EXEs.
* PE resource directory of neverclick.exe (pefile): IMAGE 300, TEXTFILE 350, TEXTINCLUDE×3,
  **WAV 301/302** (notification sounds), **ICON ×30** (the app icon pyramid), MENU, STRING,
  **GROUP_ICON 104/105/201/202/203**, VERSION, MANIFEST. No RCDATA blobs, no data resources.
* `extracted/model-candidates/rc_1033_1033_270376.bin` = **ICON id 1** (resource dir size
  270,376 = file size exactly): raw 32-bpp DIB, `biSize=40, biWidth=256`,
  `40 + 256×264×4 = 270376`. Not a model; low-entropy gradient runs confirm image data.
* The two "zlib" streams at file 0x3feab9 / 0x41d3e9 (`.rsrc`) are **PNG IDAT chunks**: each is
  41 bytes after a `\x89PNG` signature, IHDR = 256×256, 8-bit RGBA (colortype 6); decompressed
  payload shows sparse glyph-like nonzero islands — these are icon PNGs (GROUP_ICON 201/202).
  The `.rdata` `78 da` sequences at ~0x27dbf0/0x27e2d8 are likewise interior to PE structures,
  and the binary's only `inflate` call site is the generic gunzip helper
  `FUN_140099150 @ 0x140099150` (decomp 130180–130300, `inflateInit2_("1.3.1", windowBits
  configurable)`) used solely by (a) `hotkey-config.json.gz` load and (b) a
  base64→gunzip→raw-BGRA image loader (validates `size == w*h*4`, 90,000-px cap; deflate
  counterpart = config save path). zlib is config/UX plumbing, not vision.

### 3.3 What the "model" actually is: 8 embedded DXBC compute shaders

Created by `FUN_14012c730 @ 0x14012c730` (edge pack, 7 shaders via `FUN_14012ced0`,
"Failed to create compute shader.") and `FUN_140130690 @ 0x140130690`
(`CreateComputeShader(vtable+0x90, &DAT_140272f50, 0x4120)` + 0x90-byte CB), from
`FUN_140127500 @ 0x140127500` during vision-runtime build; per-monitor failure is tolerated
(`FUN_140127e70 @ 0x140127e70`: "GPU template matcher failed to initialize on monitor '{}': {}.
Template search will be unavailable there.").

Extracted & magic-verified (`DXBC`) to `notes/scratch-vision/dxbc/` (file offset = VA −
`0x140001000` for these `.rdata` blobs):

| file | VA | size | reflection (cbuffer / SRVs) |
|---|---|---|---|
| `edge_1_140272470.dxbc` | 0x140272470 | 0xad0 | PipelineConstants; `g_input`, `g_output` |
| `edge_2_140271b50.dxbc` | 0x140271b50 | 0x91c | PipelineConstants; `g_inout` (in-place ⇒ contrast) |
| `edge_3_1402707a0.dxbc` | 0x1402707a0 | 0x13a8 | PipelineConstants; `g_input` |
| `edge_4_14026fd10.dxbc` | 0x14026fd10 | 0xa8c | PipelineConstants; `g_input` |
| `edge_5_14026f520.dxbc` | 0x14026f520 | 0x7f0 | PipelineConstants; `g_input` |
| `edge_6_14026e140.dxbc` | 0x14026e140 | 0x9e0 | PipelineConstants; `g_input` |
| `edge_7_gated_14026eb20.dxbc` | 0x14026eb20 | 0x9f4 | PipelineConstants; gated `if (1 < *param_1)` |
| `templatematch_140272f50.dxbc` | 0x140272f50 | 0x4120 | TemplateMatchConstants; `g_haystack`, `g_needle`, `g_group_best` |

All 7 edge shaders share one cbuffer `PipelineConstants` (HLSL Compiler "Microsoft", RD11)
with fields, in declaration order:
`g_width, g_height (uint); g_dpi_scale (float); g_edge_threshold (float);
g_scaled_width, g_scaled_height (uint); g_coord_scale (float); g_pad0;
g_label_width, g_label_height (uint); g_min_blob_area (uint); g_pad1;
g_dilate_left, g_dilate_right, g_dilate_up, g_dilate_down (int);
g_contrast, g_contrast_midpoint (float); g_pad2, g_pad3`.

Individual blob→stage assignment within the 7-shader pack is **[INFERENCE]** (creation order +
`g_inout` hint ⇒ edge_2 = contrast; rest mapped by stage count/order below).

---

## 4. Algorithms & constants

### 4.1 Capture (per monitor)

* **Backend selection**: per capture-source byte `source+0xa0` (dispatch in `FUN_1401160e0`,
  decomp 233148–233160): `0` ⇒ DDA, nonzero ⇒ GDI, `-1` invalid (abort `FUN_140040630`).
  `rebuildGraphicsPipeline` (strings "legacy"/"duplication", "  DDA OK on '{}' ({})." /
  "  DDA FAIL on '{}': {}") chooses per monitor; `FUN_140118720 @ 0x140118720` (234577) marks
  reinit needed when a DDA source dies (`source+0x98 == 0`).
* **DDA**: creation `FUN_140111910 @ 0x140111910` (228989): `IDXGIOutput1` QI →
  `DuplicateOutput` (vtable +0xb0); HRESULT `0x887A0022` → "There are too many applications
  capturing the screen." Acquisition `FUN_140129ec0 @ 0x140129ec0` (249598) +
  `FUN_14012a8d0 @ 0x14012a8d0` (250162): `AcquireNextFrame` (vtable +0x40) with **0-ms
  timeout, busy-retry ≤ 1 s**; on `DXGI_ERROR_ACCESS_LOST (0x887A0026)` recreate duplication;
  on `WAIT_TIMEOUT (0x887A0027)` retry; >2 failures ⇒ "DDA on monitor '{}' never delivered a
  frame after {} attempts; marking dead." (`source+0x99/+0x9c`). Frame is copied into an owned
  `CreateTexture2D` texture (BindFlags 0x28 = SHADER_RESOURCE|RENDER_TARGET).
* **GDI fallback**: `FUN_140034280 @ 0x140034280` (45669): `GetDC(NULL)` → `BitBlt` SRCCOPY
  (`0xcc0020`) → memory DC → `CreateTexture2D` **`DXGI_FORMAT_B8G8R8A8_UNORM` (0x57)**, then
  upload. There is **no PrintWindow** and **no per-HWND capture**: window mode crops the
  desktop capture to the window's screen-space FOV rect (clamped to each source's desktop rect
  at `source+0xe8..0xf4`, decomp 233112–233144).
* **Multi-monitor**: `FUN_140110730 @ 0x140110730` (228139) enumerates DXGI adapters skipping
  software adapters (`VendorId 0x1414 / DeviceId 0x8c`), `EnumOutputs`, per-output `GetDesc`;
  one DDA duplication per monitor; 0x1a8-byte display entries with valid flag `+0x1a0`.
  GDI helpers: `FUN_14003e2b0` (`EnumDisplayMonitors`), `FUN_14003e450`
  (`GetMonitorInfoW`, cbSize 0x68), `FUN_14003e600` (`GetDpiForMonitor(MDT_EFFECTIVE_DPI)`).
* **DPI**: affects window-rect resolution only, not pixel capture — `FUN_14003df10 @
  0x14003df10` (54288) rescales rects by systemDPI/monitorDPI under
  `SetThreadDpiAwarenessContext` save/restore; `scale = dpi/96.0`.
* **Rotation**: `nvr::win::TextureOps::Rotate` = `FUN_14012f5e0 @ 0x14012f5e0` (253952; proven
  by adjacent lambda RTTI getter `FUN_14012f830`): rotation <2 (UNSPECIFIED/IDENTITY) ⇒ AddRef
  input; 2/3/4 ⇒ 90°/180°/270° — rotated via center-offset cos/sin matrix render
  (`FUN_14012f1a0`). Called once per source in `FUN_1401160e0` (233176) with
  `source+0xfc` (DDA, from output desc) or forced IDENTITY (GDI). Rotated texture is the
  stage-0 input.

### 4.2 Detection-parameter blob (`FUN_1401f5ea0`, 15 dwords)

Defaults (Balanced) and per-model overrides (`iVar1 = detectionModel`):

| idx | field | Balanced | Narrow(1) | UltraNarrow(2) | Wide(3) |
|---|---|---|---|---|---|
| [0] | g_edge_threshold (float) | 2.0 | 2.0 | 2.0 | 2.0 |
| [1] | g_dilate_left | 2 | **1** | **1** | **3** |
| [2] | g_dilate_right | 2 | **1** | **0** | **3** |
| [3] | g_dilate_up | 1 | 1 | 1 | 1 |
| [4] | g_dilate_down | 1 | 1 | **0** | 1 |
| [5] | g_min_blob_area / CPU min area (px) | 3 | 3 | 3 | 3 |
| [6] | CPU max blob area (px²) | 200000 | " | " | " |
| [7] (byte 0) | **removeHallucinations flag** (from `config+0x174`) | cfg | cfg | cfg | cfg |
| [8] | max distinct corner colors (halluc filter) | 3 | 3 | 3 | 3 |
| [9..12] | corner probe insets (px) | 0, 2, 5, 10 | " | " | " |
| [13] | g_contrast (float) | 2.0 | 2.0 | 2.0 | 2.0 |
| [14] | g_contrast_midpoint (float) | 0.5 | 0.5 | 0.5 | 0.5 |

So **`detectionModel` = dilation-radius preset**: UltraNarrow dilates only left/up by 1
(tightest boxes ⇒ most hints), Wide dilates ±3 (loosest). This blob is uploaded into the
19-dword `PipelineConstants` CB (decomp 233263–233281):

```
CB[0]=g_width=capture w          CB[10]=g_min_blob_area=params[5]=3
CB[1]=g_height=capture h         CB[11]=pad=0
CB[2]=g_dpi_scale (float)        CB[12..15]=g_dilate L,R,U,D = params[1..4]
CB[3]=g_edge_threshold=params[0]=2.0f   CB[16]=g_contrast=params[13]=2.0f
CB[4]=g_scaled_width             CB[17]=g_contrast_midpoint=params[14]=0.5f
CB[5]=g_scaled_height            CB[18,19]=pad2,pad3=0
CB[6]=g_coord_scale (float)
CB[7]=0 ; CB[8]=g_label_width ; CB[9]=g_label_height
```

### 4.3 GPU stage chain (`FUN_1401160e0`, 232958–233831)

All dispatches: `Dispatch(ceil(w/16), ceil(h/16), 1)` via context vtable `+0x148`; per-stage
pattern `CSSetShader(+0x228)` / `CSSetConstantBuffers(+0x238)` / `CSSetShaderResources(+0x218)`
/ `CSSetUnorderedAccessViews(+0x220)` / Dispatch / unbind (`FUN_14012db40`). Stage order and
gates (debug dumps exist in the shipping binary, written only when a debug path is set at
`device+0x2b`):

| # | stage (dump name) | shader slot | gate | I/O |
|---|---|---|---|---|
| 0 | capture (`stage0_capture.bmp`) | — | always | rotated BGRA texture |
| 1 | downscale (`stage1_downscale.bmp`) | `device[0x35]` | always | capture → scaled color (scaled_w×scaled_h, BGRA8) |
| 2 | contrast (`stage2_contrast.bmp`) | `device[0x36]` | `g_contrast != 1.0` (always, =2.0) | in-place (`g_inout` shader) |
| 3 | Sobel (`stage4a_sobel.bmp`) | `device[0x37]` | always | → edge magnitude |
| 4 | NMS (`stage4b_nms.bmp`) | `device[0x38]` | always | thin edges |
| 5 | threshold (`stage4c_threshold.bmp`) | `device[0x39]` | always | `g_edge_threshold=2.0` → boolean |
| 6 | dilate (`stage5_dilate.bmp`) | `device[0x3a]` | any dilate param ≥ 1 | L/R/U/D radii from CB[12..15] |
| 7 | bool downsample (`stage6_bool_ds.bmp`) | `device[0x3b]` | `*(int*)(device+0x140) ≥ 2` | halved boolean mask → label_w×label_h |

Readbacks (`ID3D11DeviceContext::Map` slot `+0x70`, Unmap `+0x78`):
* **bool mask** staging `device[0x4e]` ← CopyResource(`+0x178`) of final bool texture; Map
  READ; row-by-row memcpy to CPU at `device[0x52]`, stride `*(u32*)(device+0x17c)`
  (= label_w), rows `device[0x30]` (= label_h). Errors: "Failed to map bool staging texture."
* **color image** staging `device[0x4f]` ← downscaled color `device[0x3c]`; memcpy rows =
  `*(u32*)(device+0x174) << 2` bytes (BGRA8), rows `device[0x2f]`, dst ptr `device[0x57]`,
  dst stride `device[0x56]` (= scaled_w×4). Error: "Failed to map color staging texture."
* A PPL `parallel_for` then runs per-monitor labeling (`FUN_1401179f0 @ 0x1401179f0`,
  233831), producing 0x50-byte records `{capture rect(16B), offsets(16B), rect(16B),
  {int, float scale}(8B), vector<Box>(24B)}`.

### 4.4 CPU connected components + box extraction

* `FUN_14012e510 @ 0x14012e510` (253106): seeds **4-connected** union-find over the boolean
  mask: for each set pixel, `FUN_140132cb0` (union with path compression, bbox merge via
  `FUN_140132db0`) with right and lower neighbors; optional FOV-clip (mask rect =
  `floor(fov / g_coord_scale)`… `ceil`, clamped to mask dims). Label state at
  `labeler+0x148` (parents), `+0x150` (mask), `+0x30` (bbox table, 16 B/px:
  `{x0,y0,x1,y1}`).
* Row init/collection is PPL-parallel (`FUN_140133530`, worker `FUN_140134660` writes
  per-pixel bbox `{x,y,x,y}`; `FUN_140132e10` collects components with **pixel count > 10** —
  minimum component size = 11 mask pixels).
* `FUN_14012dce0 @ 0x14012dce0` (252697): for each component bbox (mask space):
  * **area filter**: keep iff `params[5] ≤ area ≤ params[6]` i.e. **3 … 200 000 px**;
  * **coordinate transform** to capture space:
    `x0' = x0*scale + params[1]*scale2`, `y0' = y0*scale + params[3]*scale2`,
    `x1' = x1*scale − params[2]*scale2`, `y1' = y1*scale − params[4]*scale2`
    (`scale = labeler+0x44`, `scale2 = labeler+0x30`; the dilate radii are subtracted back so
    the box recovers the pre-dilation extent) **[INFERENCE on exact float identities]**;
  * optional final containment test against the FOV rect (`param_5[4]` flag).
* **`removeHallucinations` filter** = `FUN_14012e060 @ 0x14012e060` (252856), runs iff
  `params[7] byte0 ≠ 0` (i.e. the config flag): for each box, sample the **4 corner pixels in
  the BGRA color image** (`labeler+0x170` stride, `+0x178` ptr) at probe insets
  **{0, 2, 5, 10} px** (`params[9..12]`); keep the box at the first inset where the number of
  **distinct corner RGB triples < 3** (`params[8]`); boxes whose corners stay multi-colored at
  every inset are discarded as hallucinations.

### 4.5 Post-processing in `VisionProvider::run` (415028–415560)

1. Per record: translate boxes by capture origin `(+8,+0xc)` (capture-local → screen).
2. **Window-mode filter** (window mode + relevant foreground window): keep only boxes whose
   four corners all lie inside one of the foreground-window rects
   (`FUN_1400fad40`-collected list, 415127–415237).
3. **Window-edge hallucination filter** (415240–415340): if a box's **center** is inside the
   window frame rect but any corner is outside rect±3 px, the box is dropped (straddling boxes
   at the window border).
4. **Min-size filter** (415370–415400): with `s = record+0x34` float (mask→screen scale
   **[INFERENCE]**), keep iff
   `(height < 3 AND 9 ≤ width < 20)` **or**
   `(area ≥ 30·s AND width ≥ s AND height ≥ s)`
   (the `w−9U < 11` unsigned test rejects sub-9-px widths);
   i.e. drop medium boxes that are smaller than ~30 scale-units of area or sub-scale in either
   dimension. (Tiny horizontal slivers h≤2 with 9 ≤ w ≤ 19 — e.g. underlines/separators —
   pass through.)
5. **Clamp** to capture rect inset by 2 px (left/top) and 3 px (right/bottom).
6. Merge into `HintProviderResult` (`FUN_1401f78a0`, `FUN_1401f7b60`, `FUN_1401f7ff0`);
   per-record results are appended by `FUN_1401f7570`; provider cache is keyed by FNV-1a of
   the `{detectionModel, removeHallucinations}` pair (`FUN_1401f73f0`/`FUN_1401f7490`,
   constant `0x6a26b777ee4da3d0`), so param changes invalidate the coordinator cache.

Box format throughout: 16-byte `{int32 x0, y0, x1, y1}` (top-left/bottom-right, screen
physical pixels).

### 4.6 GPU template matcher (icons)

`nvr::detail::GpuTemplateMatcher::searchAll` = `FUN_1401311c0 @ 0x1401311c0` (255216–255721;
RTTI getter `FUN_140132380`), readback lambda `FUN_140132390 @ 0x140132390` (255733+).

* Haystack = monitor capture texture, must be `B8G8R8A8_UNORM` (else "Template match haystack
  must be DXGI_FORMAT_B8G8R8A8_UNORM."). Needle = `CpuImage`
  `{u32 width@0, height@4, stride@8, const u8* pixels@16}` (BGRA, `y*stride + x*4`).
* `TemplateMatchParams` = `{double fraction @0 (= config% / 100.0), u32 tolerance @8 (caller
  passes 0x18 = 24)}`.
* Probes: `FUN_14012fdb0 @ 0x14012fdb0` (254303) samples **12 fixed relative points** of the
  needle — x ∈ {0.05,0.2,0.35,0.5,0.65,0.8,0.95}·w, y ∈ {0.05,0.25,0.5,0.75,0.95}·h
  (grid+crosshair) — packed as `{int32 x,y; u8 B,G,R,A}` ×12 = the CB `g_probes` (144-byte
  cbuffer, matches `ByteWidth=0x90` in `FUN_140130690`).
* Match criterion: per-candidate **SAD over the 12 probes** (max error 3·255 = 765 per pixel);
  budget = `needleW·765·needleH·(1−toleranceFrac)`; candidates tiled into 16×16 thread groups
  (group count clamped ≤ 0x1000); group-best `{errorSum, linearIdx}` buffer copied back and
  filtered `errorSum ≤ maxErr·(1−tolerance)`; **overlap-based NMS**; box =
  `{x, y, x+needleW, y+needleH}`; `score = 1 − errorSum/(needleW·765·needleH)`.
* Caller `FUN_140188a00 @ 0x140188a00` (327181–328289): per monitor ("Monitor not in vision
  runtime." / "Monitor has no GPU template matcher."), haystack = fresh monitor capture
  (`FUN_140117c10` → `FUN_140131040`), iterates **40-byte template records** from
  `FUN_1401e34b0`, one `searchAll` per template per monitor. Template needles are cached
  **window-icon bitmaps** keyed by FNV-1a of the executable path (`FUN_1401446e0` region,
  "Failed to create bitmap from window icon: {}"); desktop/taskbar icon geometry is kept fresh
  via UIA WinEvent refresh (0x8000–0x800b hooks → refreshTaskbarIcons / refreshDesktopIcons).
  `FUN_140188a00` also drives the hint session (`FUN_1401e1620` → `HintCoordinator::run` core
  `FUN_1401f2510` → `provider->run`), i.e. template matching and edge detection run in the
  same activation. **[INFERENCE]** exact merge of icon-template results into the hint list.

---

## 5. Key symbols

| Symbol (RTTI) | Address | Role |
|---|---|---|
| `VisionProvider::run(FovMode)` | `FUN_1401f5f70 @ 0x1401f5f70` | one full capture→detect pass (decomp 414709–415648; proven by lambda RTTI getters `FUN_1401f7f50`/`FUN_1401f8010` for `??run@VisionProvider@nvr@@UEAA?AUHintProviderResult@3@W4FovMode@3@@Z@`) |
| capture pipeline | `FUN_140116020 @ 0x140116020` → `FUN_140118360` → `FUN_1401160e0 @ 0x1401160e0` | source select + 7 GPU stages + readback + CPU labeling orchestration |
| DDA capture | `FUN_140129ec0 @ 0x140129ec0`, `FUN_14012a8d0 @ 0x14012a8d0`, dup create `FUN_140111910 @ 0x140111910` | Desktop Duplication w/ recovery |
| GDI capture | `FUN_140034280 @ 0x140034280` | BitBlt fallback |
| `TextureOps::Rotate` | `FUN_14012f5e0 @ 0x14012f5e0` | per-monitor rotation |
| monitor enumeration | `FUN_140110730 @ 0x140110730` | DXGI adapters/outputs |
| GPU init | `FUN_14004f850 @ 0x14004f850` (CreateDXGIFactory1/D3D11CreateDevice), `FUN_140127500 @ 0x140127500` (shader pack) | |
| `GpuTemplateMatcher::searchAll` | `FUN_1401311c0 @ 0x1401311c0` (+ lambda `FUN_140132390`, RTTI getter `FUN_140132380`) | icon SAD matcher |
| CC labeling | `FUN_14012e510 @ 0x14012e510`, `FUN_14012dce0 @ 0x14012dce0`, union-find `FUN_140132cb0 @ 0x140132cb0` | mask → boxes |
| `removeHallucinations` filter | `FUN_14012e060 @ 0x14012e060` | corner-color filter |
| params builder | `FUN_1401f5ea0 @ 0x1401f5ea0` | config → 15-dword blob |
| provider dispatch | `FUN_14019a910 @ 0x14019a910` / `FUN_1401e47c0 @ 0x1401e47c0` (case 8 = FNV("VisionProvider")) | Vision/Grid/Clairvoyance selection |
| ORT bootstrap (dead) | `FUN_140005050 @ 0x140005050` → global `0x1402e0478` | never-read `OrtApi*` |
| keyboard hook | `KeyboardHook::hook FUN_1400235c0` (`SetWindowsHookExW(0xd,…)`), callback `ToolActivationHookCallback` `FUN_140098230` | activation trigger |

---

## 6. Config touchpoints (JSON, parsed by `FUN_14015c300 @ 0x14015c300`, ~289698)

| key | struct field | consumer |
|---|---|---|
| `vision.detectionModel` | `config+0x170` int; enum table VA `0x14027f540`: 0=`Balanced`(default), 1=`Narrow`, 2=`UltraNarrow`, 3=`Wide` | `FUN_1401f5ea0` → dilation-radius preset + FNV cache key |
| `vision.removeHallucinations` | `config+0x174` byte | `params[7]` → gates `FUN_14012e060` |
| `vision.enablePerfectDesktopAndTaskbarIconDetection` | parsed ~141071 (`PTR_s_enablePerfect…`), field byte ~`+0x3d` **[INFERENCE]** | gates template matcher path **[INFERENCE]** (parse+serialize sites only) |
| `fovMode` | config+0xfa8 (live); enum table `0x14027f780`: Window/Monitor/AllMonitors, default AllMonitors **[INFERENCE on int mapping]** | `VisionProvider::run` param, session drivers |
| internal key `VisionModel` | `FUN_140172220 @ 0x140172220` (compares `"VisionModel"` qword) | runtime vision-config dispatch, sibling `ClairvoyanceModel` |

Related: `g_edge_threshold`, `g_min_blob_area`, dilate radii, contrast, probe insets — all
**fixed constants** (§4.2), not user-configurable; only the dilation preset and hallucination
toggle are user-visible.

---

## 7. Gaps / undetermined

1. **Blob→stage order inside the 7-shader edge pack** not individually verified (only count +
   gating match; `edge_2` has `g_inout` ⇒ contrast). DXBC disassembly (SHEX) of the
   extracted blobs would settle it — blobs are in `notes/scratch-vision/dxbc/`.
2. `enablePerfectDesktopAndTaskbarIconDetection`'s runtime gate branch not located (parse and
   serialize sites only).
3. No textual callers for `FUN_140188a00` / session-driver closures (`FUN_1401e6390`,
   `FUN_1401e65f0`, `FUN_14019b5f0`) — invoked via `.rdata` function-pointer tables; the exact
   `0x50c` overlay-message handler edge is untraced.
4. Exact merge of `TemplateMatchResult`s into the hint box list (icon hints) not traced end-to-end.
5. `CpuImage` fields at +12/+24 (format/end-ptr) unproven; exact float identities of the
   mask→screen scale pair (`labeler+0x30` vs `+0x44`) [INFERENCE].
6. FovMode int→name mapping inferred from control flow, not from a decoded enum table row.
7. GDI-path upload vtable slot `+0x180` semantics (assumed UpdateSubresource-style upload) not
   formally identified.
8. `searchAll`'s 8-arg decomp signature vs 5-arg RTTI name (stack args truncated by Ghidra) —
   bindings at call sites [INFERENCE].

---

## 8. Spec-ready statements

1. On activation, Neverclick captures each monitor via DXGI Desktop Duplication
   (`AcquireNextFrame`, 0-ms busy retry ≤1 s, ACCESS_LOST re-duplication, dead-marking after
   >2 failures); if DDA is unavailable for a monitor it falls back to
   `GetDC(NULL)`+`BitBlt(SRCCOPY)` into a `B8G8R8A8_UNORM` D3D11 texture. No PrintWindow and no
   per-HWND capture exist — window mode is a screen-coordinate crop of the desktop capture.
2. Each captured texture is rotated to its monitor's `DXGI_MODE_ROTATION` (90/180/270 via
   matrix render), then processed by 7 compute shaders (16×16 thread groups) sharing one
   80-byte `PipelineConstants` cbuffer: downscale (BGRA8), contrast (×2.0 about midpoint 0.5),
   Sobel, non-max suppression, threshold (edge threshold 2.0), anisotropic dilation
   (L/R/U/D from the `detectionModel` preset: Balanced 2/2/1/1, Narrow 1/1/1/1, UltraNarrow
   1/0/1/0, Wide 3/3/1/1), and an optional boolean downsample.
3. The final boolean mask and the downscaled BGRA image are copied to CPU staging buffers;
   CPU union-find labeling (4-connected, PPL row-parallel, components ≤10 px discarded,
   area window 3…200 000 px) produces 16-byte `{x0,y0,x1,y1}` boxes, dilate radii subtracted
   back, mapped to screen pixels.
4. If `removeHallucinations` is enabled, a box is kept only if, at one of the corner-probe
   insets {0,2,5,10} px, its four color-image corner pixels contain fewer than 3 distinct RGB
   values.
5. `VisionProvider::run` then (window mode) keeps only boxes fully inside the foreground
   window's DWM frame rect, drops boxes centered inside it that cross its border ±3 px, drops
   boxes failing `area ≥ 30·s ∧ w ≥ s ∧ h ≥ s` unless they are tiny slivers
   (h ≤ 2 ∧ 9 ≤ w ≤ 19), where s = mask scale, and clamps survivors to the capture rect inset
   by 2/3 px.
6. Independently, a 12-probe SAD GPU template matcher (`TemplateMatchConstants`, budget
   `w·765·h·(1−tolerance)`, tolerance dword 24, 16×16 group tiling ≤ 0x1000 groups, overlap
   NMS, score `1−err/max`) locates cached window/taskbar/desktop icon bitmaps in the same
   per-monitor captures; it is initialized per monitor and degrades gracefully per monitor.
7. Detection is strictly event-driven: a single `WH_KEYBOARD_LL` hook matches activation
   chords → posted message → `ActiveToolManager::arm` → session driver →
   `HintCoordinator::run` → `VisionProvider::run(FovMode)`; FovMode ∈ {Window, Monitor,
   AllMonitors} with shell-window foregrounds forcing AllMonitors. There is no vision
   `SetTimer`, no polling loop, and `VisionProvider::run` performs exactly one
   capture→detect→return pass per invocation.
8. ONNX Runtime is imported (`onnxruntime.dll`, ordinal 1) but provably inert: a CRT
   initializer calls `OrtGetApiBase()->GetApi(19)` once and stores the pointer to a global
   that is never read; no ORT function, model file, or model blob exists in the binary. The
   config enum `Balanced|Narrow|UltraNarrow|Wide` (`detectionModel`) selects dilation-radius
   parameter presets of the classical shader pipeline, and the entire CV implementation is
   self-contained (8 embedded DXBC shaders + CPU labeling), consistent with the author's
   "no third-party CV libraries" claim.
