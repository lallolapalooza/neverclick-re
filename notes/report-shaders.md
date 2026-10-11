# Neverclick 0.4.1 — Shader / vision-kernel reference

> **Artifact availability.** The DXBC blobs (`notes/scratch-vision/dxbc/`), their disassembly
> (`notes/scratch-vision/hlsl/*.asm`) and `ghidra/neverclick-decomp.c` have been removed from this tree; the
> reconstructed `ref_edge*.hlsl` equivalents remain under `notes/scratch-vision/hlsl/`. The math below is
> the retained record.

Scope: the 8 embedded D3D11 **compute shaders of `neverclick.exe`** — the actual "computer vision model".
Sources: the DXBC blobs in `notes/scratch-vision/dxbc/`, their disassembly in
`notes/scratch-vision/hlsl/*.asm`, the CPU-side wiring in `ghidra/neverclick-decomp.c`
(cross-referenced with `notes/report-vision.md` §3.3/§4.2–§4.6), and PE resource reflection.

**Headline:** the vision system is a classical pipeline — downscale → contrast → Sobel →
non-max suppression → threshold → dilate → (gated) mask downsample — plus a separate
12-probe SAD template matcher for icons. There is no neural network (`onnxruntime.dll` is inert;
`report-vision.md` §3.1). All 8 shaders are `cs_5_0`, `[numthreads(16,16,1)]`, work on
`SV_DispatchThreadID`-indexed textures, and use an immediate-indexed constant buffer
(`cb0`) whose **dword layout is the `PipelineConstants` struct of `report-vision.md` §4.2**:

| dword | field | used by stage |
|---|---|---|
| 0,1 | `g_width`, `g_height` (capture dims) | 1 (clamp), 7 (input bound) |
| 2 | `g_dpi_scale` | 1 (downscale ratio = source/target) |
| 3 | `g_edge_threshold` (2.0) | 5 |
| 4,5 | `g_scaled_width`, `g_scaled_height` | 1 (guard), 2, 3, 4, 5, 6 (guard/bounds), 7 (input bound) |
| 6 | `g_coord_scale` | 7 (with dword 2 → downsample factor) |
| 7 | pad | – |
| 8,9 | `g_label_width`, `g_label_height` | 7 (guard) |
| 10 | `g_min_blob_area` | CPU only |
| 11 | pad | – |
| 12–15 | `g_dilate_left/right/up/down` | 6 |
| 16,17 | `g_contrast` (2.0), `g_contrast_midpoint` (0.5) | 2 |
| 18,19 | pad | – |

Each shader declares only the prefix it needs (`cb0[2]` … `cb0[5]`), which is why the reflection
sizes differ per blob.

## 1. Toolchain (how to re-verify)

```bash
cd /home/asdf/Downloads/neverclick-re
export LD_LIBRARY_PATH=$PWD/tools/vkd3d-root/usr/lib
tools/vkd3d-root/usr/bin/vkd3d-compiler -x dxbc-tpf -b d3d-asm <blob.dxbc>    # SM5 D3D assembly
tools/vkd3d-root/usr/bin/vkd3d-dxbc -t <blob.dxbc>                            # RDEF/ISGN/OSGN/SHEX/STAT
# HLSL round-trip check of the reconstructed shaders:
tools/vkd3d-root/usr/bin/vkd3d-compiler -x hlsl -b d3d-asm -p cs_5_0 <ref_*.hlsl>
```
`dxc` cannot be used: it only reads DXIL ("DXIL container is missing DXIL part"). Committed
disassembly: `notes/scratch-vision/hlsl/*.asm`; reconstructed equivalents: `ref_edge*.hlsl`
(all 7 compile clean with vkd3d).

## 2. Blob → stage mapping (verified by shader content, not by inference)

| # | blob | reads | writes | identity evidence |
|---|---|---|---|---|
| 1 | `edge_1_140272470.dxbc` | `t0` float4 texture | `u0` uint | per-output-pixel **box average** over `[tid·ratio,(tid+1)·ratio)` with `ratio = cb0[0].z`; `div_sat` by sample count, `×255`, `round_ne`, packs `A<<24\|R<<16\|G<<8\|B` → **downscale** |
| 2 | `edge_2_140271b50.dxbc` | – | `u0` uint (in-place load+store) | `saturate((rgb−mid)·contrast + mid)` with `c4.x/c4.y` → **contrast** (in-place) |
| 3 | `edge_3_1402707a0.dxbc` | `t0` uint (packed BGRA8) | `u0` float4 | 3×3 Sobel `gx=(TR+2R+BR)−(TL+2L+BL)`, `gy=(BL+2B+BR)−(TL+T+TR)`, `mag=|gx|+|gy|`, orientation code → **Sobel** |
| 4 | `edge_4_14026fd10.dxbc` | `t0` float4 (mag, orientation) | `u0` float | neighbour comparison along the quantised direction, keep magnitude or 0 → **non-max suppression** |
| 5 | `edge_5_14026f520.dxbc` | `t0` float | `u0` uint | `(cb0[0].w < v) ? 1 : 0` with `cb0[0].w = 2.0` → **threshold** |
| 6 | `edge_6_14026e140.dxbc` | `t0` uint | `u0` uint | OR over rectangle `[x−L, x+R] × [y−U, y+D]` from `cb0[3]` → **dilate** |
| 7 | `edge_7_gated_14026eb20.dxbc` | `t0` uint | `u0` uint | OR over an `n×n` block, `n = round(cb0[1].z / cb0[0].z)` → **gated mask downsample** |
| 8 | `templatematch_140272f50.dxbc` | `t0` haystack float4, `t1` needle float4 | `u0` structured (8-byte records) | 12-probe SAD + 256-thread group reduction → **icon template matcher** |

