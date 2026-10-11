# Neverclick 0.4.1 — RE Project Findings

> **Note (post-cleanup).** The source artifacts named below — the installer, the extracted payload
> (`extracted/`), the extracted UI assets and the Ghidra decompilation dumps — have since been **deleted
> from this project folder** because they are proprietary. This log is retained verbatim as the working
> record; its paths are historical. See `notes/ARTIFACTS.md` for the removal record.

## Source artifact
- Installer: `/home/asdf/Downloads/neverclick-setup-0.4.1.exe` (copy: `installer/neverclick-setup-0.4.1.exe`)
- SHA256: `bc52c68aab3c1778b418d64f1ba505d160b44a62c60ce323496f3273e0b2d877`
- Size: 15,562,472 bytes; PE32 GUI i386, 11 sections
- Installer engine: **Inno Setup 6.7.0** (strings: `Inno Setup Setup Data (6.7.0)`, `Inno Setup Messages (6.5.0) (u)`)
- Version resource: ProductName "Neverclick", FileDescription "Neverclick Setup", FileVersion 0.4.1.0, CompanyName "neverclick"

## Extraction status
- 7zz 26.04 (`tools/7zz`): only extracts PE sections → `installer/pe-sections/` (loader resource `RCDATA/11111` = 64-byte setup loader header, magic `rDlPtS cd e6 d77b 0b2a`, revision 2).
- innoextract 1.9: FAILS — Inno 6.7 loader revision 2 + unknown setup-data version string (upstream supports ≤ 6.4.0.1).
- Subagent `InnoPatch`: patching git innoextract (source: `/home/asdf/Downloads/re-tools/inno-src`, build: `/home/asdf/Downloads/re-tools/inno-build`) to support 6.7.0; target output `/home/asdf/Downloads/nc-inno/`.
- Tooling (no sudo): static `tools/7zz`; local innoextract pkg at `tools/inno-root`; network OK.

## Analysis toolchain verified
- Ghidra headless: `/opt/ghidra/support/analyzeHeadless` (JDK 27) — OK
- objdump with `pei-i386`/`pei-x86-64` — OK
- node v24.21.0 + npm (asar extraction) — OK
- python3.14 + pefile, pyelftools; pip is PEP-668 managed (use venv for extra libs)
- No wine, no capstone/lief by default

## Environment constraints
- No root/sudo (password prompt fails) — install tools user-local only.
- Project folder: `/home/asdf/Downloads/neverclick-re/` — all artifacts live here.
- `re-tools/` and `nc-inno/` still under Downloads while InnoPatch runs; relocate into project folder after.

## Goals
- Fully reverse engineer the app (computer-vision functionality, labeling, accessibility exposure).
- Produce a reimplementation specification (`SPEC.md`) for a different agent to rebuild from scratch.

## Architecture map (from RTTI + imports, 2026-10-09)
- **neverclick.exe** (4.5 MB, MSVC, namespace `nvr`): core — capture, CV, hints, hotkeys, overlay windows, input injection, local HTTP server.
  - Imports: onnxruntime.dll (ordinal 1 = OrtGetApiBase → ORT C API), zlib1.dll (raw inflate/deflate), WS2_32 (sockets), dwmapi, COMCTL32, DWrite via delay?
  - Ghidra decomp: `ghidra/neverclick-decomp.c` (6693 funcs, 13.5 MB).
  - Key RTTI: HintCoordinator + providers {VisionProvider, GridProvider, FullScreenGridProvider, CustomProvider, UiAutomationProvider}; HotkeyManager{ToolActivation/Sleeping/Suspended hooks}; tools {basic_mouse_action_tool, sticky_hints_tool, window_move_tool, window_snapping_tool}; actions {ClickOnWindow, Scroll}; common_events::{MouseOperations→INPUT vectors, MoveMouse}; win::{GpuContext, TextureOps::Rotate, GpuTemplateMatcher, GetCudaInfo, NvidiaPowerMode}; RestServer::run + hotkey routes; UiAutomationManager/FailSafeUiAutomationManager; NeverAppBar::initRouter; config {AppConfigFromDiskProvider, HotkeyEntriesFromDiskProvider, SavingManager}.
  - Config: `app-config.json`, `hotkey-config.json.gz` (+ .v1.backup, .corrupt.bak); ~23 setting keys incl. detectionModel, fovMode, hintPlacement, removeHallucinations, hintAssignment, enableProgressiveHints, keyOverrides.
  - Resources: tray PNG, 2 WAVs (sounds), many icons, no ONNX file found yet (VisionPipeline agent hunting; zlib `78 da` hits in .rdata at 0x27DC60/0x27E0B8 are leads).
- **neverclick-ui.exe** (20.4 MB, Tauri/Rust + WebView2, `.taubndl` section): settings GUI. Extracted web assets → `extracted/ui-assets/`.
- **neverclick-graphics-check.exe** (778K): dxgi/d2d1/d3d11 capability probe. **neverclick-updater.exe** (420K): self-update.
- **onnxruntime.dll** 12 MB (CPU+CUDA+TensorRT EP exports present but only OrtGetApiBase imported by ordinal 1).
- Fonts (11 TTF: Inter, JetBrainsMono, FiraMono, RobotoMono, SourceCodePro, IBMPlexMono, Geist, Outfit, PlusJakartaSans, NunitoSans, DMSans) → hint fonts selectable via hintFontName.
- Licenses: cpp-httplib (local HTTP), everything (voidtools Everything search), fmt, folly, gsl, highway (SIMD), nlohmann/json, pugixml, spdlog, tauri.

## Analysis fan-out (running)
- VisionPipeline → notes/report-vision.md; HintSystem → report-hints.md; InteractionLayer → report-interaction.md; ConfigUi → report-config-ui.md.
- Final: SPEC.md (parent, last).

## Status: COMPLETE (2026-10-09)
- All four subsystem reports delivered and spot-verified: report-vision.md (465 l),
  report-hints.md (778 l, incl. gap closure), report-interaction.md (708 l), report-config-ui.md (572 l).
- Final deliverable written: `SPEC.md` (reimplementation specification for a fresh agent).
- Headline result: no NN model — classical shader CV; onnxruntime inert; see SPEC §4.
