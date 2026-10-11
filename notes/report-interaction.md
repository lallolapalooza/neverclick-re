# Neverclick 0.4.1 — Interaction layer report

> **Artifact availability.** `ghidra/neverclick-decomp.c` and the raw scratch indexes
> (`notes/scratch-interaction/{func-index,symbol-hits,trace-scopes,trace-strings}.txt`) have been removed
> from this tree. Bare `line NNNNN` citations refer to decompilation lines of that removed dump and cannot
> be re-opened; the analysis and reconstructed pseudocode remain authoritative.
(Hotkeys / tools / mouse injection / window management / UIA exposure / app chrome)

Static analysis only. Primary source: `ghidra/neverclick-decomp.c` (6,693 functions; cited as `line (FUN_VA)`). Scratch indexes: `notes/scratch-interaction/{func-index.txt,trace-scopes.txt,vt.py,symbol-hits.txt}`. `[INFERENCE]` marks guesses; `[GAP]` marks unresolved.

---

## Summary

- **Keyboard interception**: one *global* `SetWindowsHookExW(0xd /*WH_KEYBOARD_LL*/, cb, 0, 0)` (line 31025, `FUN_1400235c0` = `nvr::win::KeyboardHook::hook`). **No `RegisterHotKey` anywhere in the binary** (0 hits). The hook lives on a dedicated `win::InputHookThread` (error string line 31468: *"Input hook thread is not running. Construct win::InputHookThread before installing hooks."*); all hook/unhook/isHooked ops from other threads marshal there via `SendMessageW(hookWnd, 0x401, 0, closure)` (line 31460-31484, `FUN_140023e40`; wndproc `FUN_140023940` line 31156 executes closure, exceptions propagate via `__ExceptionPtr`).
- **Hotkey registry**: a global vector of installed hook entries (begin/end/cap at `DAT_1402ded10/18/20`, 0x48-byte elements: `{u32 hookId, callable(std::function)}`); each `KeyboardHook` object = `{u32 id (monotonic counter DAT_1402dec54), std::function payload, char installed}` (ctor `FUN_140022c30` line 30441; `hook`/`unhook`/`isHooked` = `FUN_1400235c0`/`FUN_140023110`/`FUN_1400230a0`, lines 30993/30778/30729). LL callback iterates entries; first entry returning 1 swallows the key.
- **Three hotkey states** (int at `HotkeyManager+0x278`): `0 = Active (ToolActivationHook)`, `1 = Suspended`, `2 = Sleeping`. Rebuild function `FUN_140096d20` (line 128348) filters the `vector<HotkeyEntry>` (stride **0x70**) per state and reinstalls the hook. Transitions: suspend toggle `FUN_1400c41b0` (line 165062: `state = state!=1 ? 1 : 0`), sleep toggle `FUN_1400c3de0` (line 164850: `state = state==2 ? 0 : 2`), each followed by rebuild.
- **Chord matching** happens inside the LL thread in `ToolActivationHookCallback::operator()` (`FUN_140098230`, line 129422): chord = 5 dwords `{ctrlReq, altReq, shiftReq, winReq, vk}` + a real-time **modifier snapshot** (8-bit mask from `GetAsyncKeyState`, `FUN_14010a240` line 222708). Match → `PostMessageW(hwnd, 0x501, heapChord, 0x147d)` (line 129345) → main wndproc `FUN_1400612c0` (line 84480) linearly re-matches the chord against entries and either **activates a tool** (mode 0) or **executes an action directly** (mode 1).
- **Swallow contract**: LL cb returns 1 to eat an event, else `CallNextHookEx` (line 30435). The app marks its own injected **keyboard and wheel** input with `dwExtraInfo = 0x147d` (`DAT_1402ded28 = 0x147d`, line 5481; mouse move/button INPUTs carry 0 — see Mouse section); every callback ignores self-injected events, and a special path replays `LCTRL tap + WIN up` (SendInput×3, line 30419) to suppress the Start menu after swallowed Win chords.
- **Tool input capture**: while a tool's hints are up, `ToolInputHookCallback` (`FUN_1400e8af0`, line 195226) eats **all non-modifier key down/up**, posting `0x502 {modifierSnapshot, vk}` (line 195261) to the main window; the active tool's event chain consumes `0x502` events (e.g. `FUN_140177d70` line 313202). Modifier keys (Shift/Ctrl/Alt/Win) are never captured.
- **Release trap**: `KeyReleaseTrapCallback` (`FUN_1400e8940`, line 195150) swallows key-ups of a captured set and fires the deferred action when the set empties, with a ~1.001 s timeout fallback (line 195186); `ActiveToolManager::handleKeyReleaseTrap` (`FUN_1400e8750`, line 195006) posts `0x50f {closure}` which unhooks the trap (line 195028 / wndproc line 84754).
- **Overlay**: tool activation shows the two overlay HWNDs (`ctx+0x7c0/0x7c8 → +0x20`) with `ShowWindow(…, SW_SHOWNA)` (lines 194701-02) and posts `0x50c` refresh; deactivation hides them `SW_HIDE` (lines 194798-99).
- All injection is `SendInput` — exactly **5 call sites** in the whole binary: **30419** (LL-hook Win-key replay, `SendInput(3,…)`), **48378** + **48520** (`FUN_140036f50` keyboard/wheel batch, plain vs modifier-neutralized), **409453** (`FUN_1401efdd0` single mouse INPUT), **409522** (`FUN_1401eff30` mouse INPUT vector). No `mouse_event` import; one `SetCursorPos` (405000, window-warp helper). Mouse INPUT details: see *Mouse & scroll injection*.
- **Mouse moves** = one `MOUSEEVENTF_MOVE|ABSOLUTE|VIRTUALDESK` INPUT (0xC001) normalized to 0-65535 over the virtual screen; clicks = fixed flag vectors (left 2/4, right 8/10, middle 0x20/0x40); wheel = ±120·lines, modifier-neutralized in one batch; `ReturnToOrigin` replays the pre-click cursor position after the click events.
- **Window actions**: geometric half-plane picker (FocusWindow), z-order walk (CycleWindows Forward sends old window to bottom; Backward no-reorder), exact-abutment monitor moves, single-jump SetWindowPos snapping, AnimationQueue/AnimationWindow-thread animation side-channel gated by `enableWindowAnimations`.
- **UIA**: pure *client* — one `CoCreateInstance(CLSID_CUIAutomation {FF48DBA4-…})`, caches only BoundingRectangle; Clairvoyance = rects of all control-view descendants of the foreground window; FailSafe = one-shot `UIA_AsyncContentLoaded` (0x4E26) re-delivery of `{ticket, rects}` via a caller-chosen window message (no timeouts); **no UIA provider exposure** (zero WM_GETOBJECT/IRawElementProvider).
- **Elevation/UIPI**: embedded manifest `asInvoker uiAccess="true"` (verified verbatim from the exe) + Program Files + Authenticode — no runtime elevation code at all.
- **Config**: `app-config.json` + `hotkey-config.json.gz` (schema-versioned); live GUI control via cpp-httplib REST on **0.0.0.0:7340**; defaults compiled in code (Shift+WASD/Q/E/Z etc.); startup = startup-folder `.lnk` (not a Run key); updates = hourly WinHTTP GET `https://www.neverclick.com/api/version` → silent updater spawn; sleep/wake plays `%WINDIR%\Media\Speech {Sleep,On}.wav`, WAV resources 301/302 embedded (playback backend open).

---

## Hotkey state machine

### 1. Hook plumbing

```
win::InputHookThread (object DAT_1402ded30; +0x18 = msg wnd HWND, +0x20 = thread id)
  ├─ message-only window; wndproc FUN_140023940 (line 31156)
  │    WM_DESTROY(2)→PostQuitMessage, WM_CLOSE(0x10)→DestroyWindow,
  │    msg 0x401 → invoke marshalled closure (line 31170)
  └─ runs the single global WH_KEYBOARD_LL hook
```

| op | function | line | behavior |
|---|---|---|---|
| `hook()` | `FUN_1400235c0` | 30993 | if `DAT_1402ded08==0` → `SetWindowsHookExW(0xd, FUN_140022910, NULL, 0)`; throw `"Failed to set keyboard hook."` (line 31027) on failure; append `{id, cloned-callable}` to global vector |
| `unhook()` | `FUN_140023110` | 30778 | rebuild global vector excluding entries with own id; then `UnhookWindowsHookEx` + clear handle + clear Win-key flags `DAT_1402dec51/52/53` (line 30925 throw on failure) |
| `isHooked()` | `FUN_1400230a0` | 30729 | true iff any vector entry has matching id |
| thread marshal | `FUN_140023e40` | 31446 | same-thread → invoke inline; else `SendMessageW(hookWnd, 0x401, 0, closure)`; throws if thread not running |

`FUN_140022db0` (line 30530) = install wrapper (`Hook already exists.` throw, line 30554), `FUN_140022e80` (line 30561) = uninstall-if-installed, `FUN_140022ef0` (line 30582) = isHooked wrapper — all funnel through the marshal. Only **one** LL hook exists process-wide; state hooks and the tool trap hook coexist as *separate id-tagged entries* in the same vector (loop in LL cb, line 30361-30377, stops at first match).

### 2. LL callback `FUN_140022910` (line 30288) — full rules

```
cb(code, wParam, KBDLLHOOKSTRUCT* p):
  if code != 0:                      → CallNextHookEx            # line 30336
  vk = p->vkCode (30337); extra = p->dwExtraInfo (30338)
  if vk == 0xE7 (VK_PACKET):         vk = LOBYTE(VkKeyScanW(scan)) else pass through  # 30339-30347
  if wParam ∈ {0x100,0x104}: down=1 ; elif ∈ {0x101,0x105}: down=0 ; else pass through # 30349-30361
  selfInjected := (DAT_1402ded28 != 0 && extra == DAT_1402ded28 == 0x147d)   # 30360/30368
  # Win-key bookkeeping (only when NOT self-injected):
  #   vk LWIN(0x5b) → DAT_1402dec51 = down? ; vk RWIN(0x5c) → DAT_1402dec52 = down?   # 30360-30371
  for each entry in installed-vector:                        # 30373
      ret = entry.callable(isUp, vk, (u32)extra)             # vtbl slot 2 (+0x10) @ 30382
      if ret == 1: matched = true; break                     # 30383-30385
  if not selfInjected:
      if matched && down && (LWIN||RWIN held): DAT_1402dec53 = 1   # "win chord swallowed"  # 30389-30391
      if !matched && vk ∈ {LWIN,RWIN} && up && DAT_1402dec53
         && !Ctrl && !Alt && !Shift (GetAsyncKeyState ≥ 0):         # 30392-…
            SendInput(3, [LCTRL down(tag 0x147d), LCTRL up, vk up], 40)  # 30419
            if 3 delivered: matched = true                  # 30420-30422, swallows the WIN key-up
      if no Win key held: DAT_1402dec53 = 0                 # 30424-30426
  return matched ? 1 : CallNextHookEx(...)                   # 30430-30435
```

Notes:
- `FUN_140036950(buf, vk, isUp, extra)` = build one `INPUT{KEYBOARD, {VK, scan=MapVirtualKeyW? …, dwExtraInfo=extra}}` (used with extra = 0x147d everywhere; construction also inline at 48100/48124 `*(u32*)(ki+0x0c)=0x147d`).
- **Input reaching apps**: events not returned 1 pass to the focused app via `CallNextHookEx`. In particular modifier keys are always passed through (see matcher/trap guards below) — the app never swallows Shift/Ctrl/Alt/Win alone.
- `[INFERENCE]` replay condition `-1 < SVar7` = *key not pressed* (high bit clear), i.e. replay fires when Ctrl/Alt/Shift are all up at Win-key-up time.