Ordering matches the CPU stage chain of `report-vision.md` §4.3 exactly (stage 7 is gated: in 0.4.1
the caller passes a factor of 1, so it is effectively skipped).

## 3. Per-stage math (exact)

Notation: `tid` = dispatch thread id; `x`,`y` = pixel coords; packed pixels are **B8G8R8A8 in memory**
(`bits0-7 = B`, `8-15 = G`, `16-23 = R`, `24-31 = A`), so unpacking with `(px & 0xFF)` yields B, then G, then R.

**1 Downscale** (guard: `tid >= cb0[1].xy` → return).
```
ratio = cb0[0].z                                    // g_dpi_scale
x0 = floor(tid.x*ratio); x1 = min(floor((tid.x+1)*ratio), g_width)      // same for y
avg = sum over [x0,x1)x[y0,y1) of the float4 sample  /  sample_count    // div_sat
out = pack(round(avg*255)) with A<<24 | R<<16 | G<<8 | B
```
Sampling is a plain texture `Load` (point/box average, no filtering); `sample_count ≥ 1` because
`ratio ≥ 1`.

**2 Contrast** (in-place; guard `tid >= cb0[1].xy` → return).
```
rgb = unpack(px)/255 ; a = unpackA(px)/255
rgb = saturate((rgb - cb0[4].y) * cb0[4].x + cb0[4].y)     // midpoint 0.5, contrast 2.0
out = pack(round(rgb*255), round(a*255))
```
Alpha is untouched (multiplied by 1.0).

**3 Sobel + orientation** (guard `tid >= cb0[1].xy` → return).
Border pixels (`x==0 || y==0 || x>=w−1 || y>=h−1`, `w,h = cb0[1].xy`) → output **0**.
Gray value of a neighbour = `(B + G + R)/255` (equal weights; alpha ignored).
```
gx = (TR + 2*R + BR) - (TL + 2*L + BL)
gy = (BL + 2*B + BR) - (TL + T + TR)
mag = |gx| + |gy|
o   = (2.41421356*|gy| < |gx|) ? 0        // |gx| dominant
    : (2.41421356*|gx| < |gy|) ? 2        // |gy| dominant
    : ((gx*gy > 0) ? 1 : 3)               // diagonal, by gradient sign product
out = (mag, o, 0, 0)
```
`2.41421356 ≈ 1+√2 = tan 67.5°` — the classic 4-direction quantisation boundary.

**4 Non-max suppression** (guard `tid >= cb0[1].xy` → return; if `mag == 0` → store 0).
```
o = input.y
d = (o < 0.5) ? (0, 1) : (o < 1.5) ? (1, -1) : (o < 2.5) ? (1, 0) : (-1, 1)   // recovered from the movc chain
n1 = mag at clamp(tid + d) ; n2 = mag at clamp(tid - d)                       // clamped to [0, w-1]/[0, h-1]
out = (mag >= n1 && mag >= n2) ? mag : 0
```
Note: the offsets for codes 1 and 3 represent the same diagonal line with opposite sign
(`(1,-1)` vs `(-1,1)`); since both neighbours are tested symmetrically the outcomes are identical,
so effectively three directions are tested (vertical, diagonal, horizontal). Reproduce the table
verbatim for parity; simplify only if you accept equivalent output.

**5 Threshold** (guard `tid >= cb0[1].xy` → return).
```
out = (cb0[0].w < mag) ? 1 : 0        // cb0[0].w = g_edge_threshold = 2.0, strictly greater
```

**6 Dilate** (guard `tid >= cb0[1].xy` → return; input non-zero → 1).
```
L,R,U,D = cb0[3].xyzw
x0 = max(x-L,0), x1 = min(x+R,w-1), y0 = max(y-U,0), y1 = min(y+D,h-1)      // inclusive bounds
out = 1 if any input in [x0,x1]x[y0,y1] is non-zero, else 0
```
The structuring element is an **asymmetric rectangle centred on the pixel**; the CPU subtracts
the radii back from each component box afterwards (`report-vision.md` §4.4), so the radii only
ever *grow* the mask before labeling.

