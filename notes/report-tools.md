# Neverclick 0.4.1 — Tool / action catalog and factory configuration

> **Artifact availability.** The extracted UI bundle (`extracted/ui-assets/`), the original binaries and
> `ghidra/neverclick-decomp.c` have been removed from this tree; the salvaged catalog
> (`notes/scratch-tools/ui-catalog.tsv`) and this report remain. The §1 recipe that read the bundle is
> retained as method only — its input is no longer present.

Scope: enumerate every bindable tool and action with its `classId`, category, display name and known
parameters, and reconstruct the factory (first-run) hotkey configuration.

Sources: the shipped UI bundle `extracted/ui-assets/assets/index-CG8hdpTV.js` (the settings app's
discriminated union and its **authoritative JSON field names**), the salvaged catalog
`notes/scratch-tools/ui-catalog.tsv` (80 entries, extracted from the bundle), `ghidra/neverclick-decomp.c`
(compiled-in default keybind builders, tool/action vtables), and the existing reports
(`notes/report-interaction.md` §Config/§Window/§Mouse, `notes/report-hints.md`, `notes/report-config-ui.md`).

## 1. How to extend this catalog (method)

```bash
# 1. classIds + display strings (the TSV used below is the output of this step)
python3 - <<'EOF'
import re
js=open('extracted/ui-assets/assets/index-CG8hdpTV.js',encoding='utf-8',errors='ignore').read()
for m in re.finditer(r'classId\s*:\s*"([A-Za-z0-9_]+)"', js): print(m.group(1))
EOF
# 2. JSON field names per classId = the zod object that follows the classId literal (±400 chars context)
# 3. core-side registration: grep the binary for the same literal to see which classes the core implements
strings -a extracted/app/neverclick.exe | grep -F "ScreenSearchTool"
```
The TSV columns are `classId<TAB>category<TAB>displayName<TAB>description`.

## 2. Catalog (80 entries)

Machine-readable: `notes/scratch-tools/ui-catalog.tsv`. Rendered:

| classId | category | name | description |
|---|---|---|---|
| `ClickOnWindow` | Mouse Actions | Click on Window | Clicks at a relative position on the active window. |
| `HighlightMouse` | Mouse Actions | Highlight Mouse | Highlights the mouse cursor position. |
| `MouseButton` | Mouse Actions | Mouse Button | Holds down, releases, or toggles a mouse button. |
| `MouseSlot` | Mouse Actions | Mouse Slot | Save or activate a mouse position from a numbered slot. |
| `MoveMouse` | Mouse Actions | Move Mouse | Moves the mouse cursor in the specified direction by a set amount. |
| `RepeatLastMouseAction` | Mouse Actions | Repeat Last Mouse Action | Repeats the last mouse action performed. |
| `Scroll` | Mouse Actions | Scroll | Scrolls in the specified direction by a set amount. |
| `TeleportMouse` | Mouse Actions | Teleport Mouse | Moves the mouse instantly to a set position on the active window or screen. |
| `WiggleMouse` | Mouse Actions | Wiggle Mouse | Wiggles the mouse cursor. |
| `Zoom` | Mouse Actions | Zoom | Zooms in or out in apps that support Ctrl+Scroll. |
| `ActionSlot` | System Actions | Action Slot | Save, clear, or execute an action from a numbered slot. |
| `ActivateVoiceTool` | System Actions | Activate Voice Tool | Activates the named voice tool. |
| `ExitNeverclick` | System Actions | Exit Neverclick | Closes Neverclick completely. |
| `GoBack` | System Actions | Go Back | Navigate back in an application's history. |
| `GoForward` | System Actions | Go Forward | Navigate forward in an application's history. |
| `MuteVolume` | System Actions | Mute Volume | Toggles volume mute. |
| `OpenApplication` | System Actions | Open Application | Opens an application, or switches to it if already running. |
| `OpenSettings` | System Actions | Open Settings | Opens the Neverclick settings window. |
| `RestartNeverclick` | System Actions | Restart Neverclick | Closes and reopens Neverclick. |
| `RunShellCommand` | System Actions | Run Shell Command | Executes a shell command with configurable action, URI, and parameters. |
| `SleepNeverclick` | System Actions | Sleep Neverclick | Suspends all hotkeys and releases resources. Press again to wake. |
| `SuspendNeverclick` | System Actions | Suspend Neverclick | Suspends all hotkeys except this one. Press again to resume. |
| `ToggleAppBar` | System Actions | Toggle App Bar | Toggles the Neverclick app bar. |
| `ToggleVoiceRecognition` | System Actions | Toggle Voice Recognition | Turns voice recognition fully on or off. |
| `VirtualDesktop` | System Actions | Virtual Desktop | Switch, create, or close virtual desktops. |
| `VolumeDown` | System Actions | Volume Down | Decreases the system volume. |
| `VolumeUp` | System Actions | Volume Up | Increases the system volume. |
| `Copy` | Text & Input Actions | Copy | Copies the selected text. |
| `Cut` | Text & Input Actions | Cut | Cuts the selected text. |
| `Find` | Text & Input Actions | Find | Opens the find dialog. |
| `InsertText` | Text & Input Actions | Insert Text | Types the specified text at the current cursor position. |
| `JumpWordLeft` | Text & Input Actions | Jump Word Left | Jumps the cursor one word to the left. |
| `JumpWordRight` | Text & Input Actions | Jump Word Right | Jumps the cursor one word to the right. |
| `JumpToFirstLine` | Text & Input Actions | Jump to First Line | Jumps to the first line. |
| `JumpToLastLine` | Text & Input Actions | Jump to Last Line | Jumps to the last line. |
| `KeyPress` | Text & Input Actions | Key Press | Executes a sequence of key press events. |
| `NewLineAbove` | Text & Input Actions | New Line Above | Inserts a new line above the cursor. |
| `NewLineBelow` | Text & Input Actions | New Line Below | Inserts a new line below the cursor. |
| `OpenFile` | Text & Input Actions | Open File | Opens the file open dialog. |
| `Paste` | Text & Input Actions | Paste | Pastes from clipboard. |
| `Redo` | Text & Input Actions | Redo | Redoes the last undone action. |
| `Save` | Text & Input Actions | Save | Saves the current document. |
| `SelectAll` | Text & Input Actions | Select All | Selects all content. |
| `SelectWordLeft` | Text & Input Actions | Select Word Left | Selects the word to the left. |
| `SelectWordRight` | Text & Input Actions | Select Word Right | Selects the word to the right. |
| `SwitchTab` | Text & Input Actions | Switch Tab | Switches between tabs in the active application. |
| `TextSlot` | Text & Input Actions | Text Slot | Copy or paste text to/from a numbered slot. |
| `Undo` | Text & Input Actions | Undo | Undoes the last action. |
| `AppLauncher` | Tools | App Launcher | Launch or switch into running apps. |
| `BasicMouseActionTool` | Tools | Double Click Tool | Use computer vision to perform a double click with your keyboard. |
| `DragTool` | Tools | Drag Tool | Use computer vision to click and drag with your keyboard. |
| `FolderOpener` | Tools | Folder Opener | Open folders quickly with hints. |
| `BasicMouseActionTool` | Tools | Left Click Tool | Use computer vision to perform a left click with your keyboard. |
| `BasicMouseActionTool` | Tools | Middle Click Tool | Use computer vision to perform a middle click with your keyboard. |
| `BasicMouseActionTool` | Tools | Mouse Move Tool | Use computer vision to move the mouse with your keyboard. |
| `NavigationMode` | Tools | Navigation Mode | Remap your keyboard to navigate, scroll, and interact with your screen. |
| `QuickActionMenu` | Tools | Quick Action Menu | Bind tools and actions to a keyboard-driven menu. |
| `BasicMouseActionTool` | Tools | Right Click Tool | Use computer vision to perform a right click with your keyboard. |
| `ScreenSearchTool` | Tools | Screen Search Tool | Find every occurrence of the specified UI elements. |
| `StickyHintsTool` | Tools | Sticky Hints Tool | Save hints for quick repeat clicking. |
| `SuperAltTab` | Tools | Super Alt Tab | Switch between apps. |
| `TextSelectionTool` | Tools | Text Selection Tool | Use computer vision to select text with your keyboard. |
| `BasicMouseActionTool` | Tools | Triple Click Tool | Use computer vision to perform a triple click with your keyboard. |
| `WindowCloser` | Tools | Window Closer | Close one or more windows. |
| `WindowMoveTool` | Tools | Window Move Tool | Move the foreground window with your keyboard. |
| `WindowSnappingTool` | Tools | Window Snapping Tool | Snap windows to a grid layout with your keyboard. |
| `CloseWindow` | Window Actions | Close Window | Closes the active window. |
| `CycleWindows` | Window Actions | Cycle Windows | Cycles through open windows, with an optional monitor filter. |
| `FocusWindow` | Window Actions | Focus Window | Switches to the closest window in any direction. |
| `HighlightActiveWindow` | Window Actions | Highlight Active Window | Highlights the active window. |
| `MinimizeOthers` | Window Actions | Minimize Others | Minimizes all windows except the active one. |
| `MinimizeWindow` | Window Actions | Minimize Window | Minimizes the active window. |
| `MoveWindow` | Window Actions | Move Window | Nudge, center, or send the active window to another monitor or virtual desktop. |
| `PreviousWindow` | Window Actions | Previous Window | Switches to the last used window, like a single Alt+Tab, with an optional monitor filter. |
| `ResizeWindow` | Window Actions | Resize Window | Resizes the active window by a set amount. |
| `SearchForWindow` | Window Actions | Search for Window | Finds and activates a window by name or process. |
| `TileWindows` | Window Actions | Tile Windows | Tiles windows on the current monitor. |
| `ToggleAlwaysOnTop` | Window Actions | Toggle Always On Top | Toggles the active window between always on top and normal. |
| `ToggleWindow` | Window Actions | Toggle Window | Toggles the active window between maximized and restored. |
| `WindowLayoutSlot` | Window Actions | Window Layout Slot | Save or activate a window layout from a numbered slot. |
| `WindowSlot` | Window Actions | Window Slot | Save or activate a window from a numbered slot. |