### 3. `HotkeyEntry` (stride 0x70 = 112 B)

Proven by wndproc match loop (lines 84712-84721) + state filters (lines 128437-128458, 128656-128672) + `FUN_140096be0` (line 128293):

| offset | type | meaning |
|---|---|---|
| +0x08 | int | **ctrlReq**: 0=none, 1=left, 2=right, 3=either |
| +0x0c | int | **altReq** (same codes) |
| +0x10 | int | **shiftReq** (same codes) |
| +0x14 | int | **winReq** (same codes) |
| +0x18 | int | **vk** (trigger key) |
| +0x1c | bool | must be ≠0 for entry to participate (enabled-and-present flag) `[exact config field: GAP]` |
| +0x20 | action* | target object; vtbl: slot0=activate, slot1=execute/reactivate, slot2=deactivate, slot3=`GetName()` returning e.g. `"SuspendNeverclick"` (line 128441-128448) |
| +0x28 | char | **mode**: `-1` invalid (throw `FUN_140040630`), `0` = *tool-activation* entry (routed through ActiveToolManager), `1` = *direct action* entry |
| +0x68 | bool | `enabled` |

Modifier requirement codes confirmed by `FUN_14010a3d0` (line 222782): 0 → both L/R bits must be clear; 1 → left set & right clear; 2 → right set & left clear; 3 → either set. Snapshot bit order (`FUN_14010a240`, line 222708): `bit0 LCTRL, 1 RCTRL, 2 LALT, 3 RALT, 4 LSHIFT, 5 RSHIFT, 6 LWIN, 7 RWIN`.

Chord record posted with `0x501` = the 20 bytes `{+0x08..+0x18}` copied by `FUN_1400973c0` (line 128664-128672).

### 4. Matcher — `ToolActivationHookCallback::operator()` (`FUN_140098230`, line 129422)

```
op(isUp, vk, extra):
  if extra == 0x147d: return 0                       # ignore self-injected  (129446)
  if FUN_140109b80(vk): return 0                     # vk ∈ {0x10,0x11,0x12,0x5b,0x5c,0xa0-0xa5}
                                                      #   = modifiers never trigger chords (222391)
  if DOWN:
      erase vk from swallowed-set (TLS DAT_1402e3b70)         # idempotent (129475)
      cands = [chord in hook's chord-vector where chord.vk == vk]        # FUN_14017aec0 (315158)
      matched = ∃ c ∈ cands : modMatch(snapshot8() , c.{ctrl,alt,shift,win} reqs)   # 129476, 222782
      if matched:
          insert vk into swallowed-set                      # FUN_140038900 (49493), 129480
          adapter.invoke(matchedChordRecord)                # slot2 = FUN_1400980f0 (129325)
              → PostMessageW(hwnd, 0x501, heapCopy(20B), 0x147d)   # 129345; free on failure
          return 1                                     # swallow key-down
      return 0
  if UP:
      if vk ∈ swallowed-set: erase; return 1          # swallow paired key-up (129511)
      return 0
```

Adapter identity per state (vtable `[3]` = RTTI accessor naming the creating lambda):
`0x14026a648` → `CreateToolActivationHook::{lambda_1}` (state 0), `0x14026a5e8` → `CreateSuspendedHook::{lambda_3}` (state 1), `0x14026a618` → `CreateSleepingHook::{lambda_3}` (state 2) — all invoke `FUN_1400980f0` (post 0x501). All three hooks share the same wrapper class `ToolActivationHookCallback` (vtable `0x14026a5b8`, built by `FUN_140097650` line 128763/`FUN_140098490` line 129518).

### 5. State machine — `HotkeyManager::rebuildHooks` = `FUN_140096d20` (line 128348)

HotkeyManager layout (evidence: ctor `FUN_14000a610` line 7938 init at 7984-7990; readers `FUN_1400607d0`, `FUN_1400c4220` line 164900):

```
HotkeyManager {
  +0x00  owner (HWND-bearing context; passed to Create*Hook)
  +0x08  vector<HotkeyEntry>  (stride 0x70)
  +0x20  SharedKeybindSets
  +0xE0  win::KeyboardHook  A   (state hook; built by Create*Hook)
  +0x130 ActiveToolManager      (trap/input-capture machinery; ctor FUN_1400e7b40 line 194447)
  +0x268 observer sink ptr      (broadcast target of wndproc prefilter `FUN_140061bc0`, call 84860: vtbl+0x20(sink, AppContext, 20B msg record) for EVERY message; WM_PAINT → vtbl+0x18 at 84898; writer not located [GAP])
  +0x278 int state  (0 active / 1 suspended / 2 sleeping; init 0 at line 7990)
}
```

```
rebuild(state):                                    # FUN_140096d20
  state==0: entries = all e where e.enabled(+0x68) && e(+0x1c)         # 128680
            adapter = ToolActivation closure; post-filter none
  state==1: entries = e where enabled && +0x1c && mode(+0x28)!=-1 && mode!=0
                       && GetName(e.action) == "SuspendNeverclick"     # 128438-128448
            adapter = Suspended closure   (0x14026a5e8, line 128460)
  state==2: same filter with GetName == "SleepNeverclick"               # 128533-128541
            adapter = Sleeping closure    (0x14026a618)
  build chords (20B each) + adapter → wrapper(0x14026a5b8)
  KeyboardHook::move_assign(HM+0xE0, newHook)  → unhook old/hook new (via InputHookThread)  # 128416 (s0) / 128505 (s1) / 128588 (s2)
```

Transitions (all end with `rebuild`):

| event | function | line | formula |
|---|---|---|---|
| suspend/resume (action `SuspendNeverclick`, tray id 0xd2) | `FUN_1400c41b0` (CoreOwner closure) | 165062 | `state = (state != 1) ? 1 : 0` |
| sleep/wake (action `SleepNeverclick`, tray id 0xd3) | `FUN_1400c3de0` (CoreOwner closure) | 164850 | `state = (state == 2) ? 0 : 2`; state 2 also flips chrome flags at core `+0xe40/+0x7f8` (164907-164930) |
| hotkey config replaced (msg 0x503 / route apply) | `FUN_140095e00` | 127595 | swap entry vector → settle/deactivate active tool (`FUN_1400e7d30`, line 127612) → rebuild (callers: 127731/127838/128018/128055) |
| shared-keybind update | `FUN_140096630` | 128062 | deactivate tool w/ log *"No tool must be active while resetting the configuration."* (line 128281) → reorder entries → rebuild (line 128208); failure logs *"Failed to rebuild hotkeys after a shared keybind update: {}"* (line 128158) |
| single entry edited | `FUN_140096be0` | 128293 | if edited entry is a *tool* entry whose action == active/pending tool → deactivate (`FUN_1400e7df0`, call 128331) + log *"The active tool's keybind was modified."* (line 128335) |

While suspended/sleeping, only the resume chord is hooked, so **all other input passes to apps untouched** (no entry matches → `CallNextHookEx`).

### 6. Chord dispatch (msg 0x501) — main wndproc `FUN_1400612c0` (line 84480)

```
on 0x501 (wParam = heap 20B chord, lParam = 0x147d):            # 84700
  ctxCopy = AppContext copy (576 B, FUN_1400c3280)              # 84703
  for e in HotkeyManager.entries (stride 0x70):                 # 84705-84724
      if e.enabled(+0x68) && e(+0x1c) && e[5 dwords] == chord: break  # 84717-84722
  if e.mode(+0x28) == -1: throw                                 # 84725 → FUN_140040630 @84745
  if e.mode == 0:  ActiveToolManager.arm(HM+0x130, ctx, e.action)  # FUN_1400e7cb0 call 84730 (def 194523)
  else:            e.action.vtbl[1](e.action, ctx)   # direct execute @84736  = nvr::X::execute(AppContext)
  free(wParam)                                                  # 84741
```

Other wndproc messages (tray/UI chrome): `0x111` menu ids `0xd0` exit / `0xd1` open(`FUN_140179c20`, call 84541) / `0xd2` suspend(`FUN_14017a410`, 84548) / `0xd3` sleep(`FUN_14017abb0`, 84558) inside `if (param_4 == 0x111)` (84530); `0x401` = tray callback → `FUN_140062fc0` (84526); `TaskbarCreated` re-registers tray (registered line 3133, compared 84589 → `FUN_1400cdd80`); `0x113` timers (84605); `0x2b1` = `WM_DPICHANGED` (84640); `0x503` = hotkey entries replaced → `FUN_140095e00` (84747/84750); `0x50f` = execute+free release-trap closure (84754); `0x700` → `FUN_1400c77b0` (84809) whose 4 return values drive overlay show/hide combos (84811-84828) and which itself calls `rebuild` (168267/168716) `[so mode switches re-install hotkeys]`.

---

## Tool lifecycle

### Activation path (hotkey mode 0 → `ActiveToolManager::arm`)

`FUN_1400e7f80` (line 194644), reached via `FUN_1400e7cb0` (194519):

```
arm(trap, ctx, action):    # FUN_1400e7f80 (194644-194758)
  keys = action.sub(+8).vtbl[3](…)                    # per-action key set   (194675)
  lock(trap.mtx@+0xA0); insert keys into trap.set@0xF0 (FUN_1400ce9c0, 194691); unlock
  if action.sub.vtbl[0](…):  trap.pending(+0x140) = action                # 194695-194697
  if (!action.sub.vtbl[1](…, 194699) || trap.current(+0x138) != action):
      ShowWindow(overlay1, SW_SHOWNA); ShowWindow(overlay2, SW_SHOWNA)     # 194701-02
      if (!action.sub.vtbl[2](…, 194703)) { if !isHooked(trap.hook): hook }  else { if hooked: unhook (194713) }
                                    # trap.hook = ActiveToolManager's KeyboardHook (input capture)
      if trap.current && trap.current != action: current.vtbl[2](current, ctx)   # deactivate old  194719-20
      trap.current = action                                               # 194722
      ctx.evt@0x38 → invoke (194730)
      activate callback: prev==action ? action.vtbl[1](action, ctx) : action.vtbl[0](action, ctx)  # 194735-194743
      PostMessageW(overlay1, 0x50c, 0, 0)                                # 194744
  else:  # vtbl[1] && current==action → settle `FUN_1400e7d30` (call 194751): pending==current ⇒ close ⇒ toggle-off (e7e80); non-toggle tools take the arm branch again (refresh)
```

- The trap hook's payload callable is `ToolInputHookCallback` when input capture is on (built at `FUN_1400e7b40` line 194447-194503, vtable `0x14026b118`) or `KeyReleaseTrapCallback` when armed by `FUN_1400e83d0` (line 194812, vtable `0x14026b0e8`, constructor `FUN_1400e8a90` line 195200).
- Asynchronous activation with rollback: failure handlers log *"Tool activation failed: {}. Rolling back to idle."* (456115) / *"…unknown error. Rolling back to idle."* (456139) and call `FUN_1400e8290` (calls at 456123, 456148); a third handler only logs *"Deactivation of the failed tool also failed."* (456164).
- Close-to-idle path `FUN_1400e7e80` (194608): unhook capture (194614) → clear key set@0xF0 (194629) → arm KeyReleaseTrap (194631) → if current: `current.vtbl[2](current)` deactivate + `current=0`, `ShowWindow(SW_HIDE)` ×2 (194635-36), post `0x50c` (194637). Reached from settle `FUN_1400e7d30` (194547, call 194570).

### Input capture while hints are up — `ToolInputHookCallback` (`FUN_1400e8af0`, line 195226)

