| classId | in core | parameters (JSON key: type / enum values) |
|---|---|---|
| `ActionSlot` | core | `operation`:enum[Save|Clear|Execute] | `slot`:number | `type`:action |
| `ActivateVoiceTool` | UI-only | `type`:action |
| `AdjustGap` | core | `delta`:number |
| `AppLauncher` | UI-only | `config`:{items:Pme.array()} | `type`:tool |
| `BasicMouseActionTool` | core | `config`:{mouseAction:enum[LeftClick|RightClick|MiddleClick|DoubleClick|TripleClick|Move], visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], doSaveActionWhenFinished:boolean, mouseActionModifiers:TN.array(), targetTransformStrategy:enum[Center|SnapLeft|SnapRight|SnapTop|SnapBottom|RightEdge100px], numberOfTicksBetweenMouseActions:number, finalMousePosition:Dv?, keybinds:Pl} | `type`:tool |
| `ClickOnWindow` | core | `type`:action | `x`:number | `y`:number |
| `CloseWindow` | core | `type`:action |
| `Copy` | core | `type`:action |
| `Cut` | core | `type`:action |
| `CycleWindows` | core | `direction`:enum[Forward|Backward] | `mouseTarget`:{x:number, y:number}? | `scope`:enum[Behind|SameMonitor|AcrossMonitors|AllWindows] | `type`:action |
| `DragSpeed` | UI-only | `speed`:enum[Fast|Medium|Slow] |
| `DragTool` | UI-only | `config`:{visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], mouseActionModifiers:TN.array(), mouseAction:enum[NoClick|LeftClick|RightClick|MiddleClick], dragStrategy:enum[AllToLast|EachToNext], dragSpeed:enum[Fast|Medium|Slow], keybinds:Pl, targetTransformStrategy:enum[Center|SnapLeft|SnapRight|SnapTop|SnapBottom|RightEdge100px], finalMousePosition:Dv?} | `type`:tool |
| `Error` | core | `description`:string | `rawInput`:string | `title`:string | `type`:error |
| `ExitNeverclick` | core | `type`:action |
| `FinalMousePosition` | core | `strategy`:enum[Stay|ReturnToOrigin|Offset] | `x`:number | `y`:number |
| `Find` | core | `type`:action |
| `FocusWindow` | core | `direction`:enum[Left|Right|Above|Below|Behind] | `mouseTarget`:{x:number, y:number}? | `type`:action |
| `FolderOpener` | UI-only | `config`:{items:Lme.array()} | `type`:tool |
| `GoBack` | core | `type`:action |
| `GoForward` | core | `type`:action |
| `HighlightActiveWindow` | core | `type`:action |
| `HighlightMouse` | core | `type`:action |
| `InsertText` | core | `text`:string | `type`:action |
| `JumpToFirstLine` | core | `type`:action |
| `JumpToLastLine` | core | `type`:action |
| `JumpWordLeft` | core | `type`:action |
| `JumpWordRight` | core | `type`:action |
| `KeyPress` | core | `events`:array<{key:string, state:enum[Down|Up]}> | `type`:action |
| `LegacyVoiceCommandTool` | UI-only | `name`:string |
| `MetaVoiceTool` | UI-only | `dictation`:{name:string, dictateIntoActiveWindow:boolean, voiceRequests:array<x.unknown()>, voiceCommands:array<x.unknown()>} | `name`:string |
| `MinimizeOthers` | core | `type`:action |
| `MinimizeWindow` | core | `type`:action |
| `MouseAction` | core | `action`:enum[LeftClick|RightClick|MiddleClick|DoubleClick|TripleClick|Move] |
| `MouseButton` | core | `allowHeldModifiers`:boolean? | `button`:enum[Left|Right|Middle] | `operation`:enum[Down|Up|Toggle] | `type`:action |
| `MouseSlot` | core | `mode`:enum[Screen|Window] | `operation`:enum[Activate|Clear] | `slot`:number | `type`:action |
| `MoveMouse` | core | `direction`:enum[Left|Right|Up|Down] | `stride`:number | `type`:action |
| `MoveTargets` | core | `strideX`:number | `strideY`:number |
| `MoveWindow` | core | `direction`:enum[Left|Right|Up|Down]? | `maximize`:boolean? | `position`:enum[Left|Right|Top|Bottom|TopLeft|TopRight|BottomLeft|BottomRight]? | `stride`:number? | `strideX`:number | `strideY`:number | `target`:enum[Pixels|Monitor|Desktop|Edge|Center|Back] | `type`:action |
| `MoveWindowToEdge` | core | `direction`:enum[Left|Right|Up|Down] |
| `MoveWindowToMonitor` | core | `direction`:enum[Left|Right|Up|Down] |
| `MoveWindowToVirtualDesktop` | core | `direction`:enum[Left|Right] |
| `MuteVolume` | core | `type`:action |
| `NavigationMode` | UI-only | `config`:{keybinds:Cme.array(), keyRemaps:rF.array(), enableAppBar:boolean, doHighlightMonitorBorder:boolean, doChangeIcon:boolean, enableSound:boolean} | `type`:tool |
| `NewLineAbove` | core | `type`:action |
| `NewLineBelow` | core | `type`:action |
| `OpenApplication` | core | `config`:{application:string, parameters:string, runAsAdmin:boolean, forceLaunch:boolean?} | `type`:action |
| `OpenFile` | core | `type`:action |
| `OpenSettings` | core | `type`:action |
| `Paste` | core | `type`:action |
| `PathSelect` | core | `margin`:number |
| `PreviousWindow` | core | `mouseTarget`:{x:number, y:number}? | `scope`:enum[Any|SameMonitor|DifferentMonitor] | `type`:action |
| `QuickActionMenu` | UI-only | `config`:{items:$ve.array()} | `type`:tool |
| `Redo` | core | `type`:action |
| `RegionSelect` | core | `margin`:number |
| `RepeatLastMouseAction` | core | `type`:action |
| `ResizeWindow` | core | `axis`:enum[All|Horizontal|Vertical] | `delta`:number | `scope`:enum[Left|Right|Top|Bottom|Horizontal|Vertical|All] | `type`:action |
| `RestartNeverclick` | core | `type`:action |
| `RunShellCommand` | core | `config`:{shellAction:enum[Edit|Explore|Find|Open|Print|Properties|Runas], uri:string, parameters:string, directory:string} | `type`:action |
| `Save` | core | `type`:action |
| `ScreenSearchTool` | UI-only | `config`:{references:Wve.array(), visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], finalMousePosition:Dv?, keybinds:Pl} | `type`:tool |
| `Scroll` | core | `allowHeldModifiers`:boolean? | `direction`:enum[Up|Down|Left|Right] | `mouseTarget`:{x:number, y:number}? | `step`:number | `type`:action |
| `SearchForWindow` | core | `matchBy`:enum[ProcessName|Title] | `matchMode`:enum[Exact|Contains|StartsWith] | `query`:string | `type`:action |
| `SelectAll` | core | `type`:action |
| `SelectWordLeft` | core | `type`:action |
| `SelectWordRight` | core | `type`:action |
| `SetFieldOfVision` | core | `target`:enum[Window|Monitor|AllMonitors] |
| `SetLayout` | core | `columns`:number | `rows`:number |
| `ShiftFocus` | core | `direction`:enum[Left|Right|Up|Down] |
| `SleepNeverclick` | core | `type`:action |
| `SnapTargets` | core | `percentX`:number | `percentY`:number |
| `StickyHintsTool` | core | `config`:{anchor:Ume, autoClick:boolean, persistence:enum[Persistent|OnePress], keyAssignment:enum[Automatic|Manual], visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], finalMousePosition:Dv?, keybinds:Pl} | `type`:tool |
| `SuperAltTab` | UI-only | `config`:{algorithm:enum[AllWindows|AltTabWindows], desktopScope:enum[CurrentDesktop|AllDesktops], filter:enum[AllWindows|NonMinimizedWindowsOnly|MinimizedWindowsOnly], keybinds:Pl, animateSelection:boolean, spatialAssignment:boolean, pinnedKeys:string, hintPlacement:enum[bottomRight|belowIcon]} | `type`:tool |
| `SuspendNeverclick` | core | `type`:action |
| `SwitchTab` | core | `direction`:enum[Left|Right] | `type`:action |
| `TeleportMouse` | core | `mode`:enum[WindowPercent|ScreenPixels] | `type`:action | `x`:number | `y`:number |
| `TextSelectionTool` | UI-only | `config`:{visionStrategy:enum[Vision|Grid|Clairvoyance|FullScreenGrid|Custom], mouseActionModifiers:TN.array(), keybinds:Pl, finalMousePosition:Dv?} | `type`:tool |
| `TextSlot` | core | `operation`:enum[Copy|Paste] | `slot`:number | `type`:action |
| `TileWindows` | core | `scope`:enum[CurrentMonitor|FrontTwo] | `style`:enum[Fit|Fill] | `type`:action |
| `ToggleAlwaysOnTop` | core | `type`:action |
| `ToggleAppBar` | core | `type`:action |
| `ToggleFieldOfVision` | core | `fovA`:enum[Window|Monitor|AllMonitors] | `fovB`:enum[Window|Monitor|AllMonitors] |
| `ToggleModifiers` | core | `alt`:boolean | `ctrl`:boolean | `shift`:boolean |
| `ToggleVoiceRecognition` | UI-only | `type`:action |
| `ToggleWindow` | core | `type`:action |
| `Undo` | core | `type`:action |
| `VirtualDesktop` | core | `operation`:enum[SwitchLeft|SwitchRight|Create|Close] | `type`:action |
| `VisionMode` | core | `vision`:{detectionModel:enum[Balanced|Narrow|UltraNarrow|Wide], removeHallucinations:boolean} |
| `VoiceCommandTool` | UI-only | `name`:string | `voiceCommands`:array<x.unknown()> |
| `VolumeDown` | core | `type`:action |
| `VolumeUp` | core | `type`:action |
| `WiggleMouse` | core | `mode`:enum[InPlace|OnWindow] | `position`:{x:number, y:number}? | `type`:action |
| `WindowCloser` | UI-only | `config`:{algorithm:enum[AllWindows|AltTabWindows], desktopScope:enum[CurrentDesktop|AllDesktops], keybinds:Pl, animateSelection:boolean, spatialAssignment:boolean, pinnedKeys:string, hintPlacement:enum[bottomRight|belowIcon]} | `type`:tool |
| `WindowLayoutSlot` | core | `operation`:enum[Activate|Clear] | `slot`:number | `type`:action |
| `WindowMoveTool` | core | `config`:{keybinds:Pl} | `type`:tool |
| `WindowSlot` | core | `operation`:enum[Activate|Clear] | `slot`:number | `type`:action |
| `WindowSnappingTool` | core | `config`:{initialLayout:{rows:..., columns:...}, gap:number, keybinds:Pl} | `type`:tool |
| `Zoom` | core | `direction`:enum[In|Out] | `step`:number | `type`:action |