## 3. Core-supported vs UI-only

The UI ships a superset of what the 0.4.1 core implements:

- **Core-backed (modes, verified via RTTI/vtables in `neverclick.exe`)**: `BasicMouseActionTool`,
  `StickyHintsTool`, `WindowMoveTool`, `WindowSnappingTool`, `ScreenSearchTool`, `MoveMouse`, `Scroll`,
  `Zoom`, `WiggleMouse`, `MouseSlot`, `ClickOnWindow`, `TeleportMouse`, `MouseButton`,
  `FocusWindow`, `CycleWindows`, `PreviousWindow`, `MoveWindow`, `MoveWindowToMonitor`,
  `MoveWindowToEdge`, `MoveWindowToVirtualDesktop`, `VirtualDesktop`, `TileWindows`, `ResizeWindow`,
  `ToggleWindow`, `MinimizeWindow`, `MinimizeOthers`, `CloseWindow`, `HighlightActiveWindow`,
  `WindowCloser`, `SuperAltTab`/`FocusWindowBehind`, `SearchForWindow`, `KeyPress`, `InsertText`,
  `Copy/Cut/Paste/Undo/Redo/Save/Find/SelectAll`, `JumpWordLeft/Right`, `NewLineAbove/Below`,
  `JumpToFirstLine/LastLine`, `TextSlot`, `ActionSlot`, `WindowSlot`, `MouseSlot`,
  `ToggleAppBar`, `OpenSettings`, `SuspendNeverclick`, `SleepNeverclick`, `RestartNeverclick`,
  `ExitNeverclick`, `OpenApplication`, `RunShellCommand`, `GridMode`/`ClairvoyanceMode`/`VisionMode`,
  `SetFieldOfVision`/`ToggleFieldOfVision`, `SnapTargets`/`MoveTargets`, `DualSelect`/`MultiSelect`/`PathSelect`,
  `FinishSelection`, `UndoHintSelection`, `RevealOverlappedHints`, `RefreshHints`, `ToggleHintPlacement`,
  `Clear`, `ToggleModifiers`, `SetLayout`, `RegionSelect`, `FocusWindowBehind`, `ShiftFocus`.