```
op(isUp, vk, extra):
  if extra == 0x147d: return 0                       # 195237
  if vk ∈ {LWIN,RWIN,LSHIFT,RSHIFT,LCTRL,RCTRL,LALT,RALT}: return 0   # modifiers pass through  195242
  if vk ∈ passthroughSet: return 0                   # 195250
  if DOWN:  insert vk into capturedSet;
            PostMessageW(hwnd, 0x502, heap{modifierSnapshot8, vk} /*12 B*/, 0x147d)  # 195261
            return 1                                 # swallowed — hint letters never reach target app
  if UP:    if vk ∈ capturedSet: erase; return 1     # paired release swallowed  195272
```

Consumers of `0x502`: wndproc **prefilter** `FUN_140061bc0` (line 84835) broadcasts every main-window message as a 20-byte record `{msg, wParam, lParam}` to the sink at `HotkeyManager+0x268` — that is how tool event chains see `0x502` even though the big switch does not handle it (switch covers 0x501/0x503/0x50f but not 0x502). Tool-side match: `FUN_140177d70` (line 313198): `if (*param_3 == 0x502) { payload = *(param_3+2); vk = payload[1]; scan bindings vector (stride 0x88) where +0x80 active && +0x10==vk && modMatch(snapshot, binding[0..3]); }` — same 20-byte `{4 reqs, vk}` prefix as hotkeys. Parallel consumers (other tools): `FUN_14018be60` (329760), `FUN_14018ff40` (332891), `FUN_140194640` (336477).

### Key-release trap — `KeyReleaseTrapCallback` (`FUN_1400e8940`, line 195150)

```
op(isUp, vk, extra):
  if extra != 0x147d:                                # only "real" keys considered (195166)
     switch vk: modifiers/win → return 0 (no timeout check)             # 195168-195176
     if isUp && vk ∈ capturedSet@+0x10:
         erase;  if set now empty: FUN_140025390(this+0x50)  # fire deferred closure (execute pending action)  195180-195182
         return 1                                     # swallow the key-up
     if now − t0(this+8) > 1 000 000 001 …: invoke timeout closure this+0x88   # ≈1.001 s, line 195184
  return 0
```

- `FUN_140025390` (line 32765) = invoke stored `std::function` at +0x50 (throws `_Xbad_function_call` if empty).
- Arm: `FUN_1400e83d0` (194812) first unhooks any existing trap hook (194848), snapshots the held-key set (`FUN_1400e8cf0` copy of set@0x60, line 194887) + timestamp into a fresh `KeyReleaseTrapCallback`, swaps it into the trap hook, installs it `hook()` (194933). Called from `FUN_1400e7e80` (194631) and `FUN_1400e8290` (194789).
- Disarm: `ActiveToolManager::handleKeyReleaseTrap(CoreServices)` (`FUN_1400e8750`, line 195006) → `PostMessageW(hWnd, 0x50f, heapClosure, 0x147d)` (195028) → wndproc 0x50f (84754) invokes closure `FUN_1400e8860` (195073) which clears the installed flag and dispatches `unhook` to the InputHookThread. `[GAP: textual caller of handleKeyReleaseTrap not found — bound through an event/closure table.]`

### Deactivation — `FUN_1400e8290` (line 194761)

```
unhook input-capture hook if hooked (194771-73); lock; clear set@0xF0 (`FUN_140038dc0`, 194787); unlock;
FUN_1400e83d0 → arm KeyReleaseTrap so lingering key-ups of the closing chord are swallowed (194789)
if current(+0x138): current.vtbl[2](current) # action deactivate (194793); pending==current → pending=0 (194794-96); current=0 (194797)
ShowWindow(overlay1, SW_HIDE); ShowWindow(overlay2, SW_HIDE)     # 194798-99
PostMessageW(overlay1, 0x50c, 0, 0)                               # 194802
```

`FUN_1400e7df0` (194583) = "clear pending, then settle" — invoked before config-driven rebuilds that must drop the active tool: `FUN_140096ae0` config reset (call 128277) and `FUN_140096be0` keybind-modified (call 128331); plain entries-replace settles via `FUN_1400e7d30` instead (call 127612).

### Esc / hints-up key handling (routing level)

- Esc, Enter, hint letters, `'`, Tab etc. are **not hardcoded in the input layer**: they arrive as `0x502 {snapshot, vk}` and are matched against the active tool's binding vector (stride 0x88, `+0x10 = vk`, `[0..3] = mod reqs`, `+0x80 active`) — e.g. `FUN_140177d70` line 313202; the binding list contains a byte `local_d0` where values `0x0d/0x0e` get special handling (line 313248: `(local_d0-0xd) < 2`) consistent with Enter/Shift+Enter finish semantics `[INFER]`. Whether Esc is a binding or separate flag: `[GAP — hint-side; see HintSystem report]`.
- No `vk == 0x1b` comparison exists in the input layer (grep `== 0x1b` → 2 unrelated hash constants), supporting "Esc is config/binding data".

### Keybind sets / routes

- `SharedKeybindSets` lives at `HotkeyManager+0x20`; rebuild-after-shared-update = `FUN_140096630` (128062). REST endpoints (strings line 116661-116691): `GET/POST /shared-keybinds`, `GET /shared-keybinds/defaults`, `GET/PUT /shared-keybinds/:classId`; settings JSON fields `hotkeys`, `sharedKeybinds` (lines 121434/121450, malformed-field error 121464); serializer tag `action_keybind_json` + field `keybind` (292323/292356).
- Route type names (RTTI getters, lines 117475-124527): `GetHotkeysRoute`, `CreateHotkeyRoute`, `UpdateHotkeyRoute`, `ToggleHotkeyRoute`, `DuplicateHotkeyRoute`, `SwapHotkeysRoute`, `DeleteHotkeyRoute`, `FactoryResetHotkeysRoute`, `UpdateSharedKeybindsRoute`, `GetSharedKeybindsRoute`, `GetSharedKeybindDefaultsRoute`, `GetKeyCodeToUnicodeMapRoute`, `GetKeyPositionToKeyCodeMapRoute`, `GetAppConfigRoute`, `PatchAppConfigRoute`, `FactoryResetAppConfigRoute`, `ImportSettingsRoute` — the GUI config app drives hotkeys over a local REST server (`nvr::RestServer::run(HWND, EventHub&)`, RTTI 124527).

---

## Window management

Conventions: function-level line cites from the WindowMgmt scout; `strings N` cites refer to the exe strings dump (content quoted; scratch dump has since been regenerated with different numbering).

### Direction enums

| enum | values | evidence |
|---|---|---|
| `CycleWindows::Direction` | `0 = Forward`, `1 = Backward` [INFERENCE from config names `Forward`/`Backward` + error `Invalid cycle direction: {}`] — code only tests `0 vs ≠0` (lines 373154, 373596) | dispatch `FUN_1401c2650` (373041); RTTI signature 374300 |
| CycleWindows **scope** (member `+8`) | `0` = through-overlapping (trace 373127), `1` = same-monitor (373588), `2` = across-monitors (373356), `3` = all-windows (373505) | dispatch 373041-373596 |
| `FocusWindow` direction (5-entry table `DAT_14028d9b0`, loops 382872/383512) | `0=Left` (410768), `1=Right` (410779), `2=Up` (410790), `3=Down` (410801) thunks `FUN_1401f1420/1440/1460/1480`; `4=behind` → `DoSelectBehind` trace 383994 in `FUN_1401cf350` (383928), action id `FocusWindowBehind` | RTTI 384340 region |
| `MoveWindow::Direction` (4-entry table `0x28d500`, parse `FUN_1401c8bc0` 377794) | `0=Left` (dx=−amt, 378112), `1=Right` (+amt, 378116), `2=Up` (dy=−amt, 378120), `3=Down` (+amt, 378124) | |
| MoveWindow **target** (parse `FUN_1401c7ee0` 377145, tag `+0x10`; switch `FUN_1401c97a0` 378408) | `0=Pixels` (amount `+0xc`), `1=Monitor`, `2=Desktop`, `3=Edge`, `4=Center`, `5=Back` | |
| Edge position (table `0x28d430`, switch 379015-379070 → `FUN_1401ca8f0` 379185) | 0=Left, 1=Right, 2=Top, 3=Bottom, 4=TopLeft, 5=TopRight, 6=BottomLeft, 7=BottomRight [INFERENCE from combo pattern `Top∧Left` etc.]; primitives 411032/411126/410938/411219 | |

**README chord mapping** (`notes/public/README-upstream.md`): Shift+W/A/S/D → FocusWindow spatial; Shift+Z → `FocusWindowBehind` (value 4) [INFERENCE via action-id]; Shift+Q/Shift+W (README conflict) → two `CycleWindows` bindings differing only in direction. *Which physical key = which enum value is runtime binding data (served by `/shared-keybinds/defaults`), not compiled-in* → unresolved.

### Cycle windows

- **Forward**: scan z-list top→bottom, first filter match; then send the previously-focused window to bottom `SetWindowPos(oldfg, HWND_BOTTOM, 0x213)` (`FUN_1401c35d0` 373646; send-to-back `FUN_1400feba0` 213365). Overlap-scope Forward picks the **first** overlapping window (`FUN_1400fe560` 213003) + send-to-back (373190).
- **Backward**: scan bottom→top, first match, **no** z-reorder (`FUN_1401c3bf0` 373936). Overlap-scope Backward picks the **bottom-most** overlapping window (`FUN_1400fe8c0` 213188).
- Eligibility filter (`EnumWindows` cb `FUN_14003a600`, 51088): visible; class ≠ `Windows.UI.Core.CoreWindow`; not cloaked (`DwmGetWindowAttribute(…,0xd)` `FUN_14003c7c0`); owner filter `FUN_14003ab20`; not shell; area > 1 px²; non-empty title; minimized windows dropped at merge (`FUN_140124600` 244649).

### Focus spatial picker — `wnd::GetWindow(HWND, Direction)` (`FUN_1401f0c80`, 410337)

Geometric half-plane selection, **not** a GW_HWNDNEXT z-walk (anchor hypothesis refuted):
- tests vs foreground rect: dir0 `cand.left < fg.left`; dir1 `fg.right < cand.left`; dir2 `cand.bottom < fg.top`; dir3 `fg.bottom < cand.bottom` (410470-410500).
- perpendicular margin = 15 % of fg height (dirs 0/1) or width (dirs 2/3) (410440); first consider candidates in the aligned band (`FUN_1401f0b70`), else the directional band.
- tie-break = min distance (`FUN_1401f14f0`: dir0 `fg.l−cand.l`, dir1 `cand.l−fg.r`, dir2 `fg.t−cand.t`, dir3 `cand.t−fg.b`).
- returns `expected<optional<HWND>, Error>` (RTTI 410817/410855).

### Move window (traces Center 378042 / Monitor 378586 / Desktop 378884 / Edge 379292)

- **To monitor** (`FUN_1401c97a0` case1, 378408): neighbor = direction thunks `FUN_1401f22e0/2300/2320/2340` (411591-411624) → `FUN_1401f20a0` (411448): monitor list `FUN_140101d10`, predicate = **exact edge abutment** (e.g. `entry.right == curr.left` for Left, `FUN_1401f2360` 411635); **first match, no wrap-around**; none → log `"No monitor detected."` (378660). The trailing `bool` = config **`maximize`** (parse 377448), *not* animate: posts events vtable `0x14026d008` (378690) / `0x14026d068` (378760). Zoomed/Iconic → `ShowWindow(fg, SW_RESTORE=9)` (378745) + 2× rect-snapshot events (`0x14026d038`).
- **Apply** `FUN_1401f1da0` (411315): relative position rx/ry preserved & clamped (411360-411395); move via DPI-aware wrapper `FUN_14003df10` (54288) → `SetWindowPos(hwnd, 0, x, y, w, h, 0x204 /*NOZORDER|NOOWNERZORDER*/)` (`FUN_14003d860` 53979, call at 54000); applied twice when DPI awareness == 2 (411425).
- **Tool wrapper**: `window_move_tool::Tool::handleMoveToMonitor` RTTI 337532, region 337081-338451.

