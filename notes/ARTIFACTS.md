# Artifacts manifest — Neverclick 0.4.1 RE project

Root: `/home/asdf/Downloads/neverclick-re/`

> **The tree has been cleaned: no proprietary code remains.** Every artifact derived from, or shipped with,
> the Neverclick build was deleted. What follows lists what is present, then records what was removed (paths
> and purpose only — no content retained).

## Deliverable (present)
| Path | What |
|---|---|
| `SPEC.md` | Reimplementation specification (start at §0; evidence map §15) |
| `notes/report-vision.md` | CV pipeline evidence (capture, shaders, labeling, filters, template matcher) |
| `notes/report-hints.md` | Hint labeling/assignment/target geometry evidence |
| `notes/report-interaction.md` | Input hooks, injection, window management, UIA, elevation evidence |
| `notes/report-config-ui.md` | REST API, config schema/defaults, Tauri UI, helpers evidence |
| `notes/report-shaders.md` | Shader pseudocode + reconstructed kernel math (Appendix E source) |
| `notes/report-tools.md` | Tool/action catalog + factory hotkey config (Appendix F source) |
| `notes/report-gaps-closure.md` | Remaining behavioural gaps resolved (Appendix G source) |
| `notes/00-findings.md`, `notes/AUDIT.md` | Status log; feasibility audit |

## Authored scratch (present)
| Path | What |
|---|---|
| `notes/scratch-vision/hlsl/ref_edge*.hlsl` | Reconstructed HLSL equivalents of the 8 vision kernels |
| `notes/scratch-vision/hlsl/pilot/` | Reconstruction pilot (HLSL + SPIR-V asm) |
| `notes/scratch-vision/hlsl/sm5_tokens.py` | SM5 disassembly tokenizer |
| `notes/scratch-tools/ui-catalog.tsv` (+ `*.md`, `*.tsv`) | Catalog/parameter tables (Appendix F source) |
| `notes/scratch-configui/{extract_ui_assets.py,grabfn.js,resolve_routes.py}` | UI-bundle inspection helpers |
| `notes/scratch-hints/rtti_map.py`, `notes/scratch-interaction/vt.py` | RTTI/vtable helper scripts |
| `ghidra/scripts/{decompile-one.sh,DumpDecompilation.java}` | Headless decompilation pipeline |

## Public references (present)
| Path | What |
|---|---|
| `notes/public/README-upstream.md` | upstream README (product behaviour) |
| `notes/public/behavior-external.md` | product/author claims dossier (HN quotes, Register article) |
| `notes/public/images/` | official screenshots + hint anatomy + key-priority map (visual ground truth) |
| `notes/public/hn-*.json` | HN threads with author statements |

## Toolchain (present — third-party, non-proprietary)
| Path | What |
|---|---|
| `tools/re-tools/7zz`, `7zzs`, `7z.tar.xz` | 7-Zip (LGPL) — PE/inno scanning |
| `tools/re-tools/inno-root/usr/bin/innoextract` | stock innoextract 1.9 |
| `tools/re-tools/inno-src/`, `inno-build/`, `inno.pkg.tar.zst` | patched innoextract (Inno 6.7), built from source |
| `tools/re-tools/issrc/` | Inno Setup source (build-language reference) |
| `tools/dxc-root/` | DirectX Shader Compiler (MIT; DXIL only — cannot read SM5 DXBC) |
| `tools/vkd3d-root/usr/bin/vkd3d-compiler`, `vkd3d-dxbc` | SM5 DXBC → D3D assembly, container/reflection dump |

## Removed (proprietary — deleted, content not retained)
| Path | What it was |
|---|---|
| `installer/neverclick-setup-0.4.1.exe` | shipped installer (Inno Setup 6.7.0) |
| `extracted/app/neverclick.exe` | core engine |
| `extracted/app/neverclick-ui.exe` | settings GUI (Tauri/WebView2) |
| `extracted/app/neverclick-updater.exe` | updater/relauncher |
| `extracted/app/neverclick-graphics-check.exe` | GPU probe |
| `extracted/app/*.dll` (onnxruntime, SDL2, MSVC runtime, zlib) | shipped runtime libraries |
| `extracted/app/fonts/` | 11 bundled TTFs used by the hint renderer |
| `extracted/app/licenses/` | bundled third-party license texts |
| `extracted/tmp/MicrosoftEdgeWebview2Setup.exe` | WebView2 bootstrapper |
| `extracted/ui-assets/` | 66-file reference frontend bundle (shipped app code) |
| `extracted/model-candidates/` | large PE resources (icons) |
| `ghidra/neverclick-decomp.c` | full decompilation of the core (6693 functions) |
| `ghidra/installer-stub-decomp.c` | decompilation of the installer stub |
| `ghidra/ghidra/projects/` | Ghidra project (embedding the binaries) |
| `notes/scratch-vision/disasm.txt`, `func-index.txt` | objdump disassembly, function index |
| `notes/scratch-vision/dxbc/` | 8 DXBC compute shaders (the "model") |
| `notes/scratch-vision/hlsl/*.asm` | disassembly of those shaders |
| `notes/scratch-hints/fn_*.c`, `part_0[0-3]`, `strings4.txt` | decompiled function, decompilation parts, string dump |
| `notes/scratch-interaction/{func-index,symbol-hits,trace-scopes,trace-strings}.txt` | derived indexes/string dumps |
| `notes/scratch-configui/*.txt`, `*-decomp.c`, `probe/` | extracted bundle JS/strings, decompiled helpers, raw blobs |
| `omp-archive-*.zip` | session archive (contained tool logs with the above dumps) |

Report citations of the form `part_NN:line`, `decomp:line`, `disasm:line` and `ustr/cstr:Ln` referred to the
removed dumps; they are retained as provenance at line granularity only and cannot be re-opened.