- **UI-only in 0.4.1 (no core routes/classes → the pages 404)**: `VoiceCommandTool`,
  `VoiceDictationTool`, `MetaVoiceTool`, `LegacyVoiceCommandTool`, `ToggleVoiceRecognition`,
  `ActivateVoiceTool`, `NavigationMode`, `SetLayout`/`QuickActionMenu` presets,
  `TextSelectionTool`, `DragTool`, `AppLauncher`, `FolderOpener` (some of these exist as *tool classes*
  in the UI union only; see `notes/report-config-ui.md` §Gaps).

## 4. Known parameters per class (JSON field names from the bundle; semantics from the core)

| classId | parameters (JSON) | semantics |
|---|---|---|
| `BasicMouseActionTool` | `keyCombo`, `keybinds`, `mouseActionModifiers`, `visionStrategy`, `finalMousePosition` (+ tool instance config) | left/right/middle/double/triple click / mouse move; the instance's click type comes from the binding |
| `Scroll` | `direction`, `mouseTarget`, `config` | dir 0/1 = vertical ±, 2/3 = horizontal ∓; `mouseData = ±120 × amount`; warp-to-window only if the cursor is outside the fg window frame |
| `Zoom` | (as `Scroll`) | Ctrl + wheel |
| `MoveMouse` | `direction`, `mouseTarget`, `config` | absolute move by `amount` px (directions 0..3 = left/right/up/down) |
| `WiggleMouse` | `config` | 10 iterations of ±20 px at the cursor or at a window fraction (0.5, 0.3) |
| `MouseSlot` | slot index, `mouseTarget` | 8 slots; absolute or window-relative (normalized fraction) |
| `ClickOnWindow` | `fractionX`, `fractionY` | click at `frame.left + w·fx, frame.top + h·fy`, implemented as move → down → up (two inputs, one tick apart) |
| `TeleportMouse` | position, `mouseTarget` | instant absolute move |
| `MouseButton` | button, action (hold/release/toggle) | `MOUSEEVENTF_{LEFT,RIGHT,MIDDLE}{DOWN,UP}` |
| `FocusWindow` | `direction` (0=Left,1=Right,2=Up,3=Down,4=Behind) | geometric half-plane picker, 15 % perpendicular margin, min-distance tie-break |
| `CycleWindows` | `direction` (0=Forward,1=Backward), scope (through-overlapping / same-monitor / across-monitors / all) | Forward sends the old fg window to the bottom; Backward does not reorder |
| `PreviousWindow` | monitor filter | single Alt+Tab semantics |
| `MoveWindow` | `direction` (0..3), `target` (0=Pixels,1=Monitor,2=Desktop,3=Edge,4=Center,5=Back), `amount`, `maximize` | nudge/center/edge/monitor/desktop; monitor move requires exact edge abutment (no wrap) |
| `MoveWindowToMonitor` / `MoveWindowToEdge` / `MoveWindowToVirtualDesktop` | direction / edge position / desktop op | specialisations of `MoveWindow` |
| `VirtualDesktop` | op (0=switch left,1=switch right,2=new,3=close) | injected `Ctrl+Win+←/→/D/F4`; move-window uses `IVirtualDesktopManager` |
| `TileWindows` | style (`Fit`/`FrontTwo`/`Fill`) | nearest-center cell assignment; Fit = `scale = min(cellW/w, cellH/h)` centered, else fill |
| `ResizeWindow` | direction, amount | relative resize |
| `WindowSnappingTool` | `initialLayout`, `references`, `keybinds`, `visionStrategy`, `finalMousePosition` | single `SetWindowPos` to `union(old,new)` |
| `WindowMoveTool` | direction, stride tiers (±200 / ±50 / ±10) | move the foreground window |
| `WindowSlot` / `WindowLayoutSlot` | slot index | save/restore window or layout |
| `StickyHintsTool` | `persistence` (`OnePress`/`Persistent`), `closeBehavior`, `keyAssignment` (`Automatic`/`Manual`), `keybinds`, `visionStrategy` (`ScreenPosition`/`ImageRecognition`), `finalMousePosition`, `anchor`, `references` | saved hints; auto key assignment reuses the hint combo generator |
| `TextSlot` | slot index | copy/paste text to numbered slots |
| `ActionSlot` | slot index, action | save/clear/execute a bound action |
| `ScreenSearchTool` | `keyCombo`, `keybinds`, `references`, `visionStrategy`, `finalMousePosition` | find occurrences of a UI element (uses the template matcher) |
| `KeyPress` | key sequence | synthesised key events with the `0x147d` marker |
| `InsertText` | text | types text |
| `RunShellCommand` | action/verb, URI, parameters | `ShellExecuteExW` |
| `OpenApplication` | app id/path | `ShellExecuteExW`, "runas" allowed for user-chosen targets |
| `SuspendNeverclick` / `SleepNeverclick` | – | hotkey state machine toggles (states 1 / 2) |
| `ToggleAppBar` | – | shows/hides the docked app bar |
| `SnapTargets` | `direction`, `percentX`, `percentY` | digits 1–9 → `percentX=(d−1)/8, percentY=0.5` |
| `MoveTargets` | `direction`, `strideX`, `strideY` | arrows / Shift+JIKL → stride ±4 (second chord ±2), first press snaps to the box edge |
| `SetFieldOfVision` / `ToggleFieldOfVision` | mode | `FovMode` 0/1/2 |