### Snap — `window_snapping_tool::CreateWindowMoveEvent` (RTTI 334875)

Lambda `FUN_140192960` (334881): target = **union(old,new)** `{min l, min t, max r, max b}` (334897-334912) then **one** `SetWindowPos(…, 0x204)` (call at 334918 → `FUN_14003df10` 54288 → `FUN_14003d860` 53979/54000) — a single jump, not stepwise; failures log `"Failed to move window."` / `"Failed to get frame padding."` (334930/334990). `[INFERENCE: perceived motion comes from the animation queue, not this event.]`

### Tiling — `TileWindows` (`FUN_1401d0a80`, trace 385220)

- `FrameCache` stride **0x30**: `+0x00` HWND, `+0x08..0x17` frame {l,t,r,b}, `+0x18..0x27` assigned cell rect, `+0x28` assigned flag (build 385470-385560; nearest-center assignment 385560-385640).
- animation events queued: `0x14026d1c8` frames (385695), 2× `0x14026d1f8` cells+style (385715-385730).
- **ApplyTiling** (`FUN_1401d2180`, 386142): `style==0` (**Fit**) → `scale=min(cellW/winW, cellH/winH)`, window scaled and centered in cell (386150-386172; trace `TileWindows.ApplyTiling.Fit` 386194); else (**Stretch**) → fill cell exactly (386185; trace `…Stretch` 386207). Config names {`Fit`, `FrontTwo`, `Fill`} — numeric mapping unresolved (code tests `==0` vs else). `FUN_1401d2480` (386269) pre-restores maximized windows.

### Virtual desktops

- **Switch/create/close desktop** (`VirtualDesktop.execute`, `FUN_1401b51f0` 362568, op `+8`): op0 **Ctrl+Win+←** `{0x11,0x5b,0x25}` (362655-362665); op1 **Ctrl+Win+→** `{0x11,0x5b,0x27}` (~362710); op2 **Ctrl+Win+D** `{0x5b,0x11,0x44}` (~362745); op3 **Ctrl+Win+F4** `{0x5b,0x11,0x73}` (~362775); buffered → combo builder `FUN_140037b90` (48791) → injector `FUN_14017a780` (314838).
- **Move window to desktop** (target `Desktop`, trace 378884): **IVirtualDesktopManager** COM at `services+0x598` (init flag `+0x5e8`); ops `FUN_140105d00` (219189; arg 3 = left / 4 = right) + `FUN_140105f70` (219317); failure string `"Failed to create IVirtualDesktopManager."` (decomp CoCreate site 51867, CLSID `DAT_140259030` / IID `DAT_1402794e0`, CLSCTX 0x17, `FUN_14003b330`). Interface methods not decoded [unresolved].

### Animations & `enableWindowAnimations`

- Config parse `FUN_1400f6360` line **124158** (siblings `enableAnimations` 124147, `enableMouseAnimations` 124152); serialize **141131-141135** (field `enableWindowAnimations`).
- Runtime gate = `*(char*)(services+0x43)`: `FUN_140148b80` (274975) `0 → destroy/free` (`FUN_14000fd50` 14177) else enqueue (`FUN_140148b20` 274946); same test inline in `InvokeWindowAnimation` (382665), `FUN_1401ea430` (404870), window-move tool (337195). `[INFERENCE: services+0x43 == this setting]`
- Pipeline: events pushed by `FUN_1401451e0` (272085) into `*(services+0x1018)` = `nvr::anim::AnimationQueue`, drained by the **AnimationWindow thread** (`AnimationWindow::threadMain` RTTI 68692; class name `"animation window"`); `updateAnimationsEnabled` creates/destroys that thread (failure string `"updateAnimationsEnabled: failed to create animation window"`; body unresolved).
- `InvokeWindowAnimation(CoreServices, HWND)` (trace 382590, RTTI 384340) = generic handoff used by focus/monitor moves.

---

## Tray, window messages & chrome (main wndproc)

The main window `FUN_1400612c0` (84480) is the hub for tray + custom messages. Full catalog:

| msg | meaning | handler |
|---|---|---|
| `0x401` (WM_USER+1) | **tray callback** — `uCallbackMessage=0x401` assigned in the NOTIFYICONDATA builder `FUN_140114070` (231279; NIM_ADD path calls it at 150568); `LOWORD(lParam)` = mouse event | → `FUN_140062fc0` (85771): `0x201` LBUTTONDOWN (85801) → "Open" flow (`FUN_140179c20` call 85824 = show/activate main window, same callee as menu id 0xd1) + app-bar activation (vtable calls +0x180/+0x178/+0x188, HRESULT `0x8899000C` gate); `0x204` RBUTTONUP (85826) → build popup (below) |
| `0x111` WM_COMMAND | menu ids | `0xd0` exit → `FUN_1400d1510` + `DestroyWindow` (84533); `0xd1` Open → `FUN_140179c20` (84541); `0xd2` Suspend/Resume → `FUN_14017a410` = `SuspendNeverclick.execute` (84548); `0xd3` Sleep/Wake → `FUN_14017abb0` = `SleepNeverclick.execute` (84558) |
| `TaskbarCreated` | registered `RegisterWindowMessageW` (3133) | re-create tray icon → `FUN_1400cdd80` (172586; also triggers icon-cache refresh 172834-57) (84589-84602) |
| `2` WM_DESTROY | shutdown | `FUN_140062170` (85090): unhook (`FUN_140022e80` 85211) + **`Shell_NotifyIconW(NIM_DELETE=2, …)`** (85215) |
| `0xf` WM_PAINT | paint | `FUN_140061cb0` (84879): BeginPaint → sink(HM+0x268).vtbl+0x18(core) → EndPaint (84898) |
| `0x1a` WM_ACTIVATEAPP | app activate | `FUN_140061ef0` (84971) |
| `0x47` WM_MOVE | moved | `FUN_140061e40` (84908) |
| `0x7e` WM_DPICHANGED_AFTERPARENT | dpi | `FUN_140062070` (85051) |
| `0x113` WM_TIMER | timers 0x403/0x404/0x405/0x407/0x504 | 84605-84630 |
| `0x218` | wParam 0x12 → `FUN_140062760` (name unverified) | 84633 |
| `0x2b1` WM_DPICHANGED | wParam bitmask 0x13a | theme/dpi update `FUN_140144c90` (84640-84645) |
| `0x31e` | theme names `"primary"`/`"secondary"` | `FUN_1400625f0` ×2 (84651-84660) |
| `0x402` | single-instance guard | logs `"Only one instance may be open."` (84675) |
| `0x409` | wParam 0 → constant `0x34630b8a000` (duration; units not decoded) | `FUN_140062760` (84666-84668) |
| `0x406/0x408/0x504` | overlay/UI commands | `FUN_1400c4f70`/`FUN_140062e10`/`FUN_140061d50` |
| `0x508` | taskbar WinEvent ping | `FUN_1400416a0` = refreshTaskbarIcons (84662) |
| `0x509` | shell-change ping | `FUN_140041420` + `SHChangeNotification_Locate`/`HandleFree` (84770-84775) |
| `0x50a` | dedupe map insert (`FUN_1401444e0/446e0`) | 84780-84786 |
| `0x50b` | GPU device lost | log `"GPU device lost. Rebuilding graphics pipeline."` + `FUN_140062070` (84781-84790) |
| `0x501/0x502/0x503/0x50c/0x50f/0x510` | hotkey/tool protocol | see Hotkey/Tool sections (0x503 at 84747, 0x50f at 84754) |
| `0x700` | hints/mode request | `FUN_1400c77b0` (84809) → return 1..4 drives overlay show/hide combos (`FUN_1400c4f20`/`c4f70`/`c44f0`) + itself rebuilds hotkeys (168267/168716) |

**Tray icon lifecycle**:
- Add: `FUN_1400b3790` (150494) → `Shell_NotifyIconW(NIM_ADD=0, lpData)` (150722); failure logs `"Failed to create tray icon."`.
- Modify/swap: `FUN_1401456c0(core+0x590, out, which)` (272336) looks up an icon id in a table and does `Shell_NotifyIconW(NIM_MODIFY=1, …)` (272368) — called with 1/0 from `SuspendNeverclick.execute` (314783/314808) and `SleepNeverclick.execute` (315112/315133) ⇒ **state changes swap the tray icon**.
- Delete: WM_DESTROY path (85215).
- Explorer restart: `TaskbarCreated` re-add (above).

**Tray popup** (built on `0x204`, `FUN_140062fc0` 85771): reads state via `*(HM+0x278)` (85863):
```
AppendMenuW(0,           0xd1, L"&Open")                     # 85864
AppendMenuW(MF_SEPARATOR, 0, NULL)                            # 85865
label = state==1 ? L"Resume" : L"Suspend";
AppendMenuW(state==2 /*check*/, 0xd2, label)                  # 85866-85870
label = state==2 ? L"Wake" : L"Sleep";
AppendMenuW(state==1 /*check*/, 0xd3, label)                  # 85871-85875
AppendMenuW(MF_SEPARATOR, 0, NULL); AppendMenuW(0, 0xd0, L"Exit")   # 85876-85877
SetMenuItemInfoW(menu, 0xd1 /*&Open*/, MIIM_STATE, fState=0x1000 /*MFS_DEFAULT — default item*/)  # 85892
SetForegroundWindow(trayWnd); GetCursorPos(&pt);                                            # 85893-85894
TrackPopupMenu(menu, TPM_RIGHTBUTTON(0x20), pt, trayWnd); SendMessageW(trayWnd, 0,0,0)      # 85895-85896
```
**Tray state mapping** (cross-evidence): labels flip exactly at states 1/2 (`Resume` at state1, `Wake` at state2) and the hook rebuild collects resume-chords per state (state1 hooks `SuspendNeverclick` entries, state2 hooks `SleepNeverclick`) ⇒ **state1 = suspended, state2 = sleeping** — certain. The check flags remain crossed (`Suspend` item checked iff state==2, `Sleep` item iff state==1, 85870/85875) — recorded verbatim; visual intent [open].

**Audio** — two mechanisms:
1. **System-sound player**: single `PlaySoundA` site — `FUN_14013d450` (265119): rate-limited (`now − last < *cooldown_ms × 1e6` in 100-ns units, 265157-265159, cooldown object at `core+0x768`), path = `"{GetWindowsDirectoryA()}\Media\{name}"` (format 265201, dir fetch 265165), `PlaySoundA(path, NULL, 0x20003 /*SND_ASYNC|SND_NODEFAULT|SND_FILENAME*/)` (265208). Sole caller = **`SleepNeverclick.execute`** (call 315147) with names `"Speech Sleep.wav"` (0x140288a38, len 16, branch 315123-24) vs `"Speech On.wav"` (0x140288a50, len 13, branch 315144-45) — Windows' Media-folder sounds mark sleep/wake. Suspend is silent.
2. **Embedded WAV resources** (external hint confirmed): PE resource directory has named type **`WAV`** with **ids 301 (21 916 B) and 302 (29 556 B)**, both genuine `RIFF….WAVE` files (verified via pefile). Loaded at main init `FUN_14005bea0` — two `FUN_1400f6960(&buf, *(u32*)(cfg+0x94))` calls (80935-80936) [INFERENCE: ids from config struct +0x94 = 301/302 = success/error cues]; loader `FUN_1400f6960` (206109) = `FindResourceW(GetModuleHandle(0), id, type@DAT_140283630 /*len 3 = L"WAV"*/)` + `LoadResource` (`FUN_1400f6810`, 206061). Async init = `nvr::InitAudioAsync` (RTTI 157863). **Playback backend + success/error mapping unresolved** (no waveOut/XAudio2/DirectSound/MCI/MediaFoundation imports or strings; body of InitAudioAsync not located [GAP]).

