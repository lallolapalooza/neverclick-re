# Feasibility audit — can another agent replicate Neverclick 0.4.1 from this spec?

Method: walk the implementation path milestone by milestone (SPEC §14 / Appendix D.3) and, for each,
check whether the spec + reports contain everything needed to *build and verify* that piece, without
access to the original binary.

## Verdict

**Yes for behaviour-level replication of the full feature surface**: detection, hint labelling and
assignment, target geometry, overlay rendering, input interception, mouse/scroll injection, window
management, the three vision modes, sticky hints, the REST/GUI contract, configuration, updates and
installation are all specified to the level of exact algorithms, constants, message ids and JSON shapes.

**Not guaranteed without tuning**: pixel-identical CV output on arbitrary screens. The kernel math is now
exact (Appendix E: Sobel taps, magnitude, orientation quantisation with 2.414, the NMS offset table,
threshold semantics, dilate rectangle, downscale box average), so a correct implementation should match
closely, but the original's *box-level* output also depends on the connected-component/area/size filters
(fully specified) and on the capture path — expect to tune against the reference screenshots (Appendix D.1).

**Deliberately out of scope / stubbed**: the Voice pages and `NavigationMode` presets that the shipped GUI
ships but the 0.4.1 core does not implement (they 404 against this core).

## Per-milestone coverage

| Milestone | Coverage | Residual |
|---|---|---|
| M0 Config service, REST, tray, single instance | Full: 29 routes with effects, error envelope, event long-poll, `app-config.json` schema (36 keys) + defaults, gzip hotkey file + backups, config dir, autostart shortcut, tray menu ids, mutex/window class | Exact per-field numeric validation limits (UI zod gives bounds); the full compiled default-keybind table beyond the verified subset |
| M1 Input layer | Full: one LL hook on its own thread, marshal protocol, `0x147d` self-injection marker, Win-key replay trick, chord model + modifier snapshot, 3-state machine, `0x501/0x502/0x50f` flow, tool capture/passthrough sets, release trap with ≈1.001 s fallback | Population detail of the trap's passthrough set (behaviour specified; set contents are an implementation choice) |
| M2 Vision pipeline | Full: DDA capture + GDI fallback + recovery, rotation, FOV modes, 8 shaders with verified math and equivalent HLSL, CB layout, dilation presets, CPU union-find + area/size/hallucination/window filters, icon template matcher semantics | Concrete intermediate texture formats (free choice); byte packing of the matcher's probe table (semantics known) |
| M3 Hints | Full: alphabet construction + fallbacks, 48-key default priority order, depth rule, combo ordering proof, both assignment modes, grid math, digits/arrows formulas, provider merge, caching keys, rendering stack + fonts + colours, progressive-hint semantics | Exact label-chip pixel geometry/typography (visible in the reference screenshots; cosmetics) |
| M4 Actions & window management | Full: exact `INPUT` vectors and flags, modifier-neutralised batches, return-to-origin, click/wheel/scroll params, focus/cycle/move/snap/tile/virtual desktop algorithms and enums, animation gates | A few enum literal names (e.g. tile styles) and the `flagC` scroll nuance |
| M5 Modes, sticky hints, UIA | Full: Vision/Grid/FullScreenGrid/Clairvoyance/Custom providers, UIA client scope + failsafe one-shot, icon geometry refresh, sticky schema + re-anchoring incl. auto key assignment | `matchAccuracy`/`maxDistance` numeric wiring in the ImageRecognition path |
| M6 Installer, updater, graphics check | Full: Inno layout, `uiAccess` manifest requirement, updater argv + wait timeouts + silent install flags, probe exe argv + JSON report, WebView2 bootstrapper, update download/verify/hand-off | Authenticode certificate procurement (external prerequisite, not a spec gap) |

## Risk list for the implementer

1. **`uiAccess` prerequisite** — requires an Authenticode-signed binary installed under Program Files; you
   cannot test elevated-window clicks with an unsigned build (Windows will refuse to load it).
2. **D3D11 duplication** — the DDA primary path plus the GDI fallback and the ACCESS_LOST recovery loop are
   the most environment-sensitive part; implement the fallback early.
3. **Overlay vs capture feedback** — without the temporary `WDA_EXCLUDEFROMCAPTURE` on the overlays during
   capture, hints will be detected as UI elements.
4. **Hook hygiene** — swallowing keys via a low-level hook without the `0x147d` marker breaks your own
   hotkeys, and without the Win-key replay trick the Start menu pops after Win chords.
5. **Queue timing** — the countdown queue is tick-based; pick a 1 ms timer and keep `eventDelay` as a
   countdown (default 10) to reproduce the input pacing.

Everything else in the build is ordinary Windows/C++/Tauri work with the contracts given.