Parameter *ranges* and remaining per-class fields are defined by the bundle's zod schemas; read them with
the method of §1 if a stricter contract is needed.

## 5. Dispatch / action ids (core)

`[V]` from `report-hints.md` §Follow-up (`FUN_14019ba50` case table) and `report-interaction.md`:

| id | action | id | action |
|---|---|---|---|
| 1 | Clear | 0x0b | SetFieldOfVision |
| 2 | UndoHintSelection (Esc default) | 0x0c | FocusWindow |
| 4 | RevealOverlappedHints | 0x0e | MoveTargets |
| 5 | ToggleHintPlacement | 0x0f | SnapTargets |
| 6 | GridProvider (Grid mode) | 0x10 | CycleWindows |
| 7 | Clairvoyance mode | 0x11 | FocusWindowBehind (Shift+Z default) |
| 8 | Vision mode (Shift+R default) | 0x12 | SearchForWindow (Shift+F default) |
| 9 | RefreshHints | 0x15 | FinishSelection (Enter) |
| 0x0a | ToggleFieldOfVision (Tab) | | |

Tool instances are resolved by the `GetName()` strings; the state machine matches on
`SuspendNeverclick` / `SleepNeverclick`.

## 6. Factory (first-run) configuration

Compiled-in default keybinds are **code, not data** — there are no `"Ctrl+Enter"` literals in the binary.
Two appenders build them: `FUN_1401683f0` (actions) and `FUN_140166770` (tools), plus the window/nav
table `FUN_140175660` (`report-interaction.md` §Config). Verified subset (`[V]`), joined with the
documented activation hotkeys (`[D]` = upstream docs/Register):

