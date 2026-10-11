# Visual design notes (from official images, viewed 2026-10-09)

Files in `images/` (all webp).

## anatomy-of-hint.webp (1745x730, dark canvas ~#111)
- **Bounding box**: bright-green rectangular outline (~2 px stroke, square corners) around the detected element (example: text "neverclick" boxed). Green ≈ #3ee96b family.
- **Hint label ("jj")**: small white rounded chip with dark (near-black) monospace text, centered on the box edge it labels; chip sits ON the outline (white fill punches through the green stroke).
- **Target**: hollow green ring (~10 px dia, green dot center) — default at box center; when moved, a thin straight green line connects hint chip → target (visual guide).
- Text callouts (gray) label the three parts: Hint / Bounding box / Target.

## key-priority-map.webp (1920x998) — Settings page
- Settings app nav bar: `Neverclick | Appearance | Settings | System | About` (+ tray icon, min/max/close).
- Page: title "Key Priority Map", subtitle: "This heat map shows how each key is prioritized when generating hints. Brighter colors indicate higher priority."
- Heatmap on QWERTY: **F and J brightest** (home index); next tier D, K, S, L, A?, H/G dim; E, R, I, C, M, V, W mid-low; Q, P, O, U, T, Y, Z, X, B, N darkest-but-lit; number row / punctuation / modifier rows unlit (not used for hints).
- Implication: priority weight = per-key scalar keyed by physical position (QWERTY positions; config `keyboardLayoutPolicy`/`keyboardLayout` likely remap).

## overlay-vscode.webp / overlay-settings.webp (hint overlay in real apps)
- Hint chips overlay dense UI; see file for stroke widths/colors at scale.

## virtual-keyboard-config.webp / virtual-keyboard-ui.webp
- Config UI: interactive virtual keyboard for assigning keybinds (2560x1440 window, same dark theme, Win11 chrome).
