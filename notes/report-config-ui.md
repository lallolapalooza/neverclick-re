# Neverclick 0.4.1 — Configuration / UI / IPC Report

> **Artifact availability.** The original binaries, the extracted frontend bundle (`extracted/`), the
> Ghidra decompilation dumps (`ghidra/*-decomp.c`) and the raw scratch dumps (`notes/scratch-*/`, including
> `ui-strings.txt`, `core-strings.txt`, `*-decomp.c`) have been removed from this tree. Citations below
> (`decomp:line`, `ustr:Ln`, `cstr:Ln`, `part_NN:line`, `extracted/...`) refer to those removed files and
> cannot be re-opened; the analysis and reconstructed pseudocode remain authoritative.

Scope: `neverclick-ui.exe` (Tauri settings app), `neverclick.exe` RestServer (local HTTP API),
on-disk config formats + defaults, `neverclick-updater.exe`, `neverclick-graphics-check.exe`,
install/runtime layout. Static analysis only; binaries never executed.

Citations: `decomp:L<line>` = `ghidra/neverclick-decomp.c` line (functions cited by VA,
e.g. `FUN_140086a80` = 0x140086a80); `ustr:L<n>` = `notes/scratch-configui/ui-strings.txt`;
`cstr:L<n>` = `notes/scratch-configui/core-strings.txt`; asset paths under
`extracted/ui-assets/`. `[INFER]` = reasoned, not directly observed.

---

## Summary

- Two-process design. **`neverclick.exe`** (core, MSVC C++) owns the tray icon, hotkeys, CV,
  overlay windows, config storage, and a **cpp-httplib REST server bound to `0.0.0.0:7340`**
  with **no authentication** (bind host literal `"0.0.0.0"` at decomp:L116952; port `0x1cac`=7340
  immediates at VA 0x1400935FC/0x140093AA4 inside `FUN_140093570`/`FUN_140093930`; no
  `Authorization`/`Bearer` strings in core).
- **`neverclick-ui.exe`** (Tauri 2.9.4 + WebView2, React SPA) is the *settings GUI*. It talks to
  the core **only over HTTP** at `Gt.APP_URL = "http://127.0.0.1:7340"` (bundle, `Gt` const;
  version const `ope="0.4.1"`). No custom Tauri `invoke` commands for core data — only stock
  Tauri plugins (`http`, `fs`, `dialog`, `event`, `shell`, `window`, `webview`, `single-instance`).
- Spawn chain: core tray **"Open"** → `ShellExecuteExW(L"open", <install_dir>\neverclick-ui.exe)`
  (`FUN_140179c20` decomp:L314353; exe-name wide string at VA 0x1402811d0, len 0x11;
  `AppendMenuW ... L"&Open"` decomp:L85864). UI (tauri-plugin-single-instance 2.3.6, ustr:L72973)
  ensures a single GUI instance; UI resolves the install dir and `neverclick.exe` (ustr:L72974)
  and drives the core over HTTP — whether the UI *spawns* the core on demand is `[INFER]`
  (CreateProcessW import present; no spawn literal recovered).
- UI pushes nothing: it **long-polls `GET /events?cursor=N`** (`{bootId,cursor,resync,goingDown,events[]}`)
  and invalidates React-Query caches; health = polled `GET /health` with exponential backoff 200 ms→3 s.
- Config lives in **`%AppData%\Roaming\Neverclick\`** (FOLDERID_RoamingAppData GUID 3EB685DB-… at
  decomp:L55557 + subdir `"Neverclick"` at decomp:L5516): `app-config.json` (plain JSON) and
  `hotkey-config.json.gz` (gzip JSON, plus `.v1.backup` / `.corrupt.bak` siblings).
- Full app-config schema + defaults recovered from the default constructor
  `FUN_140057bd0` (decomp:L76365) cross-checked with `to_json` `FUN_1400a6e30` (decomp:L140714)
  and enum-name tables in `.rdata` — see Settings section.
- Frontend assets (66 brotli-compressed entries) extracted to `extracted/ui-assets/`
  (index.html + `index-CG8hdpTV.js` 1.42 MB React bundle + `index-BknSijrv.css` + fonts/images).
  Six pages: Neverclick (hotkeys), Voice, Appearance, Settings, System, About.
- Updater: core downloads/verifies; `neverclick-updater.exe` only **waits for PIDs then launches**
  (`--install <setup.exe>` runs Inno silently `/VERYSILENT … /LAUNCHAPP=1 /MERGETASKS="!startup"`).
- `neverclick-graphics-check.exe` = DXGI/D3D11/D2D probe printing a JSON report (`"gpus"` array,
  `dedicatedVideoMemory`, `DuplicateOutput` test); core invokes it with `--preference=1|2|none`.
- Core 0.4.1 contains **no `/voice*` or `/navigation-mode-presets` routes** (binary string search
  empty) — those UI pages hit 404 against this core. See Gaps.

---

## Process & IPC architecture

### Processes

| Process | Role | Evidence |
|---|---|---|
| `neverclick.exe` | Core: tray, hotkeys, CV, overlays, REST server on :7340, config I/O, updater/probe spawner | RTTI `nvr::RestServer::run(HWND*, events::EventHub&)`; `Shell_NotifyIconW` cstr:L43012 |
| `neverclick-ui.exe` | Settings GUI (Tauri 2.9.4 + WebView2), HTTP client only | ustr:L67858 (`Neverclick UI`, `com.neverclick.app`, dev `http://localhost:5173`, `src\main.rs`, `../dist`); bundle `Gt` |
| `neverclick-updater.exe` | Post-exit file replacer (wait PIDs → launch installer/relaunch) | updater-decomp FUN_140001940 |
| `neverclick-graphics-check.exe` | One-shot GPU/screen-capture capability probe (JSON stdout) | graphics-check-decomp; core FUN_1400c6900 |

### Start-up / single instance (core)
- `main` flow: `CreateMutexW(0, TRUE, name)` with name passed in; caller builds
  **`L"n3v3rcl1ck"`** (decomp:L5431); `ERROR_ALREADY_EXISTS (0xB7)` → "Mutex already exists."
  (decomp:L30050). Secondary check: `FindWindowW(L"Neverclick", NULL)` (decomp:L5794) — window
  class "Neverclick".