| chord | binding | evidence |
|---|---|---|
| `Ctrl+Enter` | Left Click Tool (`BasicMouseActionTool`, left click) | `[D]` (README "press Ctrl+Enter to activate the Left Click Tool") |
| `Alt+Enter` | Ctrl+Left Click (`BasicMouseActionTool`, left click + Ctrl modifier) | `[D]` (Register: "Ctrl+Enter for left-click or Alt+Enter for Ctrl+Left Click") |
| `Shift+W` | `FocusWindow` dir Up (2) | `[V]` |
| `Shift+A` | `FocusWindow` dir Left (0) | `[V]` |
| `Shift+S` | `FocusWindow` dir Down (3) | `[V]` |
| `Shift+D` | `FocusWindow` dir Right (1) | `[V]` |
| `Shift+Q` | `CycleWindows` Backward (1) | `[V]` |
| `Shift+E` | `CycleWindows` Forward (0) | `[V]` |
| `Shift+Z` | `FocusWindowBehind` | `[V]` |
| `Shift+F` | `SearchForWindow` (0x12) | `[V]` |
| `Shift+R` | Vision mode (8) | `[V]` |
| `Esc` | `UndoHintSelection` (2) | `[V]` |
| `Backspace` | action 8 | `[V]` |
| `Space` | (bound, action unresolved) | `[V]` |

Hint-tool keybinds (while hints are up; `[V]` `notes/report-hints.md` §Follow-up): letters = hint labels;
digits `1`–`9` = `SnapTargets{percentX=(d−1)/8, percentY=0.5}` (`0` unbound); arrows and `Shift+JIKL` =
`MoveTargets` (±4, second chord ±2); `Tab` = `ToggleFieldOfVision`; `[` = Clairvoyance; `;` = Grid;
`'` = dual select; `Shift+'` = multi select; `Ctrl+'` = path select; `Enter` = `FinishSelection`;
`Esc` = `UndoHintSelection`.

**Bootstrap document** (drop-in for a fresh install; structurally valid per `report-config-ui.md`
§Hotkey config format; ids arbitrary but stable):