**Update checks**: base URL `https://www.neverclick.com` + path `/api/version` assembled in global init `FUN_140007130` (5493-5541: qword literals `"/api/ver"+"sion"`; app name `"Neverclick"`); transport = **WinHTTP** (`WinHttpOpen(L"Neverclick", 4, 0, 0)`, 236163). Check + re-check timer in `FUN_140060a70` (84134): **`SetTimer(wnd, 0x407, 3 600 000 ms /*1 hour*/)`** (84403; failure string `"Failed to set the update re-check timer."` 84405; timer 0x407 arrives in the wndproc 0x113 branch 84605-84630 ⇒ hourly re-check). `Neverclick::maybeRecheckForUpdates(string_view, optional<duration_ns>)` (RTTI 88067/88291) = async fetch returning `expected<UpdateInfo,string>`; **UpdateInfo JSON fields** = `latestVersion`, `downloadUrl`, `releaseNotes`, `releaseNotesUrl` (surfaced by `GetUpdateInfoRoute` 118523, field reads 118686/118706/118745/118758). GUI REST: `/version` (116767), `/update-info` (116879), `/update` (116895), `/update-check` (116911); outcomes log `"No update available."` (118090) or `"Download complete. Spawning updater for silent install."` (118390) → spawns the separate updater (`"CreateProcess failed for updater (error "`, `"Failed to spawn updater ({}): {}"`, `"Response missing 'update' field"`; installer artifact string `"NeverclickSetup.exe"` 118101). Version-compare body [GAP]. Companion binaries in strings: `neverclick-ui.exe`, graphics probe (*"Probe binary not found next to neverclick.exe."*).

*(Startup/update-check/notification research merged above; `enableNotifications` consumption remains open — see Gaps.)*

---

## Config touchpoints

### Files & storage

- Two JSON files: **`app-config.json`** and **`hotkey-config.json.gz`** (gzip-compressed JSON — read path `FUN_140020240(out, core+800 /*base dir*/, name)`): names at 5649 (loader), 84324 (read), 165972/166150 (SavingManager writes). Base directory lives at `core+800` [exact folder value not decoded — likely roaming profile via `SHGetKnownFolderPath` helper `FUN_1400a6e30`-family; error strings 206407/206439/206467].
- Providers: `nvr::io::AppConfigFromDiskProvider(path, KeyboardLayout)` (async task RTTI 76460/76889 — config load is keyboard-layout-aware), `HotkeyEntriesFromDiskProvider(path)` (79473).
- Saves: `nvr::SavingManager::performHotkeyConfigSave(CoreServices, vector<HotkeyEntry> const&, SharedKeybindSets const&)` (RTTI 166373), `performAppConfigSave` (166412).

### app-config keys (parser `FUN_1400f6360`, lines 124100-124260; serializer ~141092-141359)

| key | parse | serialize | effect |
|---|---|---|---|
| `launchAtStartup` | 124129 | 141092 | startup-folder shortcut add/remove |
| `runOnStartup` | 124134 | — (legacy alias? [open]) | same updater: `AppConfigUpdater::updateRunOnStartup` log scope 201341 |
| `enableAnimations` | 124150 | 141112 | animation master flag |
| `enableMouseAnimations` | 124152 | — | mouse-hover/click animations |
| `enableWindowAnimations` | 124158 | 141131-35 | window-move animations (see Window section runtime gate `services+0x43`) |
| `enableNotifications` | 124162 | 141142 | notifications [ChromeCfg detail] |
| `showStartupNotification` | 124146 | 141102 | startup toast/balloon |
| `keyCodes` | 124178 (parse 203303) | — | layout key-code map (keyboard-layout support) |
| `keyOverrides` | 124182 (parse 201708/201777; must be object — error 204596) | 141359 | per-key remapping overrides |
| `hotkeys` | 121434 (malformed error 121464) | (hotkey-config file) | entry list |
| `sharedKeybinds` | 121450 | (same) | shared keybind sets |

### Startup = startup-folder shortcut, NOT registry Run

`Startup Folder Manager` = `FUN_1400b51a0` (151841): logs `"Failed to initialize Startup Folder Manager: {}"` (151883), `"Failed to detect startup shortcut presence: {}"` (151916), `"Failed to remove Neverclick from startup folder: {}"` (151958), `"Failed to add Neverclick to startup folder: {}"` (152000); `.lnk` helper `FUN_140114850` (231720, ext concat 231787); driven by `AppConfigUpdater::updateRunOnStartup` (log scope 201341). **No `CurrentVersion\Run` literal exists anywhere**; the generic HKCU registry writer `FUN_140035bd0` (47221, `RegCreateKeyExW`+`RegSetValueExW` REG_SZ) is used **only** for GPU graphics preference (`L"GpuPreference=1;"` 148264, call 148342) — corroborated by full-file search. Config keys `launchAtStartup` (124129) and `runOnStartup` (124134) both feed the same updater [relation open].

### REST API (GUI config app ↔ engine) — cpp-httplib, **0.0.0.0:7340**

- Server = cpp-httplib (`httplib::Server::listen` RTTI 125478); bind `"0.0.0.0"` (116952), port literal `0x1cac` → `std::to_string(7340)` (125548); observed client URL `http://127.0.0.1:7340`.
- Full route table (helpers: `FUN_140095aa0`=GET, `FUN_140093fc0`=POST, `FUN_140093f20`=PUT/DELETE [INFERENCE], `FUN_140094180`=`:id`):
  `/app-config/reset` (116507); `/hotkeys` GET/POST/DELETE (116523/116539/116555); `/hotkeys/:id` (116572); `/hotkeys/swap` (116597); `/hotkeys/:id/duplicate` (116613); `/hotkeys/:id/toggle` (116629); `/hotkeys/reset` (116645); `/version` (116767); `/update-info` (116879); `/update` (116895); `/update-check` (116911); `/nvidia-power-mode` (116941); `/shared-keybinds` + `/shared-keybinds/defaults` + `/shared-keybinds/:classId` (116661-116691); keymap routes (GetKeyCodeToUnicodeMap/GetKeyPositionToKeyCodeMap, RTTI 118824/119069) in 117475-124527.
- Route apply → `CoreOwner` lambda `FUN_1400c4270` (165133) → `FUN_140095e00` (entry swap + settle + rebuild).

### Compiled-in default keybinds — `FUN_140175660` (310727-312323) + `FUN_140181cb0` (321108+)

Defaults are **code, not strings** (no `"Ctrl+Enter"` literal exists in the binary). The 16-byte shared blob = `{ctrlReq, altReq, shiftReq, winReq}` — proven by `uVar1..4 = {0, 0, 3, 0}` (**shift=either**) at 311549-311552 reused across the WASD/QE/ZFR blocks, and `uVar5..8 = {0,0,0,0}` (no modifiers) at 311495-311498. Confirmed defaults:

| chord | vk | param | action id | lines |
|---|---|---|---|---|
| **Shift+W** | 0x57 | 2 (Up) | 0x0c = FocusWindow | 311711-18 |
| **Shift+A** | 0x41 | 0 (Left) | 0x0c | 311719-26 |
| **Shift+S** | 0x53 | 3 (Down) | 0x0c | 311727-34 |
| **Shift+D** | 0x44 | 1 (Right) | 0x0c | 311735-42 |
| **Shift+Q** | 0x51 | 1 (Backward) | 0x10 = CycleWindows | 311743-50 |
| **Shift+E** | 0x45 | 0 (Forward) | 0x10 | 311751-58 |
| **Shift+Z** | 0x5a | — | 0x11 = FocusWindowBehind | 311759-65 |
| **Shift+F** | 0x46 | — | 0x12 | 311766-72 |
| **Shift+R** | 0x52 | — | 8 | 311773-79 |
| **Esc** (no mods) | 0x1b | — | 2 | 311503-10 (`FUN_140166770` appender — separate list, likely tool keybinds; also Backspace 0x8 → action 8 @311512-23, Space 0x20 @311536-47) |

This resolves the README's "Shift+Q/W cycle" conflict: **Shift+Q = Backward, Shift+E = Forward** [param→direction mapping per Window section enum; Shift+Z = behind ✓ README]. Further groups (no-modifier `{…, 0xde…}` entries with actions 0x15/0x16/0x17 @311780-311815; `{3,0,'D'/'M','P'}` triples; scan-ish ids 0xbc/0xbe/0xbf with u16/u8 fields @311823-311860; `FUN_1401683f0` vs `FUN_140166770` = two appenders = actions vs tools) are partially decoded `[GAP: full table needs struct types]`. `hotkey-config.json.gz` initial load also seeds from these defaults (call at 5645).

- `GetSharedKeybindDefaultsRoute` handler = `FUN_14008fcb0` (122377, vtable `0x14026a178` slot 2) → `FUN_14015e970` (291865) → serves the **compiled-in defaults** (HTTP 200).

### JSON schema touchpoints

- **hotkey-config.json.gz**: gzip of JSON, **schema-versioned** — errors `"Failed to parse hotkey config from '{}'"` (79573), `"Hotkey config at '{}' has unsupported schema version {}"` (79600), `"Failed to load hotkey config from '{}': {}"` (79819), loader `FUN_14005b140` (79479, = `HotkeyEntriesFromDiskProvider` region).
- **HotkeyEntry JSON**: requires `"keyCombo"` (error `"Missing key combo"`) + `"action"` (parse region ≈293972 [part_02:46511]); serializer field `keybind` (292356) + tag `action_keybind_json` with error `"[action_keybind_json] Failed to serialize key combo. Skipped."` (292323). Exact JSON names for the 4 modifier-req values and mode byte (+0x28)/flag (+0x1c) [GAP].
- **app-config.json**: parser `FUN_140091790` (123930) / serializer `FUN_1400a6e30` (140714, field-offset↔name swap via `FUN_1400a9550`); settings-file `"version"` schema check (121416-121431, error 121880). AppConfig struct offsets: `enableEventBatching` +0x3c (141061), `enablePerfectDesktopAndTaskbarIcons` +0x3d (141071), `enableVisibilityToScreenCapture` +0x3e (141081), `enableAnimations` **+0x41** (parse 124150 / ser 141112), `enableMouseAnimations` **+0x42** (124154 / 141120), `enableWindowAnimations` **+0x43** (124158 / 141132), `enableNotifications` **+0x44** (124162 / 141142), `enableUppercaseHints` +0x45 (141152), `enableProgressiveHints` (141838). Default-struct writer for `enableAnimations` at 456557. **Note**: the window-animation runtime gate `*(char*)(services+0x43)` (Window section) coincides with this offset — upgraded to likely-certain `[INFERENCE]` (config object ≈ services view).
- `keyCodes` (map, `FUN_1400f3640` @124178, ser 141224; validated `"Invalid key codes."`) and `keyOverrides` (object, `FUN_1400a3300` @124182, ser 141359; drops invalid entries: `"Dropped {} invalid key override entries."`, `"{}" is not a valid key position"`) feed the keymap REST routes — per-key-position remapping on top of layout `keyCodes`.

---

