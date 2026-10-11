# Neverclick 0.4.1 reverse engineering

- `SPEC.md` — final reimplementation specification (the deliverable; start at §0)
- `notes/` — findings log, **`ARTIFACTS.md`** (path index + removal record), **`AUDIT.md`** (feasibility
  audit), and the reports: `report-vision.md`, `report-hints.md`, `report-interaction.md`,
  `report-config-ui.md`, `report-shaders.md`, `report-tools.md`, `report-gaps-closure.md`;
  public dossier in `notes/public/`
- `notes/scratch-*` — per-subsystem authored scratch (reconstructed HLSL, helper scripts, catalogs)
- `ghidra/scripts/` — headless decompilation pipeline (tooling only)
- `tools/` — user-local RE tooling (7zz, patched innoextract + source, dxc, vkd3d)

Status source of truth: `notes/00-findings.md`. Evidence map: `SPEC.md` §15.

> **Proprietary artifacts removed.** The original Neverclick payload (installer, `neverclick*.exe`, DLLs,
> bundled fonts), the extracted Tauri/React frontend bundle, the Ghidra decompilation dumps and projects,
> every raw scratch dump (decompilation parts, string/disassembly dumps, DXBC shader blobs, `*.asm`) and the
> session archive have been deleted from this tree. Only the analysis authored here (spec, reports,
> reconstructed HLSL, helper scripts, public dossier) remains; see `notes/ARTIFACTS.md` for the removal
> record. Citations inside the reports that point at the removed dumps (`part_NN:line`, `decomp:line`,
> `disasm:line`, `ustr/cstr:Ln`) are historical and cannot be re-opened.

## TL;DR findings
- Installer: Inno Setup 6.7.0 (extracted with a patched innoextract).
- App: Windows x64, MSVC C++ core (`neverclick.exe`, ns `nvr`) + Tauri/WebView2 settings GUI.
- **No neural network.** "Neverclick Vision" = hand-written D3D11 compute-shader classical CV
  (downscale/contrast/Sobel/NMS/threshold/dilate) + CPU union-find labeling + a 12-probe SAD GPU
  template matcher for icons. `onnxruntime.dll` ships but is provably inert.
- Hints: 2-char labels from a priority-ordered key list; deterministic combo ordering; assigned by
  distance to the foreground window center; digits/arrows adjust the target point.
- Core exposes an unauthenticated HTTP API on `0.0.0.0:7340`; config in `%AppData%\Roaming\Neverclick\`.
