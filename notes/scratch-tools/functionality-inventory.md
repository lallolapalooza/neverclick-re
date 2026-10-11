# Functionality inventory (97 bindable classes; 82 core-implemented, 15 UI-only)

`core` = the class-id literal exists in `neverclick.exe` (so the core can parse/execute it).
`UI-only` = the shipped settings GUI offers it but the 0.4.1 core has no such class (the Voice pages, and the documented "coming soon" Drag/Text-selection tools).

| classId | core | category | name | parameters (JSON key : type/enum) |
|---|---|---|---|---|
| `ActionSlot` | yes | System Actions | Action Slot | operation:enum[Save|Clear|Execute] | slot:number | type:action |
| `ActivateVoiceTool` | UI-only | System Actions | Activate Voice Tool | type:action |
| `AdjustGap` | yes | — | — | delta:number |
| `AppLauncher` | UI-only | Tools | App Launcher | config:{items:Pme.array()} | type:tool |
| `BasicMouseActionTool` | yes | Tools | Mouse Move Tool | config:{mouseAction:enum[LeftClick|RightClick|MiddleClick|DoubleClick|TripleClick|Move], visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], doSaveActionWhenFinished:boolean, mouseActionModifiers:TN.array(), targetTransformStrategy:enum[Center|SnapLeft|SnapRight|SnapTop|SnapBottom|RightEdge100px], numberOfTicksBetweenMouseActions:number, finalMousePosition:Dv?, keybinds:Pl} | type:tool |
| `ClickOnWindow` | yes | Mouse Actions | Click on Window | type:action | x:number | y:number |
| `CloseWindow` | yes | Window Actions | Close Window | type:action |
| `Copy` | yes | Text & Input Actions | Copy | type:action |
| `Cut` | yes | Text & Input Actions | Cut | type:action |
| `CycleWindows` | yes | Window Actions | Cycle Windows | direction:enum[Forward|Backward] | mouseTarget:{x:number, y:number}? | scope:enum[Behind|SameMonitor|AcrossMonitors|AllWindows] | type:action |
| `DragSpeed` | UI-only | — | — | speed:enum[Fast|Medium|Slow] |
| `DragTool` | UI-only | Tools | Drag Tool | config:{visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], mouseActionModifiers:TN.array(), mouseAction:enum[NoClick|LeftClick|RightClick|MiddleClick], dragStrategy:enum[AllToLast|EachToNext], dragSpeed:enum[Fast|Medium|Slow], keybinds:Pl, targetTransformStrategy:enum[Center|SnapLeft|SnapRight|SnapTop|SnapBottom|RightEdge100px], finalMousePosition:Dv?} | type:tool |
| `Error` | yes | — | — | description:string | rawInput:string | title:string | type:error |
| `ExitNeverclick` | yes | System Actions | Exit Neverclick | type:action |
| `FinalMousePosition` | yes | — | — | strategy:enum[Stay|ReturnToOrigin|Offset] | x:number | y:number |
| `Find` | yes | Text & Input Actions | Find | type:action |
| `FocusWindow` | yes | Window Actions | Focus Window | direction:enum[Left|Right|Above|Below|Behind] | mouseTarget:{x:number, y:number}? | type:action |
| `FolderOpener` | UI-only | Tools | Folder Opener | config:{items:Lme.array()} | type:tool |
| `GoBack` | yes | System Actions | Go Back | type:action |
| `GoForward` | yes | System Actions | Go Forward | type:action |
| `HighlightActiveWindow` | yes | Window Actions | Highlight Active Window | type:action |
| `HighlightMouse` | yes | Mouse Actions | Highlight Mouse | type:action |
| `InsertText` | yes | Text & Input Actions | Insert Text | text:string | type:action |
| `JumpToFirstLine` | yes | Text & Input Actions | Jump to First Line | type:action |
| `JumpToLastLine` | yes | Text & Input Actions | Jump to Last Line | type:action |
| `JumpWordLeft` | yes | Text & Input Actions | Jump Word Left | type:action |
| `JumpWordRight` | yes | Text & Input Actions | Jump Word Right | type:action |
| `KeyPress` | yes | Text & Input Actions | Key Press | events:array<{key:string, state:enum[Down|Up]}> | type:action |
| `LegacyVoiceCommandTool` | UI-only | — | — | name:string |
| `MetaVoiceTool` | UI-only | — | — | dictation:{name:string, dictateIntoActiveWindow:boolean, voiceRequests:array<x.unknown()>, voiceCommands:array<x.unknown()>} | name:string |
| `MinimizeOthers` | yes | Window Actions | Minimize Others | type:action |
| `MinimizeWindow` | yes | Window Actions | Minimize Window | type:action |
| `MouseAction` | yes | — | — | action:enum[LeftClick|RightClick|MiddleClick|DoubleClick|TripleClick|Move] |
| `MouseButton` | yes | Mouse Actions | Mouse Button | allowHeldModifiers:boolean? | button:enum[Left|Right|Middle] | operation:enum[Down|Up|Toggle] | type:action |
| `MouseSlot` | yes | Mouse Actions | Mouse Slot | mode:enum[Screen|Window] | operation:enum[Activate|Clear] | slot:number | type:action |
| `MoveMouse` | yes | Mouse Actions | Move Mouse | direction:enum[Left|Right|Up|Down] | stride:number | type:action |
| `MoveTargets` | yes | — | — | strideX:number | strideY:number |
| `MoveWindow` | yes | Window Actions | Move Window | direction:enum[Left|Right|Up|Down]? | maximize:boolean? | position:enum[Left|Right|Top|Bottom|TopLeft|TopRight|BottomLeft|BottomRight]? | stride:number? | strideX:number | strideY:number | target:enum[Pixels|Monitor|Desktop|Edge|Center|Back] | type:action |
| `MoveWindowToEdge` | yes | — | — | direction:enum[Left|Right|Up|Down] |
| `MoveWindowToMonitor` | yes | — | — | direction:enum[Left|Right|Up|Down] |
| `MoveWindowToVirtualDesktop` | yes | — | — | direction:enum[Left|Right] |
| `MuteVolume` | yes | System Actions | Mute Volume | type:action |
| `NavigationMode` | UI-only | Tools | Navigation Mode | config:{keybinds:Cme.array(), keyRemaps:rF.array(), enableAppBar:boolean, doHighlightMonitorBorder:boolean, doChangeIcon:boolean, enableSound:boolean} | type:tool |
| `NewLineAbove` | yes | Text & Input Actions | New Line Above | type:action |
| `NewLineBelow` | yes | Text & Input Actions | New Line Below | type:action |
| `OpenApplication` | yes | System Actions | Open Application | config:{application:string, parameters:string, runAsAdmin:boolean, forceLaunch:boolean?} | type:action |
| `OpenFile` | yes | Text & Input Actions | Open File | type:action |
| `OpenSettings` | yes | System Actions | Open Settings | type:action |
| `Paste` | yes | Text & Input Actions | Paste | type:action |
| `PathSelect` | yes | — | — | margin:number |
| `PreviousWindow` | yes | Window Actions | Previous Window | mouseTarget:{x:number, y:number}? | scope:enum[Any|SameMonitor|DifferentMonitor] | type:action |
| `QuickActionMenu` | UI-only | Tools | Quick Action Menu | config:{items:$ve.array()} | type:tool |
| `Redo` | yes | Text & Input Actions | Redo | type:action |
| `RegionSelect` | yes | — | — | margin:number |
| `RepeatLastMouseAction` | yes | Mouse Actions | Repeat Last Mouse Action | type:action |
| `ResizeWindow` | yes | Window Actions | Resize Window | axis:enum[All|Horizontal|Vertical] | delta:number | scope:enum[Left|Right|Top|Bottom|Horizontal|Vertical|All] | type:action |
| `RestartNeverclick` | yes | System Actions | Restart Neverclick | type:action |
| `RunShellCommand` | yes | System Actions | Run Shell Command | config:{shellAction:enum[Edit|Explore|Find|Open|Print|Properties|Runas], uri:string, parameters:string, directory:string} | type:action |
| `Save` | yes | Text & Input Actions | Save | type:action |
| `ScreenSearchTool` | UI-only | Tools | Screen Search Tool | config:{references:Wve.array(), visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], finalMousePosition:Dv?, keybinds:Pl} | type:tool |
| `Scroll` | yes | Mouse Actions | Scroll | allowHeldModifiers:boolean? | direction:enum[Up|Down|Left|Right] | mouseTarget:{x:number, y:number}? | step:number | type:action |
| `SearchForWindow` | yes | Window Actions | Search for Window | matchBy:enum[ProcessName|Title] | matchMode:enum[Exact|Contains|StartsWith] | query:string | type:action |
| `SelectAll` | yes | Text & Input Actions | Select All | type:action |
| `SelectWordLeft` | yes | Text & Input Actions | Select Word Left | type:action |
| `SelectWordRight` | yes | Text & Input Actions | Select Word Right | type:action |
| `SetFieldOfVision` | yes | — | — | target:enum[Window|Monitor|AllMonitors] |
| `SetLayout` | yes | — | — | columns:number | rows:number |
| `ShiftFocus` | yes | — | — | direction:enum[Left|Right|Up|Down] |
| `SleepNeverclick` | yes | System Actions | Sleep Neverclick | type:action |
| `SnapTargets` | yes | — | — | percentX:number | percentY:number |
| `StickyHintsTool` | yes | Tools | Sticky Hints Tool | config:{anchor:Ume, autoClick:boolean, persistence:enum[Persistent|OnePress], keyAssignment:enum[Automatic|Manual], visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], finalMousePosition:Dv?, keybinds:Pl} | type:tool |
| `SuperAltTab` | UI-only | Tools | Super Alt Tab | config:{algorithm:enum[AllWindows|AltTabWindows], desktopScope:enum[CurrentDesktop|AllDesktops], filter:enum[AllWindows|NonMinimizedWindowsOnly|MinimizedWindowsOnly], keybinds:Pl, animateSelection:boolean, spatialAssignment:boolean, pinnedKeys:string, hintPlacement:enum[bottomRight|belowIcon]} | type:tool |
| `SuspendNeverclick` | yes | System Actions | Suspend Neverclick | type:action |
| `SwitchTab` | yes | Text & Input Actions | Switch Tab | direction:enum[Left|Right] | type:action |
| `TeleportMouse` | yes | Mouse Actions | Teleport Mouse | mode:enum[WindowPercent|ScreenPixels] | type:action | x:number | y:number |
| `TextSelectionTool` | UI-only | Tools | Text Selection Tool | config:{visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], mouseActionModifiers:TN.array(), keybinds:Pl, finalMousePosition:Dv?} | type:tool |
| `TextSlot` | yes | Text & Input Actions | Text Slot | operation:enum[Copy|Paste] | slot:number | type:action |
| `TileWindows` | yes | Window Actions | Tile Windows | scope:enum[CurrentMonitor|FrontTwo] | style:enum[Fit|Fill] | type:action |
| `ToggleAlwaysOnTop` | yes | Window Actions | Toggle Always On Top | type:action |
| `ToggleAppBar` | yes | System Actions | Toggle App Bar | type:action |
| `ToggleFieldOfVision` | yes | — | — | fovA:enum[Window|Monitor|AllMonitors] | fovB:enum[Window|Monitor|AllMonitors] |
| `ToggleModifiers` | yes | — | — | alt:boolean | ctrl:boolean | shift:boolean |
| `ToggleVoiceRecognition` | UI-only | System Actions | Toggle Voice Recognition | type:action |
| `ToggleWindow` | yes | Window Actions | Toggle Window | type:action |
| `Undo` | yes | Text & Input Actions | Undo | type:action |
| `VirtualDesktop` | yes | System Actions | Virtual Desktop | operation:enum[SwitchLeft|SwitchRight|Create|Close] | type:action |
| `VisionMode` | yes | — | — | vision:{detectionModel:enum[Balanced|Narrow|UltraNarrow|Wide], removeHallucinations:boolean} |
| `VoiceCommandTool` | UI-only | — | — | name:string | voiceCommands:array<x.unknown()> |
| `VolumeDown` | yes | System Actions | Volume Down | type:action |
| `VolumeUp` | yes | System Actions | Volume Up | type:action |
| `WiggleMouse` | yes | Mouse Actions | Wiggle Mouse | mode:enum[InPlace|OnWindow] | position:{x:number, y:number}? | type:action |
| `WindowCloser` | UI-only | Tools | Window Closer | config:{algorithm:enum[AllWindows|AltTabWindows], desktopScope:enum[CurrentDesktop|AllDesktops], keybinds:Pl, animateSelection:boolean, spatialAssignment:boolean, pinnedKeys:string, hintPlacement:enum[bottomRight|belowIcon]} | type:tool |
| `WindowLayoutSlot` | yes | Window Actions | Window Layout Slot | operation:enum[Activate|Clear] | slot:number | type:action |
| `WindowMoveTool` | yes | Tools | Window Move Tool | config:{keybinds:Pl} | type:tool |
| `WindowSlot` | yes | Window Actions | Window Slot | operation:enum[Activate|Clear] | slot:number | type:action |
| `WindowSnappingTool` | yes | Tools | Window Snapping Tool | config:{initialLayout:{rows:..., columns:...}, gap:number, keybinds:Pl} | type:tool |
| `Zoom` | yes | Mouse Actions | Zoom | direction:enum[In|Out] | step:number | type:action |

## UI-only classes (not implementable from the core; the GUI expects them)

- `ActivateVoiceTool` — Activate Voice Tool
- `AppLauncher` — App Launcher
- `DragSpeed` — 
- `DragTool` — Drag Tool
- `FolderOpener` — Folder Opener
- `LegacyVoiceCommandTool` — 
- `MetaVoiceTool` — 
- `NavigationMode` — Navigation Mode
- `QuickActionMenu` — Quick Action Menu
- `ScreenSearchTool` — Screen Search Tool
- `SuperAltTab` — Super Alt Tab
- `TextSelectionTool` — Text Selection Tool
- `ToggleVoiceRecognition` — Toggle Voice Recognition
- `VoiceCommandTool` — 
- `WindowCloser` — Window Closer