**7 Mask downsample** (guard `tid >= cb0[2].xy` → return, i.e. label dims).
```
n = (uint)(cb0[1].z / cb0[0].z + 0.5)                 // round(g_coord_scale / g_dpi_scale)
out = 1 if any in-block sample (x = tid.x*n + i, y = tid.y*n + j, i,j < n) is non-zero and in bounds
```
Gated in practice: the caller passes a factor of 1 so the label mask equals the scaled mask.

**8 Template matcher** (icon detection; `TemplateMatchConstants`, `cb0[9]`):
- Reads `t0` = haystack (monitor capture, BGRA8), `t1` = needle (cached window-icon bitmap), writes
  `u0` = structured 8-byte records `{error, linearIndex}`.
- `cb0[1]` = `(haystackW, haystackH, toleranceThreshold)`, `cb0[2].x` = groups per row,
  `cb0[3..8]` = the probe table (12 probes: `x,y` offsets plus the needle's `B,G,R,A` bytes, packed with
  `int16`/`uint8` fields as observed in the header unpacking).
- Thread block 16×16; each thread handles one candidate position: it samples the needle colour at the
  probe coordinates, compares each channel against the haystack (with `mov_sat`+`round` quantisation to
  8-bit), accumulates SAD, and **early-outs** once the accumulated error exceeds the per-probe budget
  (`cb0[1].z` threshold comparisons in the loop).
- Group best reduction over 256 threads via 256×8-byte shared memory: pairwise compare at distance
  8/4/2/1, tie-break **lowest index wins** (`err1 == err2 ? idx1 < idx2`), then the thread-0 result is
  written to `u0[groupY*groupsPerRow + groupX]`.
- The CPU wrapper (`GpuTemplateMatcher::searchAll`) sets the tolerance (dword `0x18 = 24` per
  `report-vision.md` §4.6), copies back the group records, thresholds them, applies overlap NMS and
  computes `score = 1 − errorSum/(needleW·765·needleH)`. A reimplementation may substitute any
  equivalent SAD/SSD matcher with the same probe set, budget and NMS semantics — the record format and
  group tiling are performance details, not behaviour.

Reconstructed HLSL for stages 1–7: `notes/scratch-vision/hlsl/ref_edge{1..7}_*.hlsl`
(all compile clean under `vkd3d-compiler -x hlsl -b d3d-asm -p cs_5_0`).

## 4. Resource / dispatch requirements

| stage | SRV | UAV | dispatch |
|---|---|---|---|
| 1 | `t0` float4 = capture (B8G8R8A8_UNORM) | `u0` uint = scaled colour | `ceil(scaled/16)` |
| 2 | – (in-place) | `u0` uint = scaled colour (R/W) | `ceil(scaled/16)` |
| 3 | `t0` uint = scaled colour | `u0` float4 = magnitude/orientation | `ceil(scaled/16)` |
| 4 | `t0` float4 = stage 3 output | `u0` float = NMS magnitude | `ceil(scaled/16)` |
| 5 | `t0` float = stage 4 output | `u0` uint = boolean mask | `ceil(scaled/16)` |
| 6 | `t0` uint = mask | `u0` uint = dilated mask | `ceil(scaled/16)` |
| 7 | `t0` uint = dilated mask | `u0` uint = label mask | `ceil(label/16)` |
| 8 | `t0` haystack float4, `t1` needle float4 | `u0` structured | `ceil(haystack/16)` (groups ≤ 0x1000) |

Readback (CPU): label mask (uint8 rows, `label_width × label_height`) and the scaled BGRA colour
image. The colour image is used by the `removeHallucinations` corner filter and is the same buffer
the shaders pack as `A<<24|R<<16|G<<8|B`.

## 5. Uncertainties

1. Concrete intermediate DXGI formats (e.g. `R32G32_FLOAT` vs `R16G16_FLOAT` for stage 3/4) were not
   read out of the CPU texture-creation code; the shaders only require the *typed* view declared above
   (uint vs float); a reimplementation picks formats freely as long as both sides agree.
2. Probe packing inside `cb0[3..8]` (12 probes × {int16 x, int16 y, uint8 B, G, R, A}) was inferred from
   the header unpacking instructions, not from the CPU-side writer; the *semantics* (12 fixed relative
   probe positions, per-channel SAD, tolerance budget) are confirmed by the CPU-side call site
   (`report-vision.md` §4.6).
3. Stage-7's factor is 1 in 0.4.1 (effectively skipped); the shader is still shipped and gated on
   label dims ≠ scaled dims.
4. Group-tiling limit `0x1000` groups and the 8-byte record split (`{error, index}`) come from
   reflection/disassembly; a reimplementation only needs an equivalent reduction.