## UIA & elevation

### UIA: consumed, never exposed

Full-decomp search found **zero** of `IRawElementProvider`, `UiaReturnRawElementProvider`, `UiaHostProviderFromHwnd`, `WM_GETOBJECT`, `UiaAddEvent`, `UiaClientsAreListening` ⇒ the app implements no UIA provider; overlay windows are not accessibility-exposed. (Hidden window literally named `"Neverclick UI Automation"` at 62866 is a marshaling message window, not an exposure.) Its only accessibility registration is the OS-level `uiAccess="true"` manifest (below).

**Interface inventory** (interface → use → evidence):

| UIA interface | how obtained | members used | purpose | evidence |
|---|---|---|---|---|
| **IUIAutomation** — CLSID blob `DAT_140283bd0` = **{FF48DBA4-60EF-4201-AA87-54103EEF594E} = CLSID_CUIAutomation** (decoded from .rdata bytes `a4 db 48 ff …`, verified with `vt.py str`); IID blob `DAT_140283bc0` = **{30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}** [interface name to verify against UIAutomationClient.h] | `CoCreateInstance`, CLSCTX=1; error `"Failed to create UI Automation instance."` | +0x30 ElementFromHandle; +0x90 control-view condition; +0xa0 CreateCacheRequest; +0xb8 CreatePropertyCondition; +0x100 AddAutomationEventHandler; +0x108 RemoveAutomationEventHandler | all consumption | `FUN_1400f7600` 206857; 206958; 207300; 207781-89; 63883 (add `(0x4e26, el, 7)`); 63561-62 (remove) |
| **IUIAutomationCacheRequest** | CreateCacheRequest | AddProperty(**0x7531 = UIA_BoundingRectanglePropertyId**) | cache rects in FindAllBuildCache | ≈207020 (`"Failed to add property."`), ≈207360, 207851 (`"Failed to add property to cache request for Desktop icon retrieval"`) |
| **IUIAutomationElement** | ElementFromHandle | +0x40 FindAllBuildCache(scope 4=Descendants — bbox/taskbar; scope 2=Children — desktop; errors `"Failed to build cache."`, `"Failed to build cache for Desktop icon retrieval."`); BoundingRectangle getter +0x258 | element geometry | ≈207168 `FUN_1400f7b90`, ≈207530 `FUN_1400f8330`, ≈207940 `FUN_1400f8b00`, ≈206685 `FUN_1400f7080` |
| **IUIAutomationElementArray** | FindAllBuildCache out | get_Length, GetElement | iterate | 206529/≈206641 (`FUN_1400f7080`) |
| **UIA event handler** (object 63865-63869, vtables `0x14026b2c0`/`0x14026b280`; QI IID `DAT_140283bb0` = **{146C3C17-F12E-4E22-8C27-F894B9B79C69} = IID_IUIAutomationEventHandler** [decoded+recognized]; cppwinrt string at 63932) | handler ctor in request closure | `HandleAutomationEvent(el, ev)`: `if (ev==0x4E26 && cb) cb->v[2]()` | one-shot content-loaded reaction | `FUN_1400f7530` ≈206797 |
| conditions | control-view getter as find filter; `CreatePropertyCondition(0x7533 UIA_ControlType, VT_I4=0xc357/50007 ListItem)` for desktop icons | find filters | ≈206958; 207781-89 |
| event subscribed | **0x4E26 = UIA_AsyncContentLoadedEventId**, fg element, scope 7 | content-loaded subscription | 63883 (strings `"content loaded subscription"` 63811/63889) |

Other CoCreateInstance (not UIA): IVirtualDesktopManager 51867 (see window section).

**What Clairvoyance reads: only BoundingRectangle.** Property-ID scan of the whole decomp: `0x7531` (cache) + `0x7533` (desktop condition) only — no Name (0x7535), no Invoke/Text/LegacyIAccessible pattern IDs ⇒ hint boxes = element rects; labels are hint letters, not element names.
- `UiAutomationProvider::run` core = `FUN_1401f9070` (417333). `ForegroundTarget` built by `FUN_1401f8d10` (417142): `{hwnd, rect, dpiScale, valid}` from `GetForegroundWindow + IsWindowVisible + FUN_14003d330` (53718) `+ GetDpiForWindow`.
- if bbox flag `F+0x68` → `FUN_1400f7b90(F+0x50, fg)` → FindAllBuildCache(**Descendants**, control-view condition, cache{BoundingRect}) → `FUN_1400f7080` → `vector<RECT>` = **every control-view descendant of the foreground window (no type filter)**.
- `FUN_1401f8e20` (417206): inflate fg rect ±2 px, clip, build boxes (weight 1) → `HintProviderResult`; invalid → `EmptyResult` (ctor `FUN_1401f9460`, vtable `0x14026d728`).
- `ToResult(vector<Box>, ForegroundTarget)` RTTI 417567-72; placement math `FUN_1401f9470` (417611); fg-variant `FUN_1401f9c80` (418006).
- Provider chosen by FNV-hash of literal `"UiAutomationProvider"` in provider-name map (402079 / 342081); config key `ClairvoyanceMode` (300710); mode label `"Clairvoyance"` (349692); mode hooks `handleClairvoyanceMode` (342656, 402443).
- Docs cross-check: README:130 Clairvoyance = OS accessibility APIs, foreground-window-only; `[` switches mode.

### FailSafeUiAutomationManager / requestWindowControls

**Publics**: `requestWindowControls` = `FUN_1401f91a0` (417398; only site constructing closure vtable `0x140269088` at 417469, RTTI getter 63677 ⇒ identity certain); `cancelWindowControls` = `FUN_1401f93c0` (417525; cancel closure `0x140269028` at 417538, RTTI 63621). **Dispatch resolved by pointer scan (scout could not run the tool)**: both live in one .rdata vtable starting **0x14026d758** — layout `{dtor(1f92480→FUN_140122480? [0]), run=FUN_1401f9070, FUN_1401f9400, FUN_1401f9420, 672f0, 24520, 672f0, requestWindowControls(1f91a0), 1f92f0, cancelWindowControls(1f93c0), …}` — objects carrying it are built by factory `FUN_1401a19a0` (346532) **case 3** (object {vtable 0x14026d758, *(param+0xe78), …}, lines 346611-346620); factory call sites: `FUN_140177800` (312844, stores at tool+0xe8) and `FUN_1401e13d0` (397818, stores at +0x40). Slot-level consumer (call through +0x38/+0x50 on those objects) not pinpointed [GAP].

**Semantics** (pseudocode, scout-decoded):
```
// F = inner manager { UIA*, taskbar/desktop/bbox retriever triples (flags +0x28/+0x48/+0x68),
//   ticket counter +0x70 (=1), current ticket +0x78, request state +0x80..+0x98,
//   handler token +0xa0/+0xa8, hidden window +0xb0 ("Neverclick UI Automation", 62866),
//   hwnd +0xc8, tid +0xd0 };  OUTER { F* +8, ForegroundTarget +0x18..0x38 }
u64 requestWindowControls(OUTER, HWND /*unused*/, HWND notify, UINT msg)  // FUN_1401f91a0
  snapshot = CaptureForegroundTarget()                 // FUN_1401f8d10
  ticket = fetch_add(F.ticketCounter)
  if !snapshot.valid: PostMessage(notify, msg, heap{ticket, empty rects}); return ticket  // FAILSAFE path
  F.currentTicket = ticket
  enqueue(F.window, closure)                           // vtable 0x140269088
closure():                                             // FUN_1400480f0
  if F.currentTicket != ticket: return                 // superseded
  F.state = {ticket, watchHwnd=fg, notify, msg}
  if !F.bboxReady(+0x68): Deliver(); cancel; return    // UIA-down → still delivers (empty) — the "failsafe"
  el = uia.ElementFromHandle(watchHwnd); handler = {cb = nested{ticket}}
  uia.AddAutomationEventHandler(0x4E26 /*AsyncContentLoaded*/, el, scope=7, cache, handler)
  F.token = {uia, el, handler}; Deliver()              // immediate payload, success or failure
Deliver():                                             // FUN_140047cb0
  rects = bboxReady ? FUN_1400f7b90(F.bbox, watchHwnd) : {}
  PostMessage(notify, msg, heap{ticket, rects})        // fail → free
handler: ev==0x4E26 → cb()                             // FUN_1400f7530 ≈206797
nested():  if tokenPresent && state.ticket==ticket: Deliver(); cancel()   // ONE-SHOT  FUN_140048820 ≈64086
cancelWindowControls(): F.currentTicket=0; enqueue(closure 0x140269028)    // FUN_1401f93c0
closure(): if tokenPresent: RemoveAutomationEventHandler(0x4e26, el, h); free; clear  // FUN_140048070/140047ed0
```
- **There is no timeout**: the `unsigned` 3rd argument is the **window message id** used in both `PostMessageW` sites (417398-path and `FUN_140047cb0` 63405). No timer anywhere in the path. Anchor's "timeout" reading disproven.
- "FailSafe" = guaranteed delivery even when the *Bounding Box Retriever for Window Controls* failed to init (`"Failed to create Bounding Box Retriever for Window Controls:"`, ≈63041) or no foreground window (empty rect payload).
- **No titlebar-Button element targeting**: retriever applies no control-type filter (cache = BoundingRectangle only); no Name/Invoke/Text usage exists. Window-control actions (`Minimize Window`, `MinimizeWindow`, `CloseWindow`, `MinimizeOthers`, `ToggleMaximize`) use plain Win32 (e.g. `ShowWindow(hWnd, 6 /*SW_MINIMIZE*/)` ≈391917 next to `MinimizeOthers.execute` 391970). First HWND arg unused in the body (fg window watched instead) [open].
- dtor `FUN_140047ac0` (63309) marshals to the window thread via `SendMessageW(F+0xc8, 0x401, 0, &exc)` when caller tid ≠ `F+0xd0`.

### Elevation / UIPI

