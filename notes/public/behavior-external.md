# External behavior dossier (public sources — cross-check against binary)

Sources saved here: `README-upstream.md`, `hn-48877485.json` (author = `lazov`), Register 2026-07-16 article (key claims below), neverclick.com (fetched).

## What it is
- Windows-only C++ desktop app (author: "C++ hater", wanted GitHub language stats = C++; topics: cpp), ~40 MB install, installs to Program Files to register as an accessibility tool (UIPI → can click into elevated apps).
- Keyboard-driven mouse control. Tray icon + GUI config; **no config files** (per README).
- Digitally signed, Microsoft Trusted Signing.

## Core loop (user-visible)
1. Global hotkey activates a **Tool** (e.g. Left Click Tool = Ctrl+Enter; Alt+Enter default = Ctrl+Left Click; no default right click).
2. App captures screen, runs CV, overlays **hints**: each detected element gets a bounding box outline + 2-letter label ("ek","af","jj") + target point (center of bbox by default).
3. Typing a hint combo moves cursor there and performs the tool's action.

## Hint labeling rules (author quotes, HN)
- Key combinations are **2 characters**.
- Letters prioritized toward keyboard center (customizable Key Priority Map).
- Combo list is sorted **most→least convenient** (e.g. `JJ`, `FF` at top — repeated letters rank high; author: "so for example JJ and FF would be at the top of the list").
- Most convenient combos assigned to elements **closest to screen center** ("that's where people are most likely to perform a mouse action").
- Hints use user's Windows keyboard layout (Dvorak/Colemak/non-English supported natively).

## Target manipulation (README + Register)
- Arrow keys / Shift+J I L K: snap target to bounding-box edge (beginning/end of word).
- Number row 1–9 (Register mentions `0` too — verify): position target within box, character-level precision ("click in center of a word by default, hit a number to get to a particular letter").
- Anatomy: bounding box outline, hint label, target crosshair.

## Selection modes (README)
- `'` → Dual Select (2 hints), Shift+`'` → Multi Select, Ctrl+`'` → Path mode (auto-selects hints between two picks), Enter finishes.

## Window management (README)
- Tab toggles Window mode ↔ Full Screen mode.
- Shift+W/A/S/D switch windows (Window mode); Shift+Q/W cycle overlapping windows; Shift+Z switch to window behind.
- Actions: Scroll, Move Window (between monitors/virtual desktops), Sticky Hints Tool (save hints for repeat clicking).
- Coming soon (v0.4.1 era): text highlight between 2 hints, drag.

## Three vision modes (README)
1. **Neverclick Vision** (default): CV on raw pixels; fast ("instantaneous on 10-year-old hardware"), detects text well (good in editors/coding), supports full-screen, tunable detection settings.
2. **Clairvoyance** (`[` to switch): OS accessibility APIs (Windows UIA); slower, foreground-window-only, no text detection in editors, untunable, sometimes cleaner button boxes.
3. **Grid** (`;`): evenly spaced hints (for blank areas/desktop).

## CV implementation claims (author, to The Register)
- "built the computer vision system himself **without relying on any third-party libraries**" — no OpenCV/onnxruntime/etc.
- Small model; whole app ~40 MB; ~200 MB RAM @1080p (scales with monitors/resolution/scaling).
- No continuous loop: 0% CPU idle; runs only on activation.
- Faster than UI Automation in author's tests.
- Occasionally "hallucinates" (false positives).

## Open questions for binary
- Exact CV algorithm/model (custom NN? classical CV? model weights location/format).
- OCR/text detection approach; how word-level boxes derived.
- How labels assigned (verify sort/cost algorithm from disassembly).
- Hint rendering mechanism (layered window? DirectComposition?), screen capture API (DXGI duplication? GDI? PrintWindow?).
- Click injection (SendInput?), global hotkey registration, elevation strategy.
- Settings storage (registry? JSON in AppData? — "no config files" claim).
- UIA usage in Clairvoyance mode; tray/GUI framework (Win32? Qt? ImGui?).