- Boot also builds `https://www.neverclick.com` + `"/api/version"` (decomp:L5494, L5510-5516)
  → startup update check via WinHTTP (`WinHttpOpen(L"Neverclick", …)` decomp:L236163).

### Core → UI launch
- Tray context menu (created in `FUN_140062fc0`, decomp:L85771): **&Open** (id 0xd1, default item),
  separator, **Suspend/Resume** (0xd2), **Sleep/Wake** (0xd3), separator, **Exit** (0xd0).
- WM_COMMAND handler (decomp:L84530+):
  - 0xd1 → `FUN_140179c20` (decomp:L314353): builds `<dir(neverclick.exe)>\` + wide name at
    VA 0x1402811d0 len 0x11 = **`neverclick-ui.exe`**, then
    `ShellExecuteExW{lpVerb=L"open", lpFile=path, lpParameters=L"", nShow=SW_SHOWNORMAL}`
    (decomp:L314526-314560). Failure → "Failed to execute shell command." MessageBox
    (`FUN_1400012c0`, title "Neverclick Updater" only in updater — core uses its own log here).
  - 0xd0 → `FUN_1400d1510()` + `DestroyWindow` (clean shutdown).
  - 0xd2/0xd3 → `FUN_14017a410` / `FUN_14017abb0` (suspend/resume, sleep/wake of hotkey engine).
- UI side uses **tauri-plugin-single-instance 2.3.6** (ustr:L72973) — second tray "Open" focuses
  the running window instead of double-launching.

### UI → core
- All data via HTTP to `http://127.0.0.1:7340` (Tauri `plugin:http|fetch`, base const `Gt`).
- **Health loop** (`rPe` provider, bundle): `GET /health` with `connectTimeout:500`; on success
  `invalidateQueries()` + `isAvailable=true`; on failure retry with backoff starting
  `H0=200` ms, cap `tPe=3e3` ms, factor `nPe=2` `[INFER: 200→400→800→1600→3000]`; window
  focus forces an immediate retry. Context: `{isAvailable, hasEverConnected, downSince}`.
- **Event loop** (`d9e`, bundle): `GET /events` first, then `GET /events?cursor=<cursor>` in an
  endless long-poll loop (no client sleep). Response zod
  `{bootId:string, cursor:number, events:string[], resync:boolean, goingDown:boolean}`.
  - `bootId` change → invalidate everything (core restarted).
  - `resync` → invalidate everything.
  - `goingDown` → call global `Xr` (mark connection down), stop.
  - Event → query invalidation map (`c9e`): `hotkeysChanged→["hotkeys"]`,
    `appConfigChanged→["appConfig"]`, `keyboardLayoutChanged→["keyCodes","keyPositionMap"]`.
  - Event names also in core cstr:L40007-40009; response keys decomp:L124924-124995
    (handler `FUN_140092490`); `cursor` query param parsed decomp:L124675; contains a
    10000000-unit (1 s if 100 ns ticks) wait constant decomp:L124807 → **server blocks ≈1 s max**
    per poll `[INFER]`.
- **No other IPC** (no named pipes; core↔UI message windows are internal to each process).

### Route → window-message bridge (internal to core)
Every HTTP handler is a thin adapter: it packs a result buffer and calls
`SendMessageW(hWnd, Msg, wParam, buf)` into the core main window; the window proc
(switch-style dispatcher, cases 0…11 observed) computes the result and sets an ok-flag
(decomp:L177130 helper `FUN_1400d3890`). Observed wParam table:

| wParam | operation | caller handler |
|---|---|---|
| 0 | get app-config | GET /app-config `FUN_140092250` |
| 1 | merge-patch app-config | PATCH /app-config `FUN_140091790` |
| 2 | factory-reset app-config | POST /app-config/reset `FUN_140091550` |
| 4 | get hotkey list | GET /hotkeys `FUN_1400913b0` |
| 5 | create hotkey | POST /hotkeys via `FUN_1400d3940` |
| 6 | update hotkey | PUT /hotkeys via `FUN_1400d3ab0` |
| 7 | delete hotkey | DELETE /hotkeys/:id `FUN_140090ac0` |
| 8 | swap hotkeys | POST /hotkeys/swap `FUN_140090770` |
| 9 | duplicate hotkey | POST /hotkeys/:id/duplicate `FUN_140090490` |
| 10 | toggle hotkey | POST /hotkeys/:id/toggle `FUN_140090140` |
| 11 | factory-reset hotkeys | POST /hotkeys/reset `FUN_14008ffa0` |