```json
{
  "version": 2,
  "hotkeys": [
    {
      "type": "hotkey",
      "id": 1,
      "isEnabled": true,
      "keyCombo": {
        "key": "Enter",
        "ctrl": "Either"
      },
      "binding": {
        "classId": "BasicMouseActionTool",
        "mouseAction": "LeftClick",
        "mouseActionModifiers": []
      }
    },
    {
      "type": "hotkey",
      "id": 2,
      "isEnabled": true,
      "keyCombo": {
        "key": "Enter",
        "alt": "Either"
      },
      "binding": {
        "classId": "BasicMouseActionTool",
        "mouseAction": "LeftClick",
        "mouseActionModifiers": [
          "Ctrl"
        ]
      }
    },
    {
      "type": "hotkey",
      "id": 3,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyW",
        "shift": "Either"
      },
      "binding": {
        "classId": "FocusWindow",
        "direction": "Up"
      }
    },
    {
      "type": "hotkey",
      "id": 4,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyA",
        "shift": "Either"
      },
      "binding": {
        "classId": "FocusWindow",
        "direction": "Left"
      }
    },
    {
      "type": "hotkey",
      "id": 5,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyS",
        "shift": "Either"
      },
      "binding": {
        "classId": "FocusWindow",
        "direction": "Down"
      }
    },
    {
      "type": "hotkey",
      "id": 6,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyD",
        "shift": "Either"
      },
      "binding": {
        "classId": "FocusWindow",
        "direction": "Right"
      }
    },
    {
      "type": "hotkey",
      "id": 7,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyQ",
        "shift": "Either"
      },
      "binding": {
        "classId": "CycleWindows",
        "direction": "Backward"
      }
    },
    {
      "type": "hotkey",
      "id": 8,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyE",
        "shift": "Either"
      },
      "binding": {
        "classId": "CycleWindows",
        "direction": "Forward"
      }
    },
    {
      "type": "hotkey",
      "id": 9,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyZ",
        "shift": "Either"
      },
      "binding": {
        "classId": "FocusWindowBehind"
      }
    },
    {
      "type": "hotkey",
      "id": 10,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyF",
        "shift": "Either"
      },
      "binding": {
        "classId": "SearchForWindow"
      }
    },
    {
      "type": "hotkey",
      "id": 11,
      "isEnabled": true,
      "keyCombo": {
        "key": "KeyR",
        "shift": "Either"
      },
      "binding": {
        "classId": "VisionMode",
        "mode": "Vision"
      }
    },
    {
      "type": "hotkey",
      "id": 12,
      "isEnabled": true,
      "keyCombo": {
        "key": "Escape"
      },
      "binding": {
        "classId": "UndoHintSelection"
      }
    },
    {
      "type": "hotkey",
      "id": 13,
      "isEnabled": true,
      "keyCombo": {
        "key": "Backspace"
      },
      "binding": {
        "classId": "RevealOverlappedHints"
      }
    }
  ],
  "sharedKeybinds": {
    "HintTool": [
      {
        "key": "Digit1",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.0,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit2",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.125,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit3",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.25,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit4",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.375,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit5",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.5,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit6",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.625,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit7",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.75,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit8",
        "action": {
          "classId": "SnapTargets",
          "percentX": 0.875,
          "percentY": 0.5
        }
      },
      {
        "key": "Digit9",
        "action": {
          "classId": "SnapTargets",
          "percentX": 1.0,
          "percentY": 0.5
        }
      },
      {
        "key": "ArrowLeft",
        "action": {
          "classId": "MoveTargets",
          "direction": "Left",
          "strideX": -4,
          "strideY": 0
        }
      },
      {
        "key": "ArrowRight",
        "action": {
          "classId": "MoveTargets",
          "direction": "Right",
          "strideX": 4,
          "strideY": 0
        }
      },
      {
        "key": "ArrowUp",
        "action": {
          "classId": "MoveTargets",
          "direction": "Up",
          "strideX": 0,
          "strideY": -4
        }
      },
      {
        "key": "ArrowDown",
        "action": {
          "classId": "MoveTargets",
          "direction": "Down",
          "strideX": 0,
          "strideY": 4
        }
      },
      {
        "key": "Tab",
        "action": {
          "classId": "ToggleFieldOfVision"
        }
      },
      {
        "key": "BracketLeft",
        "action": {
          "classId": "ClairvoyanceMode"
        }
      },
      {
        "key": "Semicolon",
        "action": {
          "classId": "GridMode"
        }
      },
      {
        "key": "Quote",
        "action": {
          "classId": "DualSelect"
        }
      },
      {
        "key": "Quote",
        "shift": "Either",
        "action": {
          "classId": "MultiSelect"
        }
      },
      {
        "key": "Quote",
        "ctrl": "Either",
        "action": {
          "classId": "PathSelect"
        }
      },
      {
        "key": "Enter",
        "action": {
          "classId": "FinishSelection"
        }
      }
    ]
  }
}
```

## 7. Uncertainties

1. The full compiled default-keybind table behind `FUN_140175660` was only partially decoded (the
   `Segoe`/scan-code groups beyond the verified subset); the bootstrap JSON above is therefore the
   *verified subset + documented activation hotkeys*, not an exhaustive byte-for-byte copy.
2. Per-class parameter struct layouts (offsets/types in the core) were not fully decoded; the JSON field
   names from the bundle and the semantics in §4 are the contract surface.
3. Several catalog entries (`TextSelectionTool`, `DragTool`, `NavigationMode`, the voice tool classes)
   exist only in the shipped UI; the 0.4.1 core has no routes for them (they 404 against this core).


## 8. Per-class parameter schemas (verified against the shipped UI contract)

The settings GUI's validator schemas are the wire contract the core must accept; they were extracted
mechanically (`notes/scratch-tools/class-params.tsv`, generator in the same directory) together with every
enum domain. Full inventory (union of the UI catalog and the schemas, with a core-presence check per
class): `notes/scratch-tools/functionality-inventory.md`. Highlights:

| classId | parameters |
|---|---|
| `MoveWindow` | `target: enum[Pixels\|Monitor\|Desktop\|Edge\|Center\|Back]`, `direction?: enum[Left\|Right\|Up\|Down]`, `stride?: number`, `maximize?: boolean`, `position?: enum[Left\|Right\|Top\|Bottom\|TopLeft\|TopRight\|BottomLeft\|BottomRight]` (plus `strideX/strideY` for nudge) |
| `Scroll` | `direction: enum[Up\|Down\|Left\|Right]`, `step: number`, `mouseTarget?: {x,y}`, `allowHeldModifiers?: boolean` |
| `Zoom` | `direction: enum[In\|Out]`, `step: number` |
| `MouseButton` | `button: enum[Left\|Right\|Middle]`, `operation: enum[Down\|Up\|Toggle]`, `allowHeldModifiers?: boolean` |
| `MouseSlot` | `mode: enum[Screen\|Window]`, `operation: enum[Activate\|Clear]`, `slot: number` |
| `ActionSlot` | `operation: enum[Save\|Clear\|Execute]`, `slot: number` |
| `TeleportMouse` | `mode: enum[WindowPercent\|ScreenPixels]`, `x: number`, `y: number` |
| `ClickOnWindow` | `x: number`, `y: number` (fractions) |
| `SearchForWindow` | `matchBy: enum[ProcessName\|Title]`, `matchMode: enum[Exact\|Contains\|StartsWith]`, `query: string` |
| `TileWindows` | `scope: enum[CurrentMonitor\|FrontTwo]`, `style: enum[Fit\|Fill]` |
| `VirtualDesktop` | `operation: enum[SwitchLeft\|SwitchRight\|Create\|Close]` |
| `ResizeWindow` | `axis: enum[All\|Horizontal\|Vertical]`, `delta: number`, `scope: enum[Left\|Right\|Top\|Bottom\|Horizontal\|Vertical\|All]` |
| `KeyPress` | `events: array<{key: string, state: enum[Down\|Up]}>` |
| `InsertText` | `text: string` |
| `RunShellCommand` | `shellAction: enum[Edit\|Explore\|Find\|Open\|Print\|Properties\|Runas]`, `uri: string`, `parameters: string`, `directory: string` |
| `StickyHintsTool` | `anchor`, `autoClick: boolean`, `persistence: enum[Persistent\|OnePress]`, `keyAssignment: enum[Automatic\|Manual]`, `visionStrategy: enum[Vision\|Grid\|Clairvoyance\|FullScreenGrid\|Custom]`, `finalMousePosition?`, `keybinds` |
| `ScreenSearchTool` | `references: array`, `visionStrategy: enum[…]`, `finalMousePosition?`, `keybinds` (UI-only in 0.4.1) |
| `BasicMouseActionTool` | `mouseAction`, `mouseActionModifiers: array`, `visionStrategy`, `doSaveActionWhenFinished: boolean`, `targetTransformStrategy`, `numberOfTicksBetweenMouseActions: number`, `finalMousePosition?` |

**Core vs UI-only (definitive):** the shipped app exposes **103 class ids that exist in the 0.4.1 core** and **17 UI-only** ids (`ActivateVoiceTool, AppLauncher, ClearReference, DragSpeed, DragTool, FolderOpener, LegacyVoiceCommandTool, MetaVoiceTool, NavigationMode, QuickActionMenu, ScreenSearchTool, SuperAltTab, TextSelectionTool, ToggleVoiceRecognition, VoiceCommandTool, VoiceDictationTool, WindowCloser`) — the voice classes, the navigation/app-launcher presets, and the documented "coming soon" `DragTool`/`TextSelectionTool` (two of the 17 — `DragSpeed` and `ClearReference` — are schema tags rather than standalone classes). A reimplementation that targets the core's behaviour can stub the UI-only ones, exactly as the shipped core does (their endpoints 404).

Authoritative lists: `notes/scratch-tools/class-lists.txt`.

Full per-class table: `notes/scratch-tools/functionality-inventory.md`.