**Embedded manifest of neverclick.exe** (re-extracted verbatim from the exe by the parent; matches scout's dump):
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0"><trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges><requestedExecutionLevel level="asInvoker" uiAccess="true"></requestedExecutionLevel></requestedPrivileges></security><application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings><dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">True/PM</dpiAware></windowsSettings></application></assembly>
```
- `asInvoker` + **`uiAccess="true"`** + `dpiAware True/PM`. Repo-wide binary scan: **0** occurrences of `requireAdministrator`, **0** of `highestAvailable`; single `uiAccess="true"` occurrence (file offset 0x44b05b).
- Installer manifest (`installer/pe-sections/.rsrc/1033/MANIFEST/1`): `level="asInvoker" uiAccess="false"` — Inno loader itself has no uiAccess.
- **No runtime elevation machinery**: no `IsUserAnAdmin`, `TokenElevation`, `GetTokenInformation`, `ChangeWindowMessageFilter(_Ex)` imports. `ShellExecuteExW` used only with `lpVerb=L"runas"` for launching *user-chosen target apps* (≈359819 near `OpenApplication.execute`; error `"This application cannot be launched as Administrator."`; generic verb helper 409243).
- **UIPI story** = uiAccess + Program Files + Authenticode signature (standard accessibility-tool chain), no code trick. README:208 verbatim: *"Neverclick installs to Program Files because Windows requires that for it to register as an accessibility tool. This is what lets it perform mouse actions on apps running as administrator."* Signature presence itself not verified here [open].

### Icon refresh ("icons" = cached UIA bounding rects, not bitmaps)

```
Taskbar: FUN_1400330b0 (44725) SetWinEventHook(0x8000..0x800b, cb=FUN_1400334c0, flags=2)
   (globals: mainHwnd 44853, msg 0x508 44854); cb (44938) accepts 0x8000-0x8004 (+0x800b iff idObject==0),
   GetAncestor(GA_ROOT) class ∈ {Shell_TrayWnd, Shell_SecondaryTrayWnd} → PostMessage(main, 0x508) ≈45046
Desktop: FUN_1400336a0 (45052) SHGetSpecialFolderLocation(CSIDL_DESKTOP) then
   Ordinal_2(main, 0x8003, 0x7fffffff, 0x509) register shell-change ("Failed to register shell change notification."
   ≈45160; [INFERENCE: behavior = SHChangeNotifyRegister; DLL unidentified])
Startup: FUN_1400cdd80 (172586) → FUN_140041420/1400416a0 (172834-172857)
VisionProvider: FUN_1401f7f60 (416322) → FUN_140041420 if flag (416339)
wndproc: msg 0x508 → FUN_1400416a0 = UiAutomationManager::refreshTaskbarIcons (84662)
         msg 0x509 → FUN_140041420 = refreshDesktopIcons + SHChangeNotification_Locate(Ordinal_644)/HandleFree(Ordinal_645) (84770-84775)
refreshTaskbarIcons FUN_1400416a0 (57541): coalescing pending flag (+0x162) + Concurrency task
   (closure 0x140268e40, future +0x178); body FUN_140041da0 (57936): enumerate taskbar windows
   ("Failed to find any taskbar windows.") → per hwnd TaskbarIconRetriever FUN_1400f7df0 →
   FindAllBuildCache(Descendants) FUN_1400f8330 → rects cached under mutex +0x90
refreshDesktopIcons FUN_140041420 (57386): pending +0x160, future +0x168; body FUN_1400418a0 (57655):
   EnumChildWindows(desktop) FUN_140039020 (49839) for class SysListView32 + name FolderView
   ("Failed to find the desktop icons window.") → if hidden: clear cache; else retriever FUN_1400f84a0/
   FUN_1400f8b00 = FindAllBuildCache(Children, ControlType==ListItem 50007) → cache +0xe0
```
Purpose: keep taskbar-button / desktop-icon geometry fresh as click/hint targets. Triggers are window-activation WinEvents (taskbar) and shell item-change notifications (desktop); coalesced, async, mutex-guarded.

---

## Mouse & scroll injection

All mouse/keyboard/wheel injection goes through **`SendInput`** — exactly 5 sites (see Summary). No `mouse_event`; single `SetCursorPos` (window-warp helper `FUN_1401ea8e0` 404979/405000: only when the cursor is outside the foreground window frame → `SetCursorPos(left+(right−left)·fx, top+(bottom−top)·fy)`; callers = CycleWindows/SearchForWindow/PreviousWindow focus flows 373189/373436/373521/373757/381187…).

### INPUT construction sites

| line (FUN) | what | INPUT array | extras |
|---|---|---|---|
| 47911 (`FUN_140036950`) | keyboard INPUT builder `(buf, vk, up, extraInfo)` | 1 keyboard: `type=1, wVk=vk, wScan=MapVirtualKeyExW(vk, layout), dwFlags=(vk∈extended-set@DAT_1402ded68 ? KEYEVENTF_EXTENDED_KEY : 0) \| (up?2:0)` | extra = arg (0x147d in app paths) |
| 48044 (`FUN_140036bf0`) | key-combo → `vector<INPUT>` | N keyboard, `dwExtraInfo=0x147d` (48100/48124/48162/48186) | |
| **48199 (`FUN_140036f50`)** | **modifier-neutralized batch send** | if no held modifier: payload as-is; else `[Ctrl↓ Ctrl↑ if Alt/Win held] [each held modifier ↑] [payload] [each held modifier ↓ reversed]` (VK checks 0xa4/0xa5/0x5b/0x5c, 48280-48446) — one SendInput @ **48378** (err `"Failed to send input payload."`) or **48520** (err `"Failed to send the modifier-neutralized input."`) | so a physically-held Ctrl/Shift never alters injected combos/wheel |
| 343587/343635/343683 (`FUN_14019df90/e030/e0d0`) | **left/right/middle click** | 2× mouse: flags `0x2/0x4` (L↓↑), `0x8/0x10` (R↓↑), `0x20/0x40` (M↓↑); dx=dy=mouseData=0, time=0, **extra=0** | |
| 343731/343804 (`FUN_14019e170/e270`) | **double / triple click** | 4× / 6× `0x2,0x4` repeat, ONE vector | no SetDoubleClickTime machinery — literal vectors |
| 343901 (`FUN_14019e3e0`) | mouse-action enum → strategy vtable (6 cases; else throw `"Mouse action not recognized."`); invoked in build() @345991 | | case↔builder mapping partly unresolved |
| 344888/344953 (`FUN_14019f5c0/6e0`) | modifier down/up vectors `{ctrl,shift,alt}` → VK 0x11/0x10/0x12, extra=0x147d (344916-344938 / 344981-345003); **up-vector reversed before append** (release order alt,shift,ctrl) | | |
| **409660 (`FUN_1401f0150`)** | **absolute move** | 1×: `dx=(int)(65535.0/(SM_CXVIRTUALSCREEN−1)·(x−SM_XVIRTUALSCREEN))`, dy likewise; `dwFlags=0xC001` (**MOVE\|ABSOLUTE\|VIRTUALDESK**); extra=0; metrics via `GetSystemMetrics(0x4c..0x4f)`; err `"Failed to get virtual screen dimensions from system metrics."` | **(int) truncation, no +0.5**; `dim−1` divisor so max maps to 65535 |
| 409853 (`FUN_1401f04b0`) | wheel INPUT `(dir, amount)` | 1×: `mouseData=±0x78·amount` (**120=WHEEL_DELTA**), `dwFlags=0x800 WHEEL` (dir0 +, dir1 −) or `0x1000 HWHEEL` (dir2 −, dir3 +); callers set extra=0x147d | `amount` = configured lines-per-event |
| 409908 (`FUN_1401f0580`) | direct single wheel send (extra=0x147d @409926) | | |
| 331588/331530 (`FUN_14018e5d0/e530`) | sticky-click DOWN/UP single INPUTs (flags 2/4) | | |
| 369984/370066 (`FUN_1401be8a0/e9b0`) | ClickOnWindow Lift(4)/Hold(2) single INPUTs | | enqueued as a pair — never unpaired (no drag) |
| 409420/409498 (`FUN_1401efdd0/eff30`) | SendInput wrappers: `SendInput(1,…,0x28)` @409453 (err `"Failed to perform mouse operation for {:#04x}."`), `SendInput(count,…,0x28)` @409522 (err `"Failed to perform mouse operations."`) | | |

**dwExtraInfo policy**: keyboard + wheel = **0x147d**; mouse move + button = **0** (409747 & builders). The LL hook filters self-injected *keyboard* by marker (line 30360); mouse events never re-enter the keyboard hook.

### Execution pipeline (EventBuilder → queue)

```
EventBuilder::build(AppContext, vector<TargetWithKey>)   // FUN_1401a0110, line 345442
  origin = GetCursorPos()                                // 345699 — ReturnToOrigin capture
  per target (stride 0x58):
    move  = FUN_1401f0150(pt)          // absolute INPUT (extra=0)
    modDn = FUN_14019f5c0(mods)        // Ctrl/Shift/Alt downs (extra=0x147d)
    click = strategy->build()          // vtable call 345991 → e.g. [L↓,L↑]
    modUp = reverse(FUN_14019f6e0(mods))
    vec   = move ++ modDn ++ click ++ modUp               // 346001-346060
    wrap: ONE batched closure {0x14026d458, vector} (346072, MouseOperations)
          or per-INPUT closures {0x14026d488, INPUT} (345894, MouseOperationsWithoutBatching)
    out.push((fn, delay))             // delay 0 for first target else target+0x2b
FUN_14019f8f0(queue, pairs) @345059 → FUN_140145270(queue@ctx+0x1018, evt, countdown)
                                     // err "Countdown value cannot be negative."
pump FUN_140145340/140145390 (272145/272160): countdown → invoke vtbl+0x10, then +0x8
```
- `MouseOperations` op = `FUN_1401e7c90` (402855) → **one SendInput for the whole vector**; `MouseOperationsWithoutBatching` op = `FUN_1401e7bc0` (402778) → **one SendInput(1) per INPUT per queue tick**. Both return "done"=1. Sequencing = queue countdown only.
- **Ctrl+click** = `[abs-move] [VK_CONTROL↓] [L↓,L↑] [VK_CONTROL↑]` sent batched or per-INPUT — one-shot modifier wrap; same pattern for `optional<Key>` variants (`build(AppContext,Point,bool,optional<Key>)` RTTI 344455+, captured at closures 344461+).

### ClickOnWindow::execute (`FUN_1401be1e0`, trace 369735)

```
hwnd = GetForegroundWindow(); none → toast "No foreground window detected."      # 369725
frame = FUN_14003d330(hwnd); fail → log "…Failed to get window frame. {}"        # 369743-369790
target = frame.left + width·fracX(this+8), frame.top + height·fracY(this+0xc)    # 369811-13
enqueue (countdown 1 each): {MoveMouse,target} → {left-click anim @ctx+2000} →
        {Hold: INPUT flags=2, SendInput(1)} → {Lift: INPUT flags=4, SendInput(1)}  # 369818-369843
```
⇒ click = **move, then down and up as two separate SendInput(1) at least one queue tick apart** (never one batch).

### Scroll (`FUN_1401bcfd0` = `Scroll::execute`, RTTI 369278)

```
dir=this+8 (0..3), amount=this+0xc, fracX/Y=this+0x10/0x14,
moveToWindow=*(this+0x18), flagC=*(this+0x1c)                                 # 368793/368806
if !moveToWindow:
    flagC==0 → wheel=FUN_1401f04b0(dir,amount); extra=0x147d (368840);
               copy → FUN_140036f50 (neutralized, ONE SendInput)
    else     → FUN_1401f0580 (raw SendInput(1))
else:  # MoveMouseToWindow
    frame/pos fetch; errors "Scroll.MoveMouseToWindow: Failed to get window frame. {}" (368876)
      / "…Failed to get mouse position. {}" (368908)
    if cursor outside frame: target=(left+w·fracX, top+h·fracY) (368966-70);
        enqueue MoveMouse{target} (368969) + disappear-anim at old pos (FUN_140148df0, 368971)
enqueue scroll event {0x14026cdc8, flagC, dir, amount}                        # 368996-369002
   pump → FUN_1401bd980: flagC==0 → neutralized batch (extra 0x147d @369319);
                         flagC≠0 → raw single SendInput(1)
```
- **Wheel delta = amount×120** (WHEEL_DELTA); dir0/1 = vertical ±, dir2/3 = horizontal ∓ (409864-409901).
- Warp-to-window happens **only when the cursor is outside the fg window frame**.
- Neutralization releases held modifiers, Ctrl-taps if Alt/Win held, sends wheel, restores modifiers — all inside ONE SendInput (48520). Meaning of `flagC` [UNRESOLVED].

### MoveMouse action (`FUN_1401b7d40`, trace 364845)

`dir=this+8 (0..3)`, `delta=this+0xc`; `pos=GetCursorPos()`; dir0..3 → `FUN_1401f03c0(pos.x∓/±delta, …)` (364871/364910/364949/364989). Mechanism = absolute virtual-screen move (`0xC001`), never relative dx/dy. Event form `{0x14026d428, Point}` ctor `FUN_1401e7d40` (402920) → same executor → ONE SendInput.

### MouseSlot (`FUN_1401bad60`, traces 367271/367410)

Slots 1-8 × {x,y} + valid flag, stored at `DAT_1402deca0` (absolute) / `DAT_1402dec88` (relative-window); invalid slot → toast `"Please choose a valid slot number."` (367168). op=clear / save-or-restore toggle: empty → save (toast `"Saved mouse position to slot {}"`); filled → restore via `FUN_1401e78f0` (move + 3 animations, 402621-402723). Relative mode stores a **window-frame-normalized fraction** (needs foreign foreground window; restore = lerp of frame, 367585) [save tail 367484-367604 partial].

### WiggleMouse (`FUN_1401bfe70`, trace 371183)

mode0: at cursor; mode1: at window fraction (default 0.5×/0.3×). `FUN_1401bf980` (370892): 10 iterations of (x−20,y)/(x+20,y) → 20 MoveMouse events, countdown=1 each (371047-371064).

### ReturnToOrigin semantics

- A **saved absolute cursor Point**, captured by `GetCursorPos` at dispatch/build start (dispatch ≈`FUN_14018a670` call at 328468; EventBuilder at 345699) — *before* the cursor is moved to the hint.
- After click events, a queued absolute-move event replays the saved point: inner lambda body **`FUN_14018e440`** (331441) → `FUN_1401f03c0` → SendInput. `dispatchStickyClick` order (328468-328524): [move to target] → [DOWN @delay d] → [UP @delay d] → [origin-move @delay d], `d = 2−(flag@+0x3c!=0)` ticks; RTTI-labeled closures at 331435/344369 (`{0x14026c948, point}` ctor `FUN_14019ed10` 344375).
- Distinct from **`final_mouse_position::ToEvent(Offset)`** (`FUN_1401e77a0` 402527): runtime `GetCursorPos` + offset → absolute move (relative-by-offset evaluated at run time; err `"Failed to get mouse position: {}"` 402540).

### Animations side-channel

`AnimationEventService` at `AppContext+2000`; `addMouseMoveAnimation` {0x14026ba48} (body `FUN_14014eee0` 279828), `addMouseDisappearAnimation` {0x14026ba78} (`FUN_14014ef30`), `addLeftClickAnimation` {0x14026baa8} (`FUN_14014ef80`) — enqueue delay-0 events on the **same** animation queue (`ctx+0x1018`). Trigger points: MouseSlot restore/`FUN_1401e78f0` (402685-402723), ClickOnWindow step 2 (369824), Scroll warp (368971), sticky dispatch (331482), EventBuilder lambdas (344461-344517; hover anim gated by `*(ctx+0x42)`, floats 15/90/30 → `FUN_140148a50/140148b20`).

### Drag / double-click conclusions

- **Drag: absent** — no `Drag` strings, no down+move+up chain; Hold/Lift always paired (369833-369843) ⇒ README "coming soon" confirmed.
- **Double/triple click** = fixed 4/6-INPUT vectors, not double-click timing.

---

## Gaps (consolidated, unresolved after all passes)

**Input/hotkey layer**
1. Textual caller of `ActiveToolManager::handleKeyReleaseTrap` not found (bound via closure/event table).
2. Writer of the `HotkeyManager+0x268` message-sink pointer not located (readers: wndproc prefilter 84860, WM_PAINT 84898).
3. Population source of ToolInputHookCallback's passthrough set (`this+0x18`) vs captured set (`this+0x10`) — trap-member ownership proven, exact fills not pinned.
4. `HotkeyEntry` +0x1c flag and +0x28 mode: exact JSON field names unknown (mode semantics proven: 0=tool, 1=action, −1=invalid).
5. Full compiled-in default-keybind table (FUN_140175660): Shift+WASD/QE/ZFR + Esc decoded; remaining groups (0xde/0x15/0x16/0x17, `{3,0,D/M/P}`, 0xbc/0xbe/0xbf entries) need struct types.

**Mouse/animation layer**
6. Queue pump driver (who ticks `FUN_140145340/140145390`) and whether pair-delay ints are ticks or ms.
7. Split-vs-batched branch condition in EventBuilder::build (345894 vs 346072); possibly config `enableEventBatching` (+0x3c) [INFER].
8. Mouse-action strategy enum→builder mapping (6 cases vs 5 builders, FUN_14019e3e0).
9. Scroll `this+0x1c` flag (neutralized vs raw send) config provenance; wheel `amount` schema source.
10. MouseSlot.DoSaveRelative store tail (367484-367604) unread; extended-key set @DAT_1402ded68 contents.

**Window/UIA layer**
11. Physical-key→enum mapping for window actions beyond compiled defaults (runtime bindings authoritative; `/shared-keybinds/defaults` serves them).
12. Consumer/slot-call site of FailSafe `requestWindowControls` vtable (`0x14026d758`, factory case3 FUN_1401a19a0@346611); the window receiving `{ticket, rect-vector}`; first-HWND param unused.
13. IID name of `{30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}` (CoCreate with CLSID_CUIAutomation); IVirtualDesktopManager methods; TileWindows style numeric mapping; `updateAnimationsEnabled` body.
14. Authenticode signature + companion-binary manifests (neverclick-ui.exe etc.) unverified (payload unpack pending Inno 6.7 support).

**Chrome/config layer**
15. WAV301/302 playback backend (no waveOut/XAudio/DirectSound/MCI/MediaFoundation surfaces; `InitAudioAsync` body not located) and success-vs-error mapping.
16. `enableNotifications` (+0x44) consumption site (no balloon/toast APIs anywhere; only NIM_ADD/MODIFY/DELETE exist).
17. Update version-compare implementation; result UI surface; `launchAtStartup` vs `runOnStartup` key relation.
18. `enableAnimations` (+0x41) / `enableMouseAnimations` (+0x42) consumption sites (window animations gated at `services+0x43` ≈ `enableWindowAnimations`, near-certain).
19. Config base directory value (joined at `core+800`; `SHGetKnownFolderPath` helpers exist, exact folder id not pinned).

---

## Spec-ready statements (behavioral contract)

1. **Keyboard hook**: install exactly one global `WH_KEYBOARD_LL` hook on a dedicated thread with its own message loop; hook/unhook/isHooked marshal to that thread via `SendMessage(hwnd, WM_USER+1, 0, closure)`, exceptions marshalled back via exception_ptr. Callback returns 1 to swallow, else `CallNextHookEx`.
2. **Event tagging**: every injected keyboard/wheel INPUT carries `dwExtraInfo = 0x147d`; mouse move/button INPUTs carry 0. The hook ignores (never matches, never replays) events whose `dwExtraInfo` equals the marker.
3. **Win-chord suppression**: when a hotkey containing Win was swallowed and the user releases Win with no Ctrl/Alt/Shift held, synthesize `[LCONTROL down, LCONTROL up, Win up]` in one `SendInput(3)` and swallow the Win-up; otherwise Start-menu suppression fails.
4. **Hotkey model**: entries = `{ctrlReq, altReq, shiftReq, winReq ∈ {0 none,1 left,2 right,3 either}, vk}` + `enabled` + mode(tool|action). Matching = pressed vk equals chord vk AND a live 8-bit `GetAsyncKeyState` snapshot of {L/R Ctrl, Alt, Shift, Win} satisfies all four reqs; modifier keys never trigger chords.
5. **Three hotkey states** (active/suspended/sleeping): only active-state hooks match all enabled entries; suspended hooks only the `SuspendNeverclick` chords; sleeping only `SleepNeverclick`. Toggles rebuild the hook set atomically (unhook old id, hook new id) on the hook thread.
6. **Chord dispatch**: matched chord → `PostMessage(mainWnd, 0x501, heap{chord20}, 0x147d)`; wndproc re-matches all entries and either activates a tool (mode 0) or calls `action->execute(AppContext)` directly (mode 1); wParam freed on every path.
7. **Tool input capture**: while a tool is armed, all non-modifier key down/up are swallowed; each down posts `0x502 {modifierSnapshot8, vk}`; modifiers always reach the focused app; captured/passthrough sets pair every down with its up.
8. **Release trap**: on tool close, capture the currently-down keys, swallow their key-ups, fire the deferred close when all released or after ~1.001 s.
9. **Overlay lifecycle**: arm → `ShowWindow(SW_SHOWNA)` both overlay HWNDs + `PostMessage(overlay, 0x50c)`; close → deactivate callback, `SW_HIDE`, `0x50c`; same-chord re-press toggles (settle path closes).
10. **Mouse move**: single INPUT `MOUSEEVENTF_MOVE|ABSOLUTE|VIRTUALDESK` (0xC001), coordinates `(int)(65535/(dim−1)·(coord−origin))` over the virtual screen (truncating).
11. **Clicks**: fixed INPUT vectors (left `2,4`; right `8,10`; middle `20,40`; double `2,4,2,4`…); hint clicks execute as `[move][mod-down][click][mod-up(reversed)]` batched in one SendInput or per-INPUT SendInputs, sequenced by a countdown queue; modifier wraps use vk 0x11/0x10/0x12 with `dwExtraInfo 0x147d`.
12. **Wheel**: `MOUSEEVENTF_WHEEL/HWHEEL`, `mouseData = ±120·lines`, injected via modifier-neutralizing batch (release held modifiers, Ctrl-tap if Alt/Win held, wheel, re-press modifiers) so held modifiers never alter injected scrolling; warp cursor to the window fraction only if outside the fg window frame.
13. **ReturnToOrigin**: capture cursor position (GetCursorPos) at dispatch; after click events, queue an absolute-move replay of the saved point (sticky-click delays `d = 2−flag` ticks).
14. **Window actions**: FocusWindow geometric half-plane picker (15 % perpendicular margin, min-distance tie-break); CycleWindows z-order Forward (send old to bottom) vs Backward (no reorder); monitor moves require exact edge abutment (no wrap); snap = single SetWindowPos to union(old,new) with `NOZORDER|NOOWNERZORDER`; all moves DPI-aware; animations = queued events on `AnimationQueue` consumed by the AnimationWindow thread, gated by `enableWindowAnimations`.
15. **Virtual desktops**: switch/create/close = injected `Ctrl+Win+←/→/D/F4`; move-to-desktop = IVirtualDesktopManager COM.
16. **UIA**: pure client; one `CoCreateInstance(CLSID_CUIAutomation)`; caches only BoundingRectangle (+ControlType==ListItem for desktop icons); Clairvoyance = FindAll(control-view descendants of fg window) rect boxes; FailSafe = one-shot `UIA_AsyncContentLoaded` subscription delivering `{ticket, rects}` via a caller-chosen window message, with guaranteed immediate (possibly empty) first delivery; no UIA provider exposure (no WM_GETOBJECT/IRawElementProvider).
17. **Elevation**: manifest `asInvoker` + `uiAccess="true"` + per-monitor DPI; Program Files + Authenticode = UIPI bypass; no runtime elevation APIs.
18. **Tray**: uCallbackMessage 0x401; menu Open(default)/Suspend-Resume/Sleep-Wake/Exit with state-dependent labels; sleep/wake plays `%WINDIR%\Media\Speech {Sleep,On}.wav` rate-limited; exit = NIM_DELETE + PostQuitMessage; TaskbarCreated re-adds.
19. **Config**: `app-config.json` + `hotkey-config.json.gz` (schema-versioned) beside a base dir; live updates via REST `0.0.0.0:7340` (`/hotkeys*`, `/shared-keybinds*`, `/app-config*`, `/update*`, `/version`, `/nvidia-power-mode`); any hotkey change deactivates the active tool when its binding is touched, then rebuilds hooks; startup = startup-folder `.lnk` toggle; updates = hourly WinHTTP GET of `https://www.neverclick.com/api/version`, download → spawn updater silently.