Config application side effects run through `AppConfigUpdater` (cstr:L40303-40313):
`updateRunOnStartup` (startup-folder shortcut add/remove), `setVisibilityToScreenCapture`,
`updateKeyCodes`, `updateGlow` (requires GPU rendering: "Glow effect requires GPU-accelerated
rendering." cstr:L40298), `updateAnimationsEnabled` (animation window), theme update.

---

## HTTP API table

Server: cpp-httplib inside `nvr::RestServer::run` — actually `FUN_140086a80`
(decomp:L116158, signature `(this, HWND**, EventHub&)`; EventHub pointer captured into the
`/events` handler at decomp:L116425). Bind: host `"0.0.0.0"` (decomp:L116952),
port **7340** (`FUN_140093930` returns `0x1cac` on success, decomp:L125768; `getaddrinfo(host, "7340")`
in `FUN_140093570` decomp:L125588; `listen(fd,5)` decomp:L125627), then accept thread
(`FUN_140093bd0`, decomp:L116964). **No auth, no tokens, no origin checks** (no
auth-related strings anywhere in core).

Route registration is per-method map insert: `FUN_140095aa0`=GET, `FUN_140093fc0`=POST,
`FUN_140093f20`=PUT (map +0x170), `FUN_140094060`=PATCH (map +0x1a0), raw
`FUN_140094180(base+0x128)`=GET-inline / `(base+0x1d0)`=DELETE (decomp:L126025-126141).

| Method | Path | Handler VA | Request | Response | Effect |
|---|---|---|---|---|---|
| GET | `/health` | vtable 14026a448 | – | 200 | liveness for UI backoff poll |
| GET | `/events` | 0x140092490 | `?cursor=N` | `{bootId, cursor, events[], resync, goingDown}` | long-poll on EventHub (≈1 s cap `[INFER]`), blocks server thread |
| GET | `/app-config` | 0x140092250 | – | 200 full AppConfig JSON (+`instanceId`) | read config |
| PATCH | `/app-config` | 0x140091790 | **partial** AppConfig | 200 **full merged** config + instanceId; 400 `{code,message,details}` (e.g. `BAD_REQUEST`, "Value cannot be greater than {max}. Detected {v}") | field-wise validate + merge into live config; applies side effects; may `PostMessage(WM_CLOSE)` if handler flags it (decomp:L124358) |
| POST | `/app-config/reset` | 0x140091550 | – | 200 default config + instanceId | factory-reset settings (hotkeys untouched) |
| GET | `/hotkeys` | 0x1400913b0 | – | 200 array of HotkeyEntry | read hotkeys |
| POST | `/hotkeys` | 0x140091180 (wparam 5) | HotkeyEntry (create) | single entry (UI ignores body, invalidates) | create entry, persist, `hotkeysChanged` |
| PUT | `/hotkeys` | 0x140090da0 (wparam 6) | full HotkeyEntry incl. `id` | updated entry (`tw` zod) | replace entry |
| DELETE | `/hotkeys/:id` | 0x140090ac0 (wparam 7) | – | – | delete; errors `INVALID_HOTKEY`/`NOT_FOUND` (cstr:L40077-40079) |
| POST | `/hotkeys/swap` | 0x140090770 (wparam 8) | `{hotkeyId1, hotkeyId2}` | – | reorder by swap; `CONFLICT` "Hotkey already in use" |
| POST | `/hotkeys/:id/duplicate` | 0x140090490 (wparam 9) | – | – | duplicate entry |
| POST | `/hotkeys/:id/toggle` | 0x140090140 (wparam 10) | – | – | flip `isEnabled` |
| POST | `/hotkeys/reset` | 0x14008ffa0 (wparam 11) | – | – | `FactoryResetHotkeysRoute` → default hotkey set |
| GET | `/shared-keybinds` | 0x14008fe00 | – | keybind sets | read shared (non-hotkey) keybinds |
| GET | `/shared-keybinds/defaults` | 0x14008fcb0 | – | defaults | |
| PUT | `/shared-keybinds/:classId` | 0x14008f2e0 | keybind set | – | update per-tool keybinds |
| POST | `/settings/import` | 0x14008e030 | `{version:1|2, appConfig, hotkeys, sharedKeybinds}` | 200 merged config + instanceId; 400 `invalidSettingsFile` | full replace; version checked (decomp:L121400-121430) |
| GET | `/tool-defaults` | 0x14008d900 | – | tool defaults | |
| GET | `/navigation-mode-presets` | **not registered in core** | – | 404 | UI-only (see Gaps) |
| GET | `/theme-catalog` | 0x14008d7c0 | – | `{themes:[…]}` | appearance picker |
| GET | `/app-bar-themes` | 0x14008ce30 | – | `{themes:[{name,bar:{background,border},mode,action,param}]}` (zod `aMe`) | app-bar theme list |
| GET | `/version` | 0x14008c910 | – | semver (UI zod `/^(\d+)\.(\d+)\.(\d+)$/`) | |
| GET | `/machine` | 0x14008c8d0 | – | machine info: `{detection, gpuAcceleratedRendering, keyboardLayouts:{status,value[{klid,…}]}, effectiveKeyboardLayout,…}` | System/Settings pages |
| GET | `/apps` | 0x14008c5e0 | – | `{…, defaultBrowser, detectedBrowsers[]}` | |
| GET | `/gpu-diagnostics` | 0x14008bff0 | – | GPU list (fields incl. `pciAddress`) | System page |
| POST | `/system/graphics-check` | 0x14008be50 | – | report(s) | runs probe exe (below) |
| GET | `/key-code-to-unicode-map` | 0x14008ad60 | – | code→unicode map | |
| GET | `/key-position-to-key-code-map` | 0x14008a8c0 | – | position→code map | |
| GET | `/update-info` | 0x14008a0f0 | – | `{available, latestVersion, releaseNotes?, …}` | About page |
| POST | `/update-check` | 0x140089280 | `{force}` | check progress (`checkCount`) | queries neverclick.com |
| POST | `/update` | 0x1400892c0 | – | – | download+sha256 verify → spawn updater `--install` (below) |
| POST | `/app/restart` | 0x1400890b0 | – | – | spawn updater `--launch <neverclick.exe>` + shut down |
| PATCH | `/nvidia-power-mode` | 0x1400889f0 | `{value}` | – | set NVIDIA power mode |
| GET/POST | `/voice-tools`, `/voice/available-models`, `/voice/engine-state` | **not present in core** | – | 404 | UI-only (see Gaps) |

Notable request/response details:
- Error envelope (cstr:L40064-40088): `{code, message, details?}` with codes
  `BAD_REQUEST` ("Malformed JSON", "Type mismatch in request", "'{}' is not a valid integer",
  "'{}' is out of range", "must be non-negative"), `NOT_FOUND`, `INVALID_HOTKEY`
  ("Hotkey ID: {}", "Hotkey not found"), `CONFLICT` ("Hotkey already in use", "Key combo: {}",
  "Class ID: {}", "Unknown tool class"). UI additionally parses a defensive
  `{errors:[{code,message}]}` shape from PATCH (`bwe`, `AppConfigPatchError`).
- PATCH is genuinely **partial**: the Settings page sends single-key bodies
  (`t.mutate({launchAtStartup: dt})` etc.) and caches the returned full config.
- All successful config responses embed `instanceId` (built via `FUN_1400d4780(&PTR_s_instanceId_)`,
  decomp:L124363, L123872, L121498).
- No static file mount: `index.html`/MIME strings at cstr:L39390 are cpp-httplib's built-in
  file-serving tables; `run()` registers no wildcard/mount route → **Tauri serves all UI**
  (via `tauri://localhost` custom protocol; bundle strings ustr:L73049,73338).

Update data flow (core, WinHTTP to `https://www.neverclick.com`, `/api/version` seen at
decomp:L5510; request fields `app_version, locale, instance_id`, response fields
`update{available, latest_version, download_url, sha256, release_notes, release_notes_url}`
cstr:L40044-40057): `POST /update-check` performs the query; `POST /update` downloads to an
absolute staging path, verifies `sha256`, then `FUN_1400d14d0` (decomp:L175369) spawns the
updater with `--install`.

---

## Settings schema & defaults

Storage: single object in `%AppData%\Roaming\Neverclick\app-config.json`
(known-folder GUID {3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}=RoamingAppData decomp:L55557,
subdir `"Neverclick"` decomp:L5516; filename join decomp:L84324).

Authoritative source: **default ctor `FUN_140057bd0`** (decomp:L76365) + **`to_json FUN_1400a6e30`**
(decomp:L140714, per-field `PTR_s_<key>` xrefs give offsets/types) + `.rdata` enum tables
(parsed: name↔value pairs, stride 24 B). Defaults below are fresh-install values; on load,
missing keys fall back to these (helpers `FUN_1400f6360/…3f0/…4b0/…560` return `{value,found}`
decomp:L205821+; migration `runOnStartup`→`launchAtStartup` decomp:L124133).

| JSON key | struct offset | type / enum | default | UI control (page) |
|---|---|---|---|---|
| `instanceId` | 0x00 | string UUID | nil UUID `"00000000-…"`; (re)generated via `UuidCreate` when absent/invalid (`FUN_1400ea5d0` decomp:L196664) | not shown |
| `theme.styleName` | 0x20 (i32 enum) | 46 palette names | `"Nevermore"` (0) | Appearance → theme picker (catalog) |
| `theme.drawHintBorders` | 0x24 (bool) | | **true** | Appearance → "Draw Hint Borders" |
| (theme flag) | 0x28 (u8) | | 0 `[INFER: named-style vs custom]` | – |
| `drawGlow` | 0x2c (bool) | | **false** | Appearance → "Enable Glow" |
| `drawBoundingBoxes` | 0x2d (bool) | | **true** | Appearance → "Draw Bounding Boxes" |
| `boundingBoxOpacity` | 0x30 (f32) | 0…1 (UI zod) | **1.0** | Appearance → "Bounding Box Opacity" (slider ÷100) |
| `hintBackgroundOpacity` | 0x34 (f32) | 0.5…1 (UI zod) | **1.0** | Appearance → "Hint Opacity" |
| `eventDelay` | 0x38 (i32) | ms; UI slider 10…30 | **10** | Settings → "Input Delay" (text "default is 10 ms") |
| `enableEventBatching` | 0x3c (bool) | | **true** | Settings → "Input Batching" |
| `enablePerfectDesktopAndTaskbarIconDetection` | 0x3d (bool) | | **true** | Settings → "Perfect Desktop and Taskbar Icon Detection" |
| `enableVisibilityToScreenCapture` | 0x3e (bool) | | **true** | Settings → "Screen Capture Visibility" |
| `launchAtStartup` | 0x3f (bool) | | **false** | Settings → "Launch at Startup" (shortcut in Startup folder; `AppConfigUpdater::updateRunOnStartup`) |
| `showStartupNotification` | 0x40 (bool) | | **true** | Settings → "Startup Notification" |
| `enableAnimations` | 0x41 (bool) | | **true** | Settings → "Animations" |
| `enableMouseAnimations` | 0x42 (bool) | | **true** | Settings → "Mouse Animations" |
| `enableWindowAnimations` | 0x43 (bool) | | **true** | Settings → "Window Animations" |
| `enableNotifications` | 0x44 (bool) | | **true** | Settings → "Notifications" |
| `enableUppercaseHints` | 0x45 (bool) | | **false** | Appearance → "Capitalization" (Uppercase/Lowercase) |
| `hintFontSize` | 0x48 (i32) | 8…24 (UI zod) | **16** | Appearance → "Font Size" |
| `hintFontName` | 0x50 (string) | one of bundled fonts | `"Inter"` | Appearance → "Font" |
| `keyCodes` | 0x70 (vector<int>, begin/end) | priority order of key positions | `[]` → runtime default key positions ("Using default key positions." cstr:L40286) | Settings → "Key Priority Editor" (reset sets `null`) |
| `keyOverrides` | ~0x88/0x90 (map) | `{key: "On"/"Off"}` (UI zod `b9`) | `{}` | Settings → "Key Priority Map" (reset sets `{}`) |
| `keyboardLayout` | 0xC8 (200, string) | layout id | `""` (with policy Auto) | Settings → "Keyboard Layout" select |
| `keyboardLayoutPolicy` | 0x150 (i32 enum) | `Auto=0, Manual=1` | **`Auto`** | Settings → "Keyboard Layout" (Auto/Manual) |
| `hintAssignment` | 0x154 (i32 enum) | `Random=0, CenterFirst=1` | **`CenterFirst`** | Appearance → "Hint Assignment" |
| `enableProgressiveHints` | 0x158 (bool) | | **false** | Appearance → "Progressive Hints" |
| `hintPlacement` | 0x15c (i32 enum) | `Centered=0, BelowCenter=1` | **`Centered`** | Appearance → "Hint Placement" |
| `fovMode` | 0x160 (i32 enum) | `Window=0, Monitor=1, AllMonitors=2` | **`AllMonitors`** | Settings → "Field of Vision" |
| `graphicsPreferencePolicy` | 0x164 (i32 enum) | `LetNeverclickDecide=0, LetWindowsDecide=1, HighPerformance=2, PowerSaving=3, Manual=4` | **`LetNeverclickDecide`** | System/Graphics-preference modal (`fDe`, PATCH `{graphicsPreferencePolicy}`) |
| `appBarTheme` | 0x168 (i32 enum) | 20 names (`Graphite=0, Peridot, Amber, Obsidian, Moss, Glacier, Basalt, Jade, Cobalt, Pewter, Marble, Amethyst, Porcelain, Frost, Opal, Sapphire, Celadon, Aquamarine, Tanzanite, Topaz`) | **`Graphite`** | tool-editor app-bar picker |
| `compactAppBar` | 0x16c (bool) | | **false** | tool-editor toggle |
| `vision.detectionModel` | 0x170 (i32 enum) | `Balanced=0, Narrow=1, UltraNarrow=2, Wide=3` | **`Balanced`** | Settings → "Detection Model" (Balanced=Recommended) |
| `vision.removeHallucinations` | 0x174 (bool) | | **true** | Settings → "Remove Hallucinations" |
| (3 unnamed strings at 0xE8, 0x108, 0x130) | strings | | `""` | not serialized by `to_json` — purpose unknown (one may be the vestigial `whisperModel`) |
| `whisperModel` | **not in core** | UI zod: `string\|null` *optional* | – | Voice page sends `{whisperModel}` via PATCH; core's PATCH validator has no such key → **dropped** (see Gaps) |

Notes:
- The serialized JSON nests `theme` (object `{styleName, theme, drawHintBorders}` — UI zod `g9`)
  and `vision` (`{detectionModel, removeHallucinations}`) exactly as the UI expects; flat
  `to_json` emission keys verified via `PTR_s_*` xrefs (decomp:L140810-141620).
- Legacy alias: PATCH accepts `runOnStartup` when `launchAtStartup` absent (decomp:L124133-124145).
- Numeric range validation exists generically ("Value cannot be greater than {}. Detected {}"
  cstr:L40321) but the exact per-field limits live in call-site args not fully recovered (Gaps).
- `whisperModel` is absent from core `to_json` and the PATCH key list (key-literal sweep of the
  whole decomp: `hintFontSize` occurs exactly once) — UI zod marks it optional, consistent with
  the server never returning it.

---

## Hotkey config format

File: `%AppData%\Roaming\Neverclick\hotkey-config.json.gz` — **gzip of JSON**
(zlib1.dll raw inflate/deflate; save path join decomp:L166150, JSON dump
`FUN_1400add70(...,5)` + gzip write `FUN_1400eecc0` decomp:L166157; load provider RTTI
`nvr::HotkeyEntriesFromDiskProvider(path) → HotkeyEntriesResult` cstr:L43148).
Siblings: `hotkey-config.v1.backup.json.gz` (pre-migration copy) and
`hotkey-config.corrupt.bak.json.gz` (unparseable original preserved);
backup write failure log "Failed to write hotkey config backup '{}': {}" in `FUN_140059160`
(decomp:L77603/77705). Backup-trigger semantics `[INFER: from filenames]`.

HotkeyEntry JSON (core serializer `FUN_1400ad250` decomp:L145410 writes
`"type":"hotkey"`, `"id"`, `"keyCombo"`, `"isEnabled"`, `"binding"`; UI discriminated union `tw/vF/qve`):

```
{ "type": "hotkey" | "error" | "unknown",
  "id":  <int>,
  "keyCombo": { "key": <KeyEnum>,            // nativeEnum: "KeyA".."KeyZ","Digit1".."Digit0",
                                       // "Escape","F1".."F24","Numpad*","Arrow*","Backslash"…
                "ctrl"?: "Left"|"Right"|"Either",
                "alt"? : "Left"|"Right"|"Either",
                "shift"?: "Left"|"Right"|"Either",
                "win"? : "Left"|"Right"|"Either" },
  "isEnabled": <bool>,
  "binding":  <tool binding discriminated on classId>   // type:"hotkey" member only
}
// type:"error"   → { type, id, title, description, raw }        (corrupt entry kept visible)
// type:"unknown" → { type, id, keyCombo, isEnabled, classId, rawBinding: {} }
```
- Chord encoding is an **object, not a string**; sided modifiers (`Left/Right/Either` —
  UI zod `J1`, Iv at bundle) — consistent with core key names `LeftShift/RightShift/LeftCtrl/…`
  (bundle `RN` map; core strings "Missing key combo" cstr:L40795).
- `binding` discriminated by `classId` over tool/action classes: observed literals
  `ScreenSearchTool`, `Clear`, `UndoHintSelection`, `Exit`, `RevealOverlappedHints`,
  `ToggleHintPlacement`, `GridMode`, `ClairvoyanceMode` + ~20 more (UI union `Kve/Uve/Gve`);
  core errors: "Class ID: {}", "Unknown tool class" (cstr:L40087).
- Serialization of a binding goes through a virtual (`"binding"` emission at decomp:L145621);
  failures produce the `error` entry ("[action_keybind_json] Failed to serialize key combo…"
  cstr:L40792-40804).

Shared keybinds (non-hotkey navigation keybinds) live in the same gz
(`performHotkeyConfigSave(SavingManager, CoreServices, vector<HotkeyEntry>, SharedKeybindSets)`
RTTI cstr:L43263) and in import/export files; entry shape
`{key, ctrl/alt/shift/win?: Either|Left|Right}` (UI `J8`); validation strings
"Expected an array of keybind entries.", "Invalid keybind entry",
"Invalid Pass Through keybind", "Duplicate keybind" (cstr:L40084-40086, L40801-40802).

Import/export (Settings page): export = `{version: 2, appConfig, hotkeys (ids stripped), sharedKeybinds}`
to `neverclick-settings.json` via save-dialog + `plugin:fs`
(bundle `d3e`; `u3e=2`); import = `POST /settings/import` accepting `version` 1 or 2
(decomp:L121400-121430) — full replace of all three sections.

Factory resets:
- `POST /hotkeys/reset` → `FactoryResetHotkeysRoute` (wparam 11) — default hotkey set only.
- `POST /app-config/reset` → `FactoryResetAppConfigRoute` (wparam 2) — defaults only,
  "Hotkeys are not affected" (UI label).
- Reset Key Priority (UI) = PATCH `{keyCodes:null, keyOverrides:{}}`.

---

## Tauri frontend map

### Binary & embedding
- `neverclick-ui.exe` 20.4 MB, sections .text/.rdata/.data/.pdata/.taubndl(16 B)/.rsrc/.reloc.
  `.taubndl` = `(ptr=0x140F168E0, count=3)` metadata.
- 66 web assets embedded in `.rdata` as **brotli** streams (crate `brotli-decompressor-5.0.0`
  ustr:L78335) in 32-byte structs `{path_ptr, path_len, bytes_ptr, bytes_len}`; extracted by
  `notes/scratch-configui/extract_ui_assets.py` → `extracted/ui-assets/` (66/66 ok).
- `index.html` → module `assets/index-CG8hdpTV.js` (1,419,862 B) + `assets/index-BknSijrv.css`
  (171,145 B); images: `neverclick-logo-y8Azypv6.png`, `hand-gold-B1NB6Ly5.png`,
  `update-image-Dga6cnl4.jpg`; 60 Inter/JetBrains-Mono woff/woff2 files.
- tauri.conf (ustr:L67858-67859): productName **"Neverclick UI"**, identifier
  **`com.neverclick.app`**, devUrl `http://localhost:5173`, frontendDist `../dist`,
  entry `src\main.rs`, icon `../../neverclick-core/Neverclick/resources/neverclick-logo.ico`.
- Stack: React 19 (react.element symbol), TanStack Query, **Ant Design** (`antd` motion/theme
  strings), dnd-kit (accessible drag-and-drop announcements), lucide-react 0.556, zod,
  tauri-plugin-{http,fs,dialog,shell,event,single-instance-2.3.6} (plugin invoke table ustr:L72913+).

### Shell / navigation
- Frameless window with `data-tauri-drag-region` titlebar (bundle `n9e`), menu
  `__tauri_window_menu__Window / Help` (ustr:L72850).
- Pages (`w9e` switch): **Neverclick** (`wPe`), **Voice** (`DFe`), **Appearance** (`ZPe` via `XPe`),
  **Settings** (`N4e`), **System** (`E6e`/`k6e`), **About** (`hBe`). Arrow keys cycle pages (`W3.of(LS).next/prev`).
- Connection banner driven by `hu()` context (health), red `#ef4444` / amber `#ffc107` status dot.

### Page → controls → config keys
**Neverclick (hotkeys)** — `cye` hook (GET `/hotkeys`): list with drag-reorder (swap → POST `/hotkeys/swap`),
duplicate/toggle/delete buttons, editor `BAe` (capture component `LN`, key-priority map `keyToUiMap` from
`/key-code-to-unicode-map`), categories incl. NavigationMode presets; save → POST/PUT `/hotkeys`;
duplicate-chord guard `bP(keyCombo, enabled)`; recovery flow `handleRecovery` for corrupt entries
(error-type rows offer recovery).

**Voice** — `/voice-tools` list + detail editor (`nFe`, localStorage `voiceCommand.viewMode`
compact|detailed), voice commands (`voiceKeys`, `otherCommands`), `TFe` whisper-model picker
(PATCH `{whisperModel}`). **All voice endpoints 404 on core 0.4.1** (Gaps).

**Appearance** (`ZPe`, props: appConfig, theme catalog, gpuAcceleratedRendering) —
Font (hintFontName), Font Size (hintFontSize, 8–24), Hint Opacity (hintBackgroundOpacity ÷100),
Bounding Box Opacity (boundingBoxOpacity ÷100), Draw Bounding Boxes (drawBoundingBoxes),
Enable Glow (drawGlow; turning on also forces drawBoundingBoxes=true), Draw Hint Borders
(theme.drawHintBorders), Hint Placement (hintPlacement: Centered|BelowCenter),
Hint Assignment (hintAssignment: Random|CenterFirst), Capitalization
(enableUppercaseHints: uppercase|lowercase), Progressive Hints (enableProgressiveHints);
theme style picker (styleName) from `/theme-catalog`.

**Settings** (`N4e`) — sections:
- *General*: Launch at Startup (launchAtStartup), Keyboard Layout (keyboardLayoutPolicy +
  keyboardLayout, Auto shows detected layout `effectiveKeyboardLayout`), Screen Capture
  Visibility (enableVisibilityToScreenCapture).
- *Animations*: Animations (enableAnimations), Mouse Animations, Window Animations,
  Notifications, Startup Notification (dependent enablement: notifications require animations
  in the UI, startup-notification requires both — UI gating only).
- *Detection*: Field of Vision (fovMode), Detection Model (vision.detectionModel),
  Remove Hallucinations (vision.removeHallucinations), Perfect Desktop/Taskbar icons.
- *Input*: Input Batching (enableEventBatching), Input Delay slider 10–30 ms (eventDelay).
- *Maintenance*: Import Settings (file dialog → POST `/settings/import`), Export Settings
  (`d3e` → save dialog + GET app-config/hotkeys/shared-keybinds → JSON file), Reset Hotkeys
  (POST `/hotkeys/reset`), Reset Key Priority (PATCH keyCodes:null, keyOverrides:{}),
  Reset All Settings (POST `/app-config/reset`).
- *Key panels*: `r3e` "Key Priority Map" (keyOverrides), `_4e` "Key Priority Editor" (keyCodes).

**System** (`k6e`) — Hardware & Displays: machine info (`/machine`) + GPU diagnostics
(`/gpu-diagnostics`, grouped by `pciAddress`), graphics preference modal (`fDe`) →
PATCH `{graphicsPreferencePolicy}`; nvidia power mode PATCH `/nvidia-power-mode`.

**About** (`hBe`) — "Neverclick v0.4.1 Beta", update card when `update-info.available`
("Update Available", latest version, release notes, install button → POST `/update`,
success modal uses `update-image` asset), background check `POe`: POST `/update-check {force:true}`
then poll update-info every 1 s up to 20× watching `checkCount`.

### Transport summary
Core data = HTTP only. Tauri invoke used solely for stock plugins:
`plugin:http|fetch` (all core calls), `plugin:fs|read/write_text_file` (import/export),
`plugin:dialog|open/save` (file pickers), `plugin:event|listen` (window focus),
`plugin:shell|open` (external links), `plugin:window|…` (drag/size). No custom commands.

---

## Helper exes

### neverclick-updater.exe (420,624 B)
Ghidra dump: `notes/scratch-configui/updater-decomp.c` (101 funcs). Signed (Microsoft Trusted
Signing certs in .rsrc); manifest `asInvoker`, dpiAware True/PM.

- Entry logic `FUN_140001940` (updater-decomp:L517): `GetCommandLineW` → `CommandLineToArgvW`;
  flag parser with errors "Failed to parse command line.", "Flag '<f>' is missing its value.",
  "Unknown flag: …".
- **Arguments** (L664-713): `--parent-pid <positive int>` (core), `--ui-pid <positive int>` (UI),
  and **exactly one** of `--launch <abs path>` | `--install <abs path>`
  (else "Exactly one of --launch or --install is required."; paths must be absolute via
  `PathIsRelativeW` → "The --launch/--install path must be absolute.").
- **Wait**: `OpenProcess(SYNCHRONIZE)` on both PIDs; `WaitForMultipleObjects(bWaitAll=TRUE)`:
  timeout = **INFINITE for `--install`**, **30 000 ms for `--launch`** (L783-790).
- **Act**: `ShellExecuteW(L"open", path, …)` (L807+):
  - `--launch` → params `NULL` (just reopen e.g. `neverclick.exe`).
  - `--install` → params
    **`/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /LAUNCHAPP=1 /MERGETASKS="!startup"`**
    → runs the downloaded **Inno Setup** installer silently, then the installer relaunches the app.
  - failure → `FUN_1400012c0` → MessageBoxW(title **"Neverclick Updater"**, MB_ICONERROR)
    with "Please launch Neverclick manually." (L485-491).
- No file-copy APIs at all (imports: KERNEL32/USER32/SHELL32/SHLWAPI + CRT only; zero
  MoveFile/CopyFile/CreateProcess) — **the updater never touches files itself**; download +
  sha256 verification happen in core (strings cstr:L40044-40057), installer does replacement.
- Who spawns it: core `FUN_1400d0860` (decomp:L174738) joins `<exe dir>\neverclick-updater.exe`
  (wide literal decomp:L174904) and builds
  `" --parent-pid <pid>"` + `" --ui-pid <pid>"` (decomp:L174992/175061); the `--ui-pid` part is
  included when it finds the **`neverclick-ui.exe`** window/process first
  (name literal decomp:L174943 → `GetWindowThreadProcessId`). Errors: "Updater binary not
  found at: " / "UPDATER_MISSING" / "UPDATER_SPAWN_FAILED" / "CreateProcess failed for updater
  (error " (cstr:L40058-40063); caller logs "Failed to spawn relauncher ({}): {}".
- Callers: `POST /update` → `FUN_1400d14d0` `--install` (decomp:L118392/L175369);
  `POST /app/restart` → `FUN_1400890b0` `--launch` (decomp:L117849); two more `--launch`
  relaunch sites (`FUN_1400b0bf0` decomp:L148456, `FUN_1400c3a60` decomp:L164650) `[INFER:
  restart-after-update / theme-restart flows]`.

### neverclick-graphics-check.exe (778,512 B)
Ghidra dump: `notes/scratch-configui/graphics-check-decomp.c` (611 funcs).

- **Input**: core `FUN_1400c6900` (decomp:L167226) spawns
  `L"neverclick-graphics-check.exe"` (decomp:L167339, sibling of neverclick.exe — else
  "Probe binary not found next to neverclick.exe.") with one of
  **`--preference=1` / `--preference=2` / `--preference=none`** (decomp:L167357-16764).
- **What it tests** (strings): `CreateDXGIFactory1` (+ `IDXGIFactory6` preferred, fallback
  Factory1: "Failed to create IDXGIFactory6, falling back to IDXGIFactory1. Update Windows to
  fix this issue."), D3D11 device creation, Direct2D factory/device/device-context,
  `IDXGIAdapter1` + adapter description, `IDXGIOutput1` → **`DuplicateOutput`** (desktop
  duplication / screen capture capability: "DuplicateOutput failed: {}"), output description,
  `dedicatedVideoMemory`, registry GPU-preference apply/restore
  ("Failed to apply registry preference", create/set/delete registry value — GfxPreference).
- **Output**: nlohmann-json object containing at least a **`"gpus"` array** (decomp:26918/29939)
  with per-GPU fields incl. `dedicatedVideoMemory`; failures surface as `"Failed to …"` messages.
  Exit code: process exit status is captured by core into the report.
- **Core wrapper** `FUN_1400c6900` builds a JSON report keyed
  `preference`, `exitCode`, `trace`, `error`, `report`, `rawOutput` (decomp:L167406-167587;
  "Process failed to launch." on spawn failure) — served through `POST /system/graphics-check`;
  cached diagnostics served by `GET /gpu-diagnostics`.

---

## Install layout

- Installer: Inno Setup 6.7.0 (`notes/00-findings.md`), copy `installer/neverclick-setup-0.4.1.exe`
  (15.6 MB; innoextract 1.9 cannot unpack this revision — payload already extracted to
  `extracted/app/` by the project's patched toolchain).
- Payload (`extracted/app/` = Program Files content): `neverclick.exe` (4.53 MB),
  `neverclick-ui.exe` (20.4 MB), `neverclick-updater.exe`, `neverclick-graphics-check.exe`,
  `SDL2.dll`, `onnxruntime.dll` (12 MB), `zlib1.dll`, VC++ 2015-2022 runtimes
  (`msvcp140*.dll`, `vcruntime140*.dll`, `concrt140.dll`), `fonts/` (11 TTF), `licenses/`.
  `extracted/tmp/MicrosoftEdgeWebview2Setup.exe` = WebView2 **Evergreen bootstrapper**
  (Tauri/WebView2 dependency; shipped separately, run at install `[INFER]`).
- Install dir: **Program Files** — upstream README: "installs to Program Files because Windows
  requires that for it to register as an accessibility tool" (notes/public/README-upstream.md:208)
  → `C:\Program Files\Neverclick\` `[INFER for exact name]`. Runs elevated-UIPI capable.
- **Uninstaller**: no `unins000.*` in the extracted payload — normal (Inno generates the
  uninstaller at install time; installer strings show `UninstallFilesDir`,
  `CreateUninstallRegKey`, `UninstallDisplayName`). No evidence of its absence on a real system.
- Autostart: `launchAtStartup` managed by core (`AppConfigUpdater::updateRunOnStartup` +
  "Failed to add/remove Neverclick from/to startup folder" cstr:L151958/152000,
  `.lnk` handling `FUN_140114850` decomp:L231787) → **.lnk in the user Startup folder**
  (target exe not directly evidenced — `[INFER: neverclick.exe` since core owns tray+engine;
  installer has no Run-entry strings visible]. Shortcut display name candidate `"Neverclick"`
  (wide literal decomp:L150565)).
- Runtime data: `%AppData%\Roaming\Neverclick\{app-config.json, hotkey-config.json.gz,
  hotkey-config.v1.backup.json.gz, hotkey-config.corrupt.bak.json.gz}`.
- WebView2 runtime: required by `neverclick-ui.exe`; bootstrapper ships as
  `MicrosoftEdgeWebview2Setup.exe`.

---

## Gaps / unresolved

1. **Voice & navigation-preset endpoints** — `/voice-tools`, `/voice/{available-models,engine-state}`,
   `/navigation-mode-presets` are called by the shipped UI but contain zero bytes in
   `neverclick.exe`; they 404 on this core (spec: either stub-404 or the UI build is ahead of the
   core module set). Exact UI failure display for these pages not fully traced.
2. **Numeric range limits** for core-side field validation ("Value cannot be greater than {}")
   not recovered — they are passed as arguments inside `FUN_1400f6360/…` call sites whose
   descriptor initialization blocks were not fully located. UI zod gives partial bounds
   (opacity 0–1 / 0.5–1, hintFontSize 8–24, eventDelay int≥0).
3. **Config load/merge window-proc**: the actual window-message switch (wparam 0–11) that
   performs merge/reset/load was not pinned to a single function; behaviors reconstructed from
   route adapters (`SendMessageW` sites) and the shared helpers.
4. **`index.html` in core strings**: cpp-httplib file-serving table; no mount registered in
   `run()` — concluded core never serves it, but no explicit "no static routes" proof beyond
   the complete route enumeration.
5. **PATCH semantic errors**: whether any validation path returns HTTP 200 with
   `{errors:[…]}` (UI defends against it) vs only 400 `{code,message}` — core shows only the
   400 builder `FUN_1400d2600(param_3,400,…)`; the `{errors}` shape may be legacy.
6. **Unnamed config strings** at offsets 0xE8/0x108/0x130 (empty, never serialized) — possibly
   `whisperModel`-era fields.
7. **Who starts the UI on login**: tray-Open launch proven; whether the installer also creates a
   Start-Menu/Run entry for `neverclick-ui.exe` (compressed Inno [Run]/[Icons] not unpacked).
8. **Update-check endpoint details**: exact neverclick.com path beyond `"/api/version"`
   (decomp:L5510) and request/response wiring only partially traced (fields cstr:L40055+).
9. **`/health`, `/version`, `/machine` exact bodies**: handlers not decomp-read; schemas taken
   from UI zod only.

---

## Spec-ready statements

1. Core exposes an unauthenticated HTTP API on **`0.0.0.0:7340`** (all interfaces); clients use
   `http://127.0.0.1:7340`. Any LAN host can reconfigure the app — a reimplementation should
   reproduce (or deliberately fix) this.
2. API surface = the **HTTP API table** above (29 registered routes; methods/paths/handler
   effects verified against both binaries). Config semantics: `GET` returns the full object,
   `PATCH` merges arbitrary subsets field-by-field with per-field validation
   (400 `{code,message,details}` on failure, full merged object on success), `POST …/reset`
   returns defaults. Every config response embeds `instanceId`.
3. Server-to-client change notification = **poll-based**: `GET /events?cursor=N` long-poll
   returning `{bootId, cursor, events[], resync, goingDown}` with events
   `hotkeysChanged | appConfigChanged | keyboardLayoutChanged`; `bootId` change ⇒ full resync.
4. `app-config.json` schema + defaults = **Settings schema & defaults table** (36 keys incl.
   nested `theme` and `vision`; enum domains fully enumerated; defaults from ctor `FUN_140057bd0`).
   File format: single JSON object, rewritten atomically by `SavingManager`
   (`performAppConfigSave` RTTI cstr:L43264).
5. `hotkey-config.json.gz` = gzip JSON holding the HotkeyEntry array + shared keybind sets;
   entry = `{type,id,keyCombo{key,ctrl?,alt?,shift?,win?},isEnabled,binding}` with
   sided modifier enum `Left|Right|Either`; corrupt entries surface as `type:"error"` rows and
   are preserved to `hotkey-config.corrupt.bak.json.gz`; `v1` configs preserved to
   `hotkey-config.v1.backup.json.gz` on migration.
6. Settings GUI = one Tauri 2.9.4 window, six pages (neverclick/hotkeys, voice, appearance,
   settings, system, about), React+Ant Design bundle served from embedded brotli assets; all
   backend calls are plain HTTP fetch via `tauri-plugin-http`; Tauri invoke is stock plugins only.
7. Process relationships: single-instance core (mutex `n3v3rcl1ck` + window class `Neverclick`);
   tray menu {&Open, Suspend/Resume, Sleep/Wake, Exit}; **Open ⇒ ShellExecute `neverclick-ui.exe`
   next to the core exe**; UI single-instance via tauri-plugin-single-instance; UI drives core
   through `/health` (backoff 200 ms→3 s) and `/events`.
8. Update flow: core (WinHTTP) checks `https://www.neverclick.com` with
   `{app_version, locale, instance_id}`, receives `{available, latest_version, download_url,
   sha256, release_notes…}`, downloads+verifies, then spawns
   `neverclick-updater.exe --install <abs setup.exe> --parent-pid <pid> [--ui-pid <pid>]`;
   updater waits for both processes (infinite) and runs the installer
   `/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /LAUNCHAPP=1 /MERGETASKS="!startup"`;
   `POST /app/restart` uses `--launch <neverclick.exe>` with a 30 s wait.
9. GPU probe: `neverclick-graphics-check.exe --preference=1|2|none` prints a JSON report
   (`gpus[]` with adapter/dedicatedVideoMemory, DuplicateOutput capability, D2D/D3D11/DXGI
   error strings); core wraps it as `{preference, exitCode, trace, error, report, rawOutput}`
   via `POST /system/graphics-check` and caches results in `GET /gpu-diagnostics`.
10. Install: Program Files payload (4 exes + SDL2 + onnxruntime + zlib + VC++ runtimes +
    fonts/licenses) with WebView2 bootstrapper; per-user data in
    `%AppData%\Roaming\Neverclick\`; autostart implemented as a Startup-folder shortcut
    managed by the core (`launchAtStartup`).
