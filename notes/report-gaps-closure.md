# Neverclick 0.4.1 — Gap closure report (14 remaining behavioural gaps)

> **Artifact availability.** `ghidra/neverclick-decomp.c`, the extracted UI bundle and the original binaries
> have been removed from this tree. Line citations (`decomp:line`, `part_NN:line`) refer to those removed
> dumps and cannot be re-opened; the analysis and reconstructed pseudocode remain authoritative.

Scope: close the 14 gaps listed by the parent task so that no undefined semantics remain for a
faithful reimplementation. Every claim is anchored to `ghidra/neverclick-decomp.c`
(`neverclick.exe`, image base `0x140000000`, function headers `// ----- <addr> : <name> -----`),
to the shipped UI bundle `extracted/ui-assets/assets/index-CG8hdpTV.js`, or to PE imports of
`extracted/app/neverclick.exe`. Line numbers are decomp line numbers unless prefixed `0x`
(addresses). `[V]` = verified in code/PE/strings; `[I]` = inferred.

Known-good layout of the `AppConfig` object (ctor `FUN_140057bd0 @ 0x140057bd0`,
decomp:76376–76450) used throughout:

| off | type | key | default (ctor) |
|---|---|---|---|
| +0x3c | u8 | enableEventBatching | 1 (decomp:76389 `0x10101` → +0x3c,+0x3d,+0x3e = 1,1,1) |
| +0x3e | u8 | enableVisibilityToScreenCapture | 1 |
| +0x40 | u8 | (unnamed) | 1 |
| +0x41 | u8 | enableAnimations | 1 (decomp:76390 `0x1010101` @+0x40..0x43) |
| +0x42 | u8 | enableMouseAnimations | 1 |
| +0x43 | u8 | enableWindowAnimations | 1 |
| +0x44 | u8 | enableNotifications | 1 (decomp:76391 `*(u16*)(+0x44)=1`) |
| +0x45 | u8 | enableUppercaseHints | 0 |
| +0x48 | i32 | hintFontSize | **16** (decomp:76392 `*(u32*)(cfg+0x48)=0x10`) |
| +0x50 | string | hintFontName | **"Inter"** (decomp:76397) |
| +0x150 | i32 | keyboardLayoutPolicy | 0 = Auto (decomp:76420) |
| +0x154 | i32 | _pk_strategy_ (unnamed) | 1 |
| +0x158 | u8 | enableProgressiveHints | 0 = false (decomp:76421 `*(u8*)(cfg+0x158)=0`) |
| +0x15c | i32 | hintPlacement | 0 = Centered (decomp:76422) |
| +0x160 | i32 | fovMode | 2 = AllMonitors (decomp:76423) |
| +0x164 | i32 | graphicsPreferencePolicy | 0 = LetNeverclickDecide |
| +0x168 | i32 | appBarTheme | 0 = Graphite |
| +0x16c | u8 | compactAppBar | 0 |
| +0x170 | i32 | (unnamed) | 0 |
| +0x174 | u8 | removeHallucinations | 1 (decomp:76428) |

(The same object also owns the overlay window pointers at `+0x7c0`, `+0x7c8`, `+0x7e8`, `+0x7f8`,
the label pipelines at `+0xc38`/`+0xcb0`, the alphabet at `+0xf08` and the hint state at `+0xf10`;
it is reached as `config = *(AppContext + 0x248)` — deref sites e.g. decomp:172857, 173062.)

---

## 1. `enableProgressiveHints` (config+0x158, mirror +0xd7d)

**Finding.** `enableProgressiveHints` is a *rendering* flag, not a detection flag:
- Storage: byte `config+0x158`; duplicate byte `config+0xd7d` is kept in sync by the same writer.
- Writer `FUN_1400f0b00 @ 0x1400f0b00` (decomp:201867): `*(u8*)(cfg+0x158)=v; *(u8*)(cfg+0xd7d)=v;`
  then `RedrawWindow(overlayHwnd, NULL, NULL, RDW_INVALIDATE|RDW_UPDATENOW (0x101))`
  (decomp:201888–201895). It does **not** re-run detection/capture — the effect is a pure repaint.
- Default: **false** (ctor decomp:76421).
- Semantics (authoritative, from the shipped settings UI): *“Only show the first letter of long
  hints. Remaining letters are revealed as you type.”* (tag “Experimental”).
  → With the flag ON, a hint whose label is multi-character is **displayed truncated to its first
  character** while no prefix has been typed; every time the user types a character that keeps the
  hint a candidate, the next character of its label becomes visible (prefix consumption).
- Feasibility mechanism confirmed in the core: the label table is pre-generated for **all lengths
  1..min(3, depth)** — `FUN_1400b3d30 @ 0x1400b3d30` (decomp:150864–151080) loops `n = 1..uVar35`
  (`uVar35 = min(3, depth(budget))`), appends `min(|A|^n, budget)` combos per length, so the 1-char
  and 2-char prefixes of every 3-char label are *also* layout-cached keys. That is exactly what a
  progressive display needs; `enableUppercaseHints` is the separate `param_9 → towupper`
  post-processing (decomp:151074–151078).
- The only runtime *session* switch affecting label stability during typing is
  `session+0x154` (byte, session ctor default 0, `FUN_140177560 @ 0x140177560`, decomp:312774),
  read in the hint-layout-request handler `FUN_140177d70 @ 0x140177d70` on window-message **0x510**
  (decomp:313501–313560):
  * `session+0x154 == 0` ⇒ always accept the provider's new target set and re-run the full
    re-assignment/layout pass `FUN_1401f26a0(session+0xa8, …, session+0x150, …)`;
  * `session+0x154 != 0` ⇒ accept the new layout only when the current layout is empty
    (`state.depth < 1` **and** zero slots), otherwise **keep the existing labels** (no re-assign).
  This is the "labels regenerate while typing vs stay stable" policy the task refers to.

**Evidence.** ctor decomp:76421; setter decomp:201878–201895; serializer read
`FUN_1400a6e30 @ 0x1400a6e30` decomp:141433–141439 (reads `cfg+0x158`);
settings-copy `FUN_1400a6690 @ 0x1400a6690` decomp:140546 (`packed+0xac ← cfg+0x158`), stored by
`FUN_1400a6370 @ 0x1400a6370` at `packed_settings = obj+0x178` (decomp:140415);
label generator decomp:151039–151065; 0x510 handler decomp:313501–313560; UI string in
`extracted/ui-assets/assets/index-CG8hdpTV.js` (`title:"Progressive Hints", desc:"Only show the
first letter of long hints. Remaining letters are revealed as you type."`).
Two co-existing label pipelines (built by `FUN_1400cc820 @ 0x1400cc820` and again by
`FUN_1400ce300 @ 0x1400ce300`, and once at init decomp:81263/81288) prove the multi-length table:
* `pipeline A` → `config+0xc38`: `budget = 1000`, `font = (float)(i32)(config+0x48)` (decomp:173060–173067
  and 172879–172886 pattern: `*(u64*)(shadow+0x30)=1000; *(float*)(shadow+0x28)=(float)iVar8;`).
* `pipeline B` → `config+0xcb0`: `budget = 0`, `font = 0x42100000 = 36.0f` (decomp:173074–173081).
  With `budget == 0` `FUN_1400b3d30` skips the generation loop entirely (decomp:151036 `if (param_7 != 0)`),
  so **B is an empty-label "on-demand / large font" pipeline** (the Hint Painter has an explicit
  cache-miss fallback, `[Hint Painter] Unicode cache miss for {}/{} hint(s).`).

**Confidence.** Storage/default/writer/readers/repaint `[V]`; label-table length 1..3 `[V]`;
`session+0x154` gate semantics `[V]`; the exact truncation/reveal code path: `[I]` — it is not
statically reachable from `config+0x158` (only the JSON serializer and the whole-object settings
copy read that byte; the packed copy at `+0x178+0xac` has no field-wise reader anywhere in the
decompilation). The `session+0x154` gate is therefore the *confirmed* label-stability switch,
while the (de)selection/relabel while typing is implemented in the overlay repaint path.

**If undeterminable — best default (implementable).** Implement exactly as the UI documents, with
the label table of §3.1/3.3 of `report-hints.md`:

```
renderLabel(hint):
    if not cfg.enableProgressiveHints:  draw(hint.fullLabel)
    elif typedPrefix is empty:          draw(firstChar(hint.fullLabel))      # 1 char only
    else:                               draw(suffix(hint.fullLabel, len(typedPrefix)))
                                        # already-typed chars consumed; next char is the cue

onKey(char c):                                   # window msg 0x502 handler family
    cand = { h in hints : upper(h.fullLabel) startsWith upper(typedPrefix + c) }
    if cand is empty:      ignore (do not extend prefix)
    typedPrefix += c
    if |cand| == 1 and cand[0].fullLabel == typedPrefix:
        executeClick(cand[0]); resetPrefix()      # label complete → click
    else:
        keepOnly(cand); typedPrefix = c           # relabel/redraw survivors
    if cfg.enableProgressiveHints: repaint()      # only 1 char visible per surviving hint
    else:                          repaintWithFullLabels()

onKey(Esc / UndoHintSelection): resetPrefix()     # Esc default-binds to UndoHintSelection (id 2)
if session+0x154 == 0: re-run full assignment on every 0x510 layout request
else:                  keep labels unless the current layout is empty
```

---

## 2. Hint label rendering defaults (`hintFontSize`, `hintFontName`)

**Finding.** The renderer reads `config+0x48` (i32) as the font size and `config+0x50`
(std::string) as the font name. Defaults from the ctor: **`hintFontSize = 16`**,
**`hintFontName = "Inter"`**.
The earlier “default 28 at config+0x48” inference was wrong (it came from the serializer's
fallback path, not the ctor). The shipped UI zod range is 8–24 (`hintFontSize`), consistent with 16.
A second, fixed 36.0 px font exists for the on-demand label pipeline `config+0xcb0` (§1) — that
36.0 is a constant, **not** `hintFontSize`; do not conflate the two.

**Evidence.** ctor `FUN_140057bd0` decomp:76392 (`*(u32*)(cfg+0x48) = 0x10`), decomp:76397
(`FUN_1400204c0(cfg+0x50,"Inter",5)`); serializer reads `cfg+0x48` for key `hintFontSize`
(decomp:141161–141166, `FUN_1400a9760(&x, param_2 + 0x48)`) and `cfg+0x50` for key `hintFontName`
(decomp:141168–141175); render pipeline reads `iVar3 = *(i32*)(config+0x48)` then
`local_1b0 = (float)iVar3` (decomp:172930, 173054) and the font-name string at `config+0x50`
(decomp:172931–172939: buffer base `config+0x50`, length at `+0x60`, capacity `+0x68`).
Bundled fonts present in `extracted/app/fonts/` (11 TTFs including Inter-Regular).

**Confidence.** `[V]`.

**If undeterminable.** N/A.

---

## 3. Audio backend, resource playback, `enableNotifications`

**Finding.**
1. **Init API = SDL2 (audio subsystem only) + CoInitializeEx.** `nvr::InitAudioAsync`
   (`FUN_1400bbe20 @ 0x1400bbe20`, decomp:157693–157790) returns
   `std::future<nvr::AudioInitResult>` and schedules the async body
   `FUN_1400bc110 @ 0x1400bc110` (decomp:157869–157945):
   ```
   CoInitializeEx(NULL, COINIT_APARTMENTTHREADED /*2*/)
   if (refcount DAT_1402dec00 == 0):
        if (SDL_Init(0x10 /*SDL_INIT_AUDIO*/) < 0) -> result = SDL_GetError()
        SDL_SetHintWithPriority("SDL_AUDIO_RESAMPLING_MODE","medium", SDL_HINT_OVERRIDE /*2*/)
        DAT_1402dec00++
   result = {status, ok};  teardown: if refcount->1: SDL_QuitSubSystem(0x10); CoUninitialize()
   ```
   It is started once at app init: `FUN_1400b9e60 @ 0x1400b9e60` (decomp:156038–156070) is called
   from `FUN_14005bea0` (decomp:80900) and awaits/stores the future.
   **There is no SDL audio *device***: the whole PE imports only `SDL_Init`, `SDL_GetError`,
   `SDL_QuitSubSystem`, `SDL_SetHintWithPriority` from `SDL2.dll` (verified via PE import table) —
   no `SDL_OpenAudioDevice`/`SDL_LoadWAV`/`SDL_QueueAudio`.
2. **Playback API = `PlaySoundA` (WINMM), one site only.** `FUN_14013d450 @ 0x14013d450`
   (decomp:265119–265230):
   ```
   ts = now_us();  if (now - last < *cooldown_secs * 1000000) return 0;   // rate limit (µs)
   last = ts;
   path = fmt("{}\\Media\\{}", GetWindowsDirectoryA(), name)
   PlaySoundA(path, NULL, 0x20003 /*SND_ASYNC|SND_NODEFAULT|SND_FILENAME*/)
   ```
   Sole caller = `SleepNeverclick.execute` (decomp:315147) with `name = "Speech Sleep.wav"`
   (decomp:315123) / `"Speech On.wav"` (decomp:315144). Suspend is silent.
   Cooldown object lives at `core+0x768`; interval = `*param_1` **seconds** (`*param_1 * 1000000` µs,
   decomp:265157). `WINMM.dll` imports exactly one function: `PlaySoundA`.
3. **Embedded WAV resources 301/302 are loaded but never played.** Resource type `L"WAV"`
   (`DAT_140283630`, length 3) with ids 301/302 (PE `.rsrc` named type `WAV`, verified earlier);
   loader `FUN_1400f6960 @ 0x1400f6960` → `FUN_1400f6810 @ 0x1400f6810`
   (`FindResourceW(GetModuleHandleW(0), MAKEINTRESOURCE(id), L"WAV")` + `LoadResource` +
   `SizeofResource` + `LockResource`, decomp:206061–206130). App init calls it twice
   (decomp:80935–80936: first id = `*(u32*)(cfg+0x94)`, second elided, = 301/302). The two buffers
   are moved into the audio-context object but **no code path passes them to any playback API**:
   there is no `PlaySoundA(.., SND_MEMORY)`, no `waveOut*`, no `XAudio2`, no DirectSound, no MCI, no
   MediaFoundation import anywhere in the PE. Consequence: **success/error/notification sounds are
   not implemented in 0.4.1**; only the Windows sleep/wake sounds are audible.
   *Note*: the WAV buffers' move targets are `FUN_14000b8e0` (24-byte vector move) into a struct; the
   struct is never played from. Treat 301/302 as vestigial in a reimplementation.
4. **`enableNotifications` (config+0x44, default 1)** is consumed by the *notification animation*
   builder `FUN_1401440f0 @ 0x1401440f0` (decomp:271168+):
   ```
   if (*(u8*)(param_1[2] + 0x44) == 0) return;          // notifications disabled
   build notification object {title=param_2, body=param_3}
   push into sink: FUN_14004c970(sink, obj)  ->  PostMessageW(hwnd, 0x401 /*anim/event msg*/, obj, 0)
   ```
   `"Failed to create notification animation: {}"` on failure. Callers include the startup
   notification (`"Neverclick Initialized Successfully"` / `"Ready for user input."`,
   decomp:84395–84398, gated additionally by `showStartupNotification`), and dozens of
   success/error/status sites. So `enableNotifications` gates an on-screen animated notification —
   **not** a sound.
5. `%WINDIR%\Media\Speech {Sleep,On}.wav` **is** used (see 2) and **is** rate-limited (see 2);
   confirmed.

**Evidence.** As above; SDL/WINMM import lists from the PE import directory
(`extracted/app/neverclick.exe`, `SDL2.dll` = {SDL_Init, SDL_GetError, SDL_QuitSubSystem,
SDL_SetHintWithPriority}, `WINMM.dll` = {PlaySoundA}); strings `SDL_AUDIO_RESAMPLING_MODE`,
`Speech Sleep.wav`, `Speech On.wav`, `Failed to create notification animation: {}`,
`Failed to initialize animation window.`.

**Confidence.** `[V]` for init API, playback site, resource loader, `enableNotifications` consumer,
import lists. `[V]` for “no playback path for 301/302” (exhaustive API/import check).

**If undeterminable.** If a reimplementation wants sounds, the original gives no mapping
(success vs error vs notification) — use this default: no sounds for success/error; play
`%WINDIR%\Media\Speech On.wav` on wake and `Speech Sleep.wav` on sleep, rate-limited to 1/s,
`PlaySoundA(SND_ASYNC|SND_NODEFAULT|SND_FILENAME)`; gate the on-screen notification animation on
`enableNotifications`.

---

## 4. Animation queue

**Finding.**
1. **Ticker.** There are *two* distinct queues; do not conflate them.
   * **Countdown delay-queue** `nvr::anim::AnimationQueue` — ring buffer
     `{base@+0x10, cap@+0x18, head@+0x20, count@+0x28}`, element stride **0x48**
     `{+0x00/+0x38 std::function<bool()>, +0x40 i32 countdown, +0x44 u8 run-immediately}`.
     It is driven by a **Win32 `WM_TIMER` with `wParam` id `0x504`** on the main window:
     wndproc `FUN_1400612c0 @ 0x1400612c0` (decomp:84480), `param_4 == 0x113` branch
     (timer ids `0x403/0x404/0x405/0x407/0x504`, decomp:84605–84630) → tick
     `FUN_140061d50 @ 0x140061d50` (decomp:84912–84973):
     ```
     queue = *(ctx+0x1108)  ; slot = back slot
     if (slot.runImmediately) slot.countdown = 0
     if (slot.countdown > 0) { slot.countdown -= 1; return }     // exactly one step per tick
     if (slot.fn()) FUN_140145390(queue)                          // done -> pop-front
     else { if (++DAT_1402e0310 > 500) FUN_140145390(queue); else /* stay */ }
     ```
     So the countdown unit is **ticks of that timer**, decremented by 1 per delivered tick.
   * **AnimationWindow renderer** — separate thread with its own WS_POPUP windows
     (`NeverclickAnimationWindow` / `NeverclickAnimationOverlay`) and its own GPU device;
     `nvr::AnimationWindow::threadMain` (RTTI `FUN_14004e0c0 @ 0x14004e0c0`, decomp:68692)
     runs `GetMessageW` + `PeekMessage` (handles `0x401/0x403/0x404`), computes
     `dt = min(elapsed, 0.1 s)` and ticks each animation object's `vtbl+8(dt)` (decomp:68390–68440),
     with `WaitForSingleObjectEx(handle, 1000, 0)` + `DwmFlush`, and a 10 fps fallback
     `SetTimer(hwnd, 1, 100, 0)` (decomp:66938). Objects are handed to it thread-safely by
     `FUN_14004c970 @ 0x14004c970` (`mov 0x18(%rcx),%rcx` then lock+emplace) — this is the call
     used by every `AnimationEventService::add*Animation` path
     (`FUN_14014eee0/FUN_14014ef30/FUN_14014ef80`) after the countdown tick fires.
2. **Timer object/interval.** `nvr::InitAnimationQueue(NeverWindow&)` → getter
   `FUN_1400ba990 @ 0x1400ba990`; construction `FUN_1400b35e0 @ 0x1400b35e0` builds
   `Timer{ vtbl@+0, hwnd=NeverWindow+0x20 @+8, id=0x504 @+0x10, interval=arg @+0x14, running@+0x18 }`.
   Start `FUN_140145020` = `PostMessageW(hwnd, 0x113, 0x504, 0)` + `SetTimer(hwnd, 0x504, interval, 0)`;
   `FUN_1401450a0` = `KillTimer`; `FUN_140145100` = setInterval; `FUN_1401451d0` = getInterval.
   The interval is a runtime value passed from the `NeverWindow` ctor `FUN_14005bea0`
   (disasm `mov 0xf8(%rbp),%r9d; call 0x1400b35e0`), not an immediate.
   **Best default = 1 ms/tick** (⇒ `eventDelay` = 10 ms default, 500-tick stuck guard ≈ 0.5 s).
   `[I]` for the interval value; `[V]` for "unit = ticks".
3. **Gates.**
   * `enableAnimations` (**config+0x41**) — master gate: the animation window/queue subsystem is
     created/updated only when set (gate in the state-update routine, decomp ~164976:
     `if (*(char*)(cfg+0x41) != 0) { … *(cfg+0xd28) vtable+0x38 … }`). Default **true**.
   * `enableMouseAnimations` (**config+0x42**) — per-lambda gate: when clear, the mouse-animation
     factory lambdas `destroy; return` instead of enqueueing. Suppresses mouse
     move / disappear / hover animations. Default **true**.
   * `enableWindowAnimations` (**config+0x43**) — gate `FUN_140148b80 @ 0x140148b80`
     (`if (*(char*)(cfg+0x43)==0) discard; else FUN_140148b20(...)`), also inlined in
     `InvokeWindowAnimation`, `FUN_1401ea430`, the window-move tool and several lambdas.
     Suppresses window focus / move / snap / glow animations. Default **true**.
   (All three defaults read from ctor `0x1010101` at `cfg+0x40..0x43`, decomp:76390.)

**Evidence.** decomp:84480, 84605–84630, 84912–84973, 272158 (`FUN_140145340` = clear, called by
`EventBuilder::build` at decomp 346534 just before enqueueing), 272178 (`FUN_140145390` = pop),
`FUN_140145270` (push), `FUN_1401451e0` (single push, delay=1), `FUN_14019f8f0` (batch push),
`FUN_1400b35e0`, `FUN_14004e0c0`, `FUN_14004c970`, 164976, 274975, gates at 344461 and
scratch-hints part_02/part_03 lambdas; RTTI
`nvr::anim::AnimationQueue`, `nvr::InitAnimationQueue(nvr::NeverWindow&)`,
`nvr::AnimationWindow::threadMain`, `nvr::AnimationEventService::add{MouseMove,MouseDisappear,LeftClick}Animation`.

**Confidence.** `[V]` driver/timer id, one-decrement-per-tick, gates, AnimationWindow thread;
`[I]` timer interval = 1 ms (best default; the observed placement of `eventDelay` as the countdown
plus its ms labelling implies 1 ms).

**If undeterminable.** Use a 1 kHz timer (or a 1 ms-resolution loop) as the tick source; keep the
500-tick stuck guard; treat the countdown strictly as ticks.

---

## 5. Batching

**Finding.**
1. **Exactly one branch, on `enableEventBatching` (config+0x3c).** In `EventBuilder::build`
   (`FUN_1401a0110 @ 0x1401a0110`, decomp around 346534–346100), after the per-target INPUT vector
   (move + modifier-down + click + modifier-up) is assembled:
   ```
   if (*(char*)(config+0x3c) == '\0') {          // enableEventBatching == false
        /* MouseOperationsWithoutBatching */  vtable &PTR_FUN_14026d488   // one closure per INPUT
   } else {
        /* MouseOperations */                 vtable &PTR_FUN_14026d458   // one closure for the vector
   }
   ```
   `config+0x3c` is enableEventBatching (parse decomp:124117; serializer swap with
   `PTR_s_enableEventBatching_14027e190` decomp:141061–141065; default **true**, ctor decomp:76389).
   RTTI/vtable: `PTR_FUN_14026d458` = `common_events::MouseOperations(vector<INPUT>&)` — **one
   `SendInput` for the whole vector** (body `FUN_1401e7c90`, `SendInput` at 409522);
   `PTR_FUN_14026d488` = `common_events::MouseOperationsWithoutBatching(vector<INPUT>&)` — **one
   closure per INPUT, one `SendInput(1)` each** (body `FUN_1401e7bc0`, `SendInput` at 409453).
2. **`eventDelay` (config+0x38) is never slept on.** It is read per target as
   `delay = is_first_target ? 0 : *(i32*)(build_ctx+0x158)` (`bVar11` = first target,
   decomp:346070–346080) and deposited as the **countdown of the first queue element** of the
   target's block: batched path `local_5d8 = delay; FUN_14019e890(...)` (decomp:346085–346095) →
   `FUN_14019f8f0` turns it into the queue countdown; non-batched path writes it directly
   `*(i32*)(elem+0x40) = delay` (decomp:345965–345975). There is **no `Sleep`/`SleepEx`/
   `WaitableTimer`** anywhere in the injection path — the only inter-event delay is the
   `WM_TIMER(0x504)` countdown of §4. Unit = that timer's tick (1 ms by default; `eventDelay`
   default **10**, UI slider 10–30 ms).

**Evidence.** decomp:124113–124117, 141051–141065, 345965–346100; RTTI for
`common_events::MouseOperations` / `MouseOperationsWithoutBatching`;
`notes/report-interaction.md` §“Mouse & scroll injection”.

**Confidence.** `[V]` (branch condition, vtables, delay plumbing); `[I]` only for tick = 1 ms.

**If undeterminable.** Implement: if `enableEventBatching` → one `SendInput` for the whole vector,
else one `SendInput` per INPUT; inter-target delay = `eventDelay` ms applied as a queue countdown
(0 ms for the first target).

---

## 6. Config base directory

**Finding.** Base directory = **`%APPDATA%` (Roaming) + `\Neverclick`** ⇒
`C:\Users\<user>\AppData\Roaming\Neverclick\`, resolved with **`SHGetKnownFolderPath`** (not
`GetEnvironmentVariable`, not `SHGetFolderPathW`), known-folder id
`FOLDERID_RoamingAppData = {3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}`
(GUID bytes `DB 85 B6 3E F9 65 F6 4C A0 3A E3 EF 65 72 9F 3D`).
The result is stored in the core object at offset **+0x320** (decimal 800) as a wstring and later
joined with filenames (`app-config.json`, `hotkey-config.json.gz`, …) by the same `path::append`
helper.

Chain: main boot builds the wide literal `L"Neverclick"` (`FUN_1400204c0`, decomp:5516) and passes it
to the config-dir provider `FUN_14003f430 @ 0x14003f430` (decomp:55485), which stores the 16-byte
GUID at decomp:55557–55558 and calls the SHGetKnownFolderPath wrapper
`FUN_1400f6d90 @ 0x1400f6d90` (decomp:206363, call at 206389; on success copies and
`CoTaskMemFree`s); `FUN_14003f890 @ 0x14003f890` (decomp:55733) then joins base+subdir via
`FUN_140020240 @ 0x140020240` (decomp:27973) — an append that inserts a single `L'\'` (0x5c) if the
base does not already end in `\`/`/`, then appends the subdir — and checks/creates the folder
(`FUN_1401fe160`, error `"Failed to check if app folder exists: "`).
Usage as `core+800`: `FUN_140020240(&local_88, lVar8 + 800, "app-config.json")` (decomp:84327).
(NB: the `SHGetFolderPathW` helper `FUN_140002ba0` (decomp:1527) exists but is a generic
known-folder+subpath builder — it special-cases CSIDL 0x26/0x2a with `"NVIDIA Corporation"` — and is
**not** used for the config directory.)

**Evidence.** decomp:5516, 5544, 55485, 55557–55558, 55587, 55733–55742, 27973, 206363–206476, 84324–84327;
error strings `"SHGetKnownFolderPath failed. The specified folder might be virtual. Virtual folders
have no path."`, `"… might not be present on the system."`, `"SHGetKnownFolderPath failed."`.

**Confidence.** `[V]`.

**If undeterminable.** N/A — this matches the expected `%AppData%\Roaming\Neverclick\`.

---

## 7. App bar / tool editor / themes

**Finding.**
1. **`nvr::NeverAppBar` is a Windows Shell AppBar** docked to the **top edge** (`uEdge = 1 = ABE_TOP`).
   Driver `FUN_140141a40 @ 0x140141a40` (decomp part_02:21825–22700):
   `CreateWindowExW(exStyle = 0x8000080 = WS_EX_TOOLWINDOW|WS_EX_NOREDIRECTIONBITMAP,
   class = L"NeverclickAppBar", style = 0x80000000 = WS_POPUP, 0,0,0,0, …)`, then
   `SHAppBarMessage(ABM_NEW = 0, {cbSize = 0x30, hWnd, uCallbackMessage = 0x407, uEdge = 1})`
   (failure string `"Failed to register Neverclick App Bar."`). The bar height is
   `max(1, lroundf(this+0x94 * this+0xb8))` (scale × base height). Docking
   `FUN_140048b20 @ 0x140048b20`: `ABM_QUERYPOS(2)` then `ABM_SETPOS(3)` and move the HWND.
   Show/register `FUN_140048f80 @ 0x140048f80`: `ShowWindow(hwnd, SW_SHOWNA = 8)` + `ABM_NEW` +
   reposition + set `this+0x1e0` (shown); hide/unregister `FUN_140049450 @ 0x140049450`:
   `ABM_REMOVE(1)` + `ShowWindow(SW_HIDE = 0)` + teardown.
   Object layout: `+0x10` HWND, `+0x18` APPBARDATA, `+0x48` render target, `+0x94` float scale,
   `+0xb8` float bar height, `+0x1d8` bitmap, `+0x1e0` shown, `+0x1e8` enabled/registered.
2. **Router / messages.** `nvr::NeverAppBar::initRouter` is a lambda; the RTTI accessor is
   `FUN_1400494d0 @ 0x1400494d0` and the handler is `FUN_1400494e0 @ 0x1400494e0`:
   ```
   if (msg == 0x407 && wParam == 1 /*ABN_POSCHANGED*/) { FUN_1400492f0(appbar); *out=0; out[1]=1; }
   ```
   That is the **only** route: the shell's registered callback message `0x407` with
   `ABN_POSCHANGED`. There is no IPC/HTTP route for the bar itself.
3. **What it shows / when it appears.** It is an **on-demand dockable toolbar of action items**
   (buttons + row separators), *not* tied to tool activation. Items are described by classIds such
   as `"ToggleAppBar"` (`"Toggles the app bar visibility"`) and `"NewLineBelow"`.
   It is shown/hidden by (a) the **tray icon** handler `FUN_140062fc0 @ 0x140062fc0` (decomp part_00:85771–85923):
   on `WM_LBUTTONDOWN (0x201)` / `WM_RBUTTONUP (0x204)` it toggles the app-bar controller stored at
   `core+0x8b8` (controller vtable `+0x180/+0x178/+0x188`, then `PostMessage` of the controller's
   own message or `FUN_140051780`); and (b) the `ToggleAppBar` action.
   `[V]` for messages/actions; `[I]` that nothing else makes it appear.
4. **Config effects.**
   * `appBarTheme` = **config+0x168** (i32), enum table `DAT_14027f5a0..DAT_14027f780`
     (20 entries, stride 0x18), **default 0 = `Graphite`**. Resolved at runtime by
     `FUN_14013d7a0(themeId, compactAppBar)` → theme definition with **`+0x00` background colour,
     `+0x10` border colour** (higher fields: mode/action/param). Setter at part_01:76361.
   * `compactAppBar` = **config+0x16c** (u8), **default 0/false**; selects the compact variant of
     the theme definition (setter part_01:76379; both setters then call the refresh
     `FUN_1400f0d90`).
   * `GET /app-bar-themes` handler `FUN_14008ce30 @ 0x14008ce30` (decomp part_00:120600–120690)
     returns `[{name, bar:{background,border}, mode, action, param}]`.
   * **The 20 app-bar themes, in index order (verified by resolving `DAT_14027f5a0`, stride 0x18,
     name pointer at entry+0x8):**
     `0 Graphite, 1 Peridot, 2 Amber, 3 Obsidian, 4 Moss, 5 Glacier, 6 Basalt, 7 Jade, 8 Cobalt,
     9 Pewter, 10 Marble, 11 Amethyst, 12 Porcelain, 13 Frost, 14 Opal, 15 Sapphire, 16 Celadon,
     17 Aquamarine, 18 Tanzanite, 19 Topaz`.
5. **`theme` config sub-object** = `{ paletteId @ config+0x20 (JSON key **"theme"**),
   drawHintBorders @ config+0x24, style discriminator @ config+0x28 (JSON key **"styleName"**) }`.
   Serializer: style `0` → `"Modern"` (palette table `DAT_14027e9c0..DAT_14027ee28`, **47** entries),
   style `1` → `"Classic"` (table `DAT_14027f120..DAT_14027f510`, **42** entries), anything else →
   custom. Defaults (ctor): palette id **0 = `"Nevermore"`**, style **0 = `"Modern"`**,
   `drawHintBorders = true`.
   **Correction vs `report-config-ui.md`:** the earlier report swapped the two: `config+0x20` is the
   palette name emitted as key **`theme`**, and `config+0x28` is the style template emitted as key
   **`styleName`** (`Modern`/`Classic`); there are 47 Modern + 42 Classic palettes, not “46”.
   The **Modern palette list in index order** (verified): `0 Nevermore, 1 Supernova, 2 Lightspeed,
   3 Candy Shop, 4 Elements, 5 Vaporwave, 6 Volcanic Eruption, 7 Violet Sunset, 8 Opal, 9 Tropical,
   10 Golden Obsidian, 11 Dragon Fruit, 12 Northern Lights, 13 Watermelon, 14 Cyberpunk, 15 Crystal,
   16 Interstellar, 17 Coral Reef, 18 Chalk, 19 Candlelight, 20 Cosmic Dust, 21 Horizon, 22 Campfire,
   23 Renaissance, 24 Neon Tokyo, 25 Violet, 26 Blue, 27 Purple, 28 Indigo, 29 Sky, 30 Cyan, 31 Teal,
   32 Emerald, 33 Green, 34 Fuchsia, 35 Pink, 36 Rose, 37 Orange, 38 Amber, 39 Yellow, 40 Lime,
   41 Red, 42 Pastel Blue, 43 Pastel Orange, 44 Pastel Mint, 45 Pastel Lavender, 46 Pastel Pink`.
   The **Classic list (42)** (verified): `0 Nevermore, 1 Supernova, 2 Lightspeed, 3 Candy Shop,
   4 Elements, 5 Vaporwave, 6 Cyberpunk, 7 Volcanic Eruption, 8 Violet Sunset, 9 Opal, 10 Tropical,
   11 Golden Obsidian, 12 Dragon Fruit, 13 Northern Lights, 14 Watermelon, 15 Crystal,
   16 Interstellar, 17 Coral Reef, 18 Renaissance, 19 Neon Tokyo, 20 Violet, 21 Blue, 22 Purple,
   23 Indigo, 24 Sky, 25 Cyan, 26 Teal, 27 Emerald, 28 Green, 29 Fuchsia, 30 Pink, 31 Rose,
   32 Orange, 33 Amber, 34 Yellow, 35 Lime, 36 Red, 37 Pastel Blue, 38 Pastel Orange,
   39 Pastel Mint, 40 Pastel Lavender, 41 Pastel Pink`.
   `GET /theme-catalog` handler `FUN_14008d7c0 @ 0x14008d7c0` wraps the catalog builder
   `FUN_1400d59c0 @ 0x1400d59c0` (groups: Modern = Gradient 25 + Solid 17 + Pastel 5 = 47;
   Classic = 20 + 17 + 5 = 42) under key `"catalog"`.
   The overlay/hint side consumes the theme via the serializer plus `FUN_1400ea570`
   (`drawHintBorders`) and the palette via the render pipeline (rebuildGraphicsPipeline / Hint
   Painter) — the exact overlay colour plumbing was not separately re-verified `[I]`.

**Evidence.** decomp part_02:21825–22700 (`FUN_140141a40`), part_00:64299–64912 (class 0x140048xxx +
router), part_00:85771–85923 (tray), part_02:70220–70359 (ToggleAppBar/NewLineBelow),
part_00:116737/116752 (routes), part_00:120600–120690 (`/app-bar-themes`), part_01:15150–15400
(theme serializer), part_01:53301–53872 (catalog), decomp:76361/76379/76424–76427 (setters/getter);
name tables resolved from the PE `.rdata` at `0x14027f5a0`, `0x14027e9c0`, `0x14027f120`.

**Confidence.** `[V]` for the class/dock/messages/router, the table addresses+sizes, the resolved
name lists and the config offsets/defaults; `[I]` for the exact show-trigger exclusivity (tray +
`ToggleAppBar`) and for the overlay-side palette colour plumbing.

**If undeterminable.** Implement the app bar as a top-docked Shell AppBar
(`SHAppBarMessage(ABM_NEW/QUERYPOS/SETPOS/REMOVE)`, callback message `0x407`, `ABN_POSCHANGED` ⇒
reposition), shown/hidden from the tray and the `ToggleAppBar` action, with `appBarTheme`
(config+0x168, default `Graphite`) + `compactAppBar` (config+0x16c, default false) selecting the
background/border colours.

---

## 8. `enableVisibilityToScreenCapture` (config+0x3e)

**Finding.**
1. **API = `SetWindowDisplayAffinity`.** Two wrappers:
   * `FUN_1400ff410 @ 0x1400ff410`: `SetWindowDisplayAffinity(hwnd, 0x11 /*WDA_EXCLUDEFROMCAPTURE*/)`;
     log `"ExcludeFromScreenCapture failed for HWND {:#x}: {} (code {:#010x})."`
   * `FUN_1400ff2d0 @ 0x1400ff2d0`: `SetWindowDisplayAffinity(hwnd, 0 /*WDA_NONE*/)`;
     log `"AllowScreenCapture failed for HWND {:#x}: {} (code {:#010x})."`
2. **Setting → API** (authoritative, applied on config change by
   `AppConfigUpdater::setVisibilityToScreenCapture` = `FUN_1400efb60 @ 0x1400efb60`, decomp:201134–201140):
   ```
   if (config+0x3e == 0) FUN_1400ff410(...)   // WDA_EXCLUDEFROMCAPTURE  (hide from capture)
   else                  FUN_1400ff2d0(...)   // WDA_NONE               (capturable)
   ```
   i.e. **`enableVisibilityToScreenCapture = true` ⇒ windows are capturable (WDA_NONE);
   `false` ⇒ excluded (0x11)**. Confirmed by the shipped UI label:
   *“Screen Capture Visibility — Show Neverclick in screen recordings and captures.”* (checkbox bound
   to `enableVisibilityToScreenCapture`). Default from the ctor is **true**. `FUN_1400f04e0` also
   re-allows (`FUN_1400ff2d0`) `config+0x7e8` when the flag is true.
3. **Which windows.** The **hint/overlay windows** owned by the core: window objects at
   `config+0x7c0` and `config+0x7c8` (HWND at each object's `+0x20`), plus optionally
   `config+0x7e8` (when `config != -2000`, `*(u8*)(config+0x7f8) == 0` and `config+0x7e8 != 0`);
   the global allow/exclude lists are applied at decomp part_00:81193/81200/81384/81395,
   part_01:39393/75959, part_02:77809.
4. **Additional scoped use (self-capture guard).** `FUN_1401e2980 @ 0x1401e2980` builds the HWND
   vector `{config+0x7c0, config+0x7c8 [, config+0x7e8]}` and, **only when `config+0x3e != 0`**
   (i.e. only when the overlays are *not* already excluded), applies
   `FUN_1400ff410` (WDA_EXCLUDEFROMCAPTURE) to each and then runs the hint pass
   `FUN_1401f2510` (HintCoordinator::run = capture + detect + layout) inside that scope; the paired
   teardown `FUN_1401858b0 @ 0x1401858b0` calls `FUN_1400ff2d0` (WDA_NONE) on every HWND, restoring
   the user setting. Net effect: while Neverclick takes its own screen capture for hint detection,
   its overlay windows are temporarily hidden from capture so the overlay cannot feed back into the
   CV input. (Call pairs: decomp:327428/328011, 345180/345208, 397987/398015.)
   `WDA_EXCLUDEFROMCAPTURE (0x11)` requires Windows 10 2004+.

**Evidence.** decomp:213718–213834 (`FUN_1400ff2d0`/`FUN_1400ff410`), 201134–201140 (`FUN_1400efb60`),
75950–75990 (`FUN_1400f04e0`), 398776–398887 (`FUN_1401e2980`), 325239+ (`FUN_1401858b0`),
part_00:81193–81395 (allow lists); UI text in `extracted/ui-assets/assets/index-CG8hdpTV.js`
(`"Screen Capture Visibility"`, `"Show Neverclick in screen recordings and captures."`);
ctor default decomp:76389.

**Confidence.** `[V]` for API, wrapper semantics, setting polarity, default and HWND set;
`[I]` only for the *purpose* of the temporary exclusion during the hint capture pass (self-capture
guard) — the mechanics are verified.

**If undeterminable.** Implement: `enableVisibilityToScreenCapture` true ⇒
`SetWindowDisplayAffinity(hwnd, WDA_NONE)` on the overlay HWNDs; false ⇒
`SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`; and wrap each internal screen capture used
for hint detection with a temporary `WDA_EXCLUDEFROMCAPTURE` on the same HWNDs when the flag is true.

---

## 9. `graphicsPreferencePolicy`

**Finding.**
1. **Enum** (config+0x164, i32): `0 = LetNeverclickDecide` (default), `1 = LetWindowsDecide`,
   `2 = HighPerformance`, `3 = PowerSaving`, `4 = Manual`. Serializer falls back to
   `"LetNeverclickDecide"` (decomp:141503); enum table `DAT_14027f800` (24-byte entries, sentinel
   `"version"`); UI zod enumerates the same set. Setter `FUN_1400f0c40 @ 0x1400f0c40`
   (`if (*(i32*)(cfg+0x164) != v) { *(i32*)(cfg+0x164) = v; … }`).
2. **The policy does _not_ select a single probe argument.** `FUN_1400c6900 @ 0x1400c6900`
   (decomp:167226) always spawns `neverclick-graphics-check.exe` **three times**, once per literal
   argument — `--preference=1`, `--preference=2`, `--preference=none` (arg table decomp:167357–167364,
   loop tail decomp:167622). Each run is wrapped as JSON `{preference, exitCode, trace,
   report|error|rawOutput}`. This is the handler of `POST /system/graphics-check`;
   it is also invoked on `WM_DISPLAYCHANGE (0x700)` via `FUN_1400c77b0 @ 0x1400c77b0` case `0x13`
   (decomp:168622).
3. **Policy → registry** is a separate path: `HKCU\Software\Microsoft\DirectX\UserGpuPreferences`,
   value **name** = full module path of `neverclick.exe` (`GetModuleFileNameW`), **data** (REG_SZ):
   * policy 2 (HighPerformance) → `"GpuPreference=2;"`
   * policy 3 (PowerSaving) → `"GpuPreference=1;"`
   * policy 1 (LetWindowsDecide) / policy 4 (Manual, normalised to 1) → value deleted
   * policy 0 (LetNeverclickDecide) → `"=2"` if `config+0xd8c!=0`, else `"=1"` if
     `config+0xd88 ∈ {7..14}`, else delete — i.e. only overrides when a discrete GPU is present/drives
     a display.
   Mapping in `FUN_1400b0bf0 @ 0x1400b0bf0`; writer `FUN_140035bd0` (`RegCreateKeyExW` +
   `RegSetValueExW(type REG_SZ, size = len*2+2)`), delete `FUN_1400366c0`, verify `FUN_1400ee290`
   (`RegOpenKeyExW`/`RegQueryValueExW`, then re-read + compare).
4. **When it runs.** (a) Registry apply `FUN_1400b16d0 @ 0x1400b16d0` runs at startup and on
   display/monitor change; it detects `"Hybrid GPU system detected."`, computes the wanted
   preference, writes the registry, and if the value actually changed relaunches via
   `neverclick-updater.exe --launch <neverclick.exe>` and exits (`ExitProcess(0)`), so Windows
   re-launches the app on the chosen GPU. (b) The capability probe runs on demand
   (`POST /system/graphics-check`) and on `WM_DISPLAYCHANGE`.
5. **Result storage / gating.** The snapshot fields `config+0xd88` (i32), `+0xd8c` (u8),
   `+0xe38` (u8) are written from the `FUN_1400b16d0` result at the tail of `FUN_1400c6900`
   (decomp:42088–42093). `GET /machine` then reports `gpuAcceleratedRendering` (bool,
   decomp:182352), `renderingSystem` = `"Modern"|"Legacy"` (decomp:182371), `isHybridSystem`,
   `launchTimeGraphicsPreference`/`currentGraphicsPreference`/`launchValue`/`currentValue`.
   **`gpuAcceleratedRendering` does not gate the glow effect** — glow is gated by the config
   `drawGlow` flag and by successful D2D init; the `/machine` fields are informational for the UI
   System page.

**Evidence.** decomp:141503, 148209, 148228, 148261, 167226–167626, 168622, 42088–42093, 182352,
182371; registry API imports are via `api-ms-win-core-registry-*`; UI zod
`graphicsPreferencePolicy: enum([...])` in `index-CG8hdpTV.js`.

**Confidence.** `[V]` for enum, the always-3-probes behaviour, registry key/value mapping and
writers, and the run triggers; `[I]` for the exact meaning of `config+0xe38/+0xd8c/+0xd88`
(best default: `+0xe38` = isHybridSystem, `+0xd8c` = discrete GPU drives the active display,
`+0xd88` = current effective GpuPreference enum) and `[I]` that the result is status-only.

**If undeterminable.** Implement: probe all three preferences, report the JSON, and choose the
registry override from the policy as in (3); treat `gpuAcceleratedRendering` as read-only status.

---

## 10. `keyboardLayoutPolicy`

**Finding.** Enum (config+0x150, i32): **`0 = Auto` (default)**, `1 = Manual`; JSON key
`keyboardLayoutPolicy`; enum table `DAT_14027f7c8`, serializer fallback string `"Manual"`.
The earlier “default Manual” inference is **wrong** — it came from the serializer fallback; the
ctor sets 0 (decomp:76420) and the UI zod is `enum(["Auto","Manual"])`.
* **Auto**: `effectiveKeyboardLayout` (`config+0xe80`, string id) follows the **foreground window's
  focused thread** layout. `FUN_1400397d0 @ 0x1400397d0` (decomp:50258) does
  `GetForegroundWindow → GetWindowThreadProcessId → GetGUIThreadInfo → GetKeyboardLayout(thread of
  hwndFocus)`. Refresh routine `FUN_1400eeb30 @ 0x1400eeb30` (decomp:200227):
  `if (*(i32*)(cfg+0x150)==0 && detected.valid && detected != *(u64*)(cfg+0xf00)) { *(cfg+0xe80)=id;
  emit keyboardLayoutChanged; }`. It is driven by the core-owner context lambda
  `FUN_1400c3cc0 @ 0x1400c3cc0` (decomp:165160); `config+0xf00` caches the last applied HKL.
  The `/events` stream therefore carries `keyboardLayoutChanged` (event-name table) whenever the
  user switches keyboard layout in the foreground app.
* **Manual**: `FUN_1400eeb30` early-exits (`cfg+0x150 != 0`); the effective layout is pinned to the
  configured `keyboardLayout` (`config+0xC8`). On config apply, if Manual and configured != effective,
  the value is copied into `config+0xe80`, the layout-changed notification is re-emitted and the
  overlay is redrawn (decomp:77409, 77556–77562).

**Evidence.** decomp:141383–141397 (serializer for +0x150), 50258–50300 (`FUN_1400397d0`),
200227–200245 (`FUN_1400eeb30`), 165160 (caller), 77409/77556–77562 (Manual pinning), 76420 (default),
UI zod `keyboardLayoutPolicy: enum(["Auto","Manual"])`.

**Confidence.** `[V]`.

**If undeterminable.** N/A.

---

## 11. `maximize` parameter of move-window-to-monitor

**Finding.** Inside the `MoveWindow` action-config parser, the `target` string is read
(`"Pixels" | "Monitor" | "Desktop"`). For `target == "Monitor"` only
(decomp:377448–377540) the payload is `{direction:int, maximize:bool}` parsed with JSON key
`"maximize"`; **default `false`** (`uVar15 = 0; if (present_flag) uVar15 = (u8)value`).
The built action object (0x18 bytes) = `{+0 vftable &PTR_FUN_14026d098, +8 direction(int),
+0xc maximize(bool), +0x10 kind tag = 1}`. `"Pixels"` uses sub-key `"stride"` and kind 0;
`"Desktop"` uses kind 2 and has **no** `maximize` field.
Executor `FUN_1401c97a0` case 1 (`MoveWindow.DoMoveToMonitor`, decomp:378408):
`direction` selects the neighbour monitor (L/R/U/D); if none → `"No monitor detected."` and bail.
Then, with `maximize = *(u8*)(action+0xc)`:
* foreground window neither maximized nor minimized (`!IsZoomed && !IsIconic`) → move it
  (SetWindowPos `NOZORDER|NOOWNERZORDER` = 0x204, relative position preserved/clamped); if
  `maximize` → post a maximize event (lambda_1, vtable `PTR_FUN_14026d008`).
* window maximized or minimized → `ShowWindow(hwnd, 9 /*SW_RESTORE*/)`, post two rect-snapshot move
  events (vtable `PTR_FUN_14026d038`), then if `maximize` → post lambda_2 (vtable
  `PTR_FUN_14026d068`), whose invoke is `FUN_1401cae10 @ 0x1401cae10`:
  `ShowWindow(hwnd, 3 /*SW_MAXIMIZE*/); return 1;` (decomp:~377513).
So: `maximize = true` ⇒ after relocation the window is maximized (`SW_MAXIMIZE`);
`maximize = false` ⇒ left restored/moved only. Restoring (`SW_RESTORE`) of an
already-maximized/minimized window happens regardless, to permit the move.

**Evidence.** decomp:377448–377540 (parse), 378408–378520 (executor), 377513 (`FUN_1401cae10`),
13360–13535 (case-1 body with `ShowWindow(...,9)` and the vtable posts);
`report-interaction.md` “Move window” section already records the trailing bool + those vtables.

**Confidence.** `[V]` for type/default/executor; `[I]` that lambda_1 (already-restored path) also
maximizes — it is posted only when `maximize` is set and lives in the same lambda cluster.

**If undeterminable.** Default `maximize = false`.

---

## 12. Update flow

**Finding.**
1. **There is no client-side version comparison.** `neverclick.exe` sends its version and trusts
   the server. Update-check coroutine `FUN_1400cf360 @ 0x1400cf360` builds a JSON body with keys
   **`instance_id`**, **`app_version`**, **`locale`** (`GetUserDefaultLocaleName`) and POSTs it
   (`FUN_14011a020`, timeout 10 000 ms) to `https://www.neverclick.com/api/version`. On HTTP 200 it
   requires an object `update` with keys `available`, `latest_version`, `download_url`
   (`release_notes`, `release_notes_url`, `sha256` optional) and copies `available` verbatim into
   `UpdateInfo` (no threshold, no comparison). Errors: `"Response missing 'update' field"`,
   `"Response missing required fields"`.
   *(The Rust UI embeds the `semver` crate, but the engine does not.)*
2. **Endpoints/URLs.** Base host `https://www.neverclick.com` (init, decomp:5493); update endpoint
   `/api/version` assembled from the qwords `/api/ver` + `sion` (decomp:5510–5535), method **POST**.
   REST routes on `0.0.0.0:7340`: `/version` (decomp:116767), `/update-info` (116879), `/update`
   (116895), `/update-check` (116911). Download URL is **server-supplied** (`download_url`);
   staging path = `GetTempPathW() + "NeverclickSetup.exe"` (`FUN_1400892c0`, decomp:118109–118140),
   fetched with GET; integrity = **CryptoPP::SHA256** over the body compared to the server `sha256`
   field (mismatch → `"Installer verification failed: SHA-256 mismatch (expected …"`);
   spawn `neverclick-updater.exe` via `FUN_1400d14d0 → FUN_1400d0860` with
   `--parent-pid <pid>` (+ `--ui-pid <pid>` when the UI is running) and/or `--install`.
3. **`update-info.available`** = raw JSON boolean `update.available` (byte `+8` of the message
   struct, copied to `UpdateInfo+0x240`); the REST serializer `FUN_14008a0f0` emits `available`,
   `latestVersion`, `downloadUrl`, `checkCount` (+ optional `releaseNotes`, `releaseNotesUrl`,
   `error`).
4. Mechanics: hourly `SetTimer(hwnd, 0x407, 3 600 000)` (decomp:84403) and throttle
   `FUN_140062760 @ 0x140062760`: minimum interval **30 min** by default, **12 h** when
   `Neverclick+0x1630 != 0`, overridable by an optional duration argument. Transport is WinHTTP
   (`WinHttpOpen(L"Neverclick",…)`, 5 s/5 s/10 s timeouts).

**Evidence.** decomp:5493, 5510–5535, 84403, 85450–85508, 116767–116911, 118109–118470, 118440–118760,
236100+ (`FUN_14011a020`); `notes/scratch-configui/updater-decomp.c`;
`notes/scratch-configui/ui-strings.txt` (semver crate strings only in the UI);

**Confidence.** `[V]`.

**If undeterminable.** The comparison rule is server-side and not in the binary — a faithful
reimplementation must replicate the request (`app_version` semver string) and trust
`update.available`; do **not** invent a local comparator.

---

## 13. FailSafe `requestWindowControls` consumer

**Finding.**
1. **Method address/slot.** `FailSafeUiAutomationManager::requestWindowControls(HWND, HWND, unsigned)`
   = `FUN_1401f91a0 @ 0x1401f91a0` (decomp:417398), at **vtable `0x14026d758` slot `+0x38` (index 7)**;
   the manager is built by the factory `FUN_1401a19a0` case 3 (decomp:346532), inner manager from
   `core+0xe78`.
2. **Callers** (all indirect through slot `+0x38`) — the **hint-session/provider-dispatch drivers**:
   * `FUN_1401e1620 @ 0x1401e1620` (call ≈ decomp:397975–397977; also part_03:32716)
     ```
     uVar4 = (**(code**)(*plVar1 + 0x38))(plVar1,
                 uVar5 & 0xffffffff,                                     // arg1 (dead HWND)
                 *(u64*)(*(longlong*)(*param_1 + 0x7c0) + 0x20),         // arg2 = notify HWND
                 0x510);                                                // arg3 = message id
     *(u64*)(param_3 + 0xa0) = uVar4;                                   // ticket stored on the tool
     ```
     where `plVar1 = *(longlong*)(param_3 + 0x88)` = the FailSafe manager.
   * `FUN_14019f9e0 @ 0x14019f9e0` (decomp part_02:97708–97710) — byte-identical call, the sibling
     instantiation.
   Both are the **fallback branch**: they are reached only when the normal hint dispatch
   `FUN_1401f2510` (`HintCoordinator::run`) cannot run — the preceding gates are
   `vtable+0x20()` (slot 4), `vtable+0x30()` (slot 6, boolean gate) and `FUN_1401f3f50`.
3. **Argument semantics.**
   * **arg1 (first HWND) — dead/ignored.** `uVar5 & 0xffffffff` is a zero-extended 32-bit
     *target-window* candidate computed just before the call (either `0`, or `**(u32**)(core+0xfa8)`,
     or the low dword at `tool+0x98`); it is also stored at `*(i32*)(tool+0xa8)`. The callee never
     references its `param_2` — it re-captures the watched window itself via
     `FUN_1401f8d10` (`CaptureForegroundTarget`). So the argument is vestigial; pass `0` in a
     reimplementation.
   * **arg2 (HWND) — the notification window.** `*(u64*)(*(longlong*)(ctx+0x7c0) + 0x20)` = the HWND
     of the window object at `CoreServices+0x7c0` (the Neverclick overlay/hint window; a thunk
     `FUN_140064960` forwards its messages to the main wndproc `FUN_1400612c0`). The `{ticket, rects}`
     payload is `PostMessage`d to **this** window.
   * **arg3 (uint) = `0x510`**, the notification message id. There is no timeout.
   * **Return value = ticket** (counter `fetch_add` at manager `+0x70`); stored at `tool+0xa0`
     (or `tool+0x148` for `basic_mouse_action_tool`, cleared by its teardown `FUN_140177b30`).
4. **`{ticket, rects}` flow.** Payload = heap block (`FUN_1401feca0(0x20)`) shaped as
   `{ u64 ticket; vector<nvr::Box> {begin,end,cap} }`. It is delivered
   `PostMessageW(notify, 0x510, payload, 0)` either immediately by `FUN_1401f91a0` when there is no
   valid foreground target (empty rects — the true “fail-safe” path), or by the queued closure
   `FUN_1400480f0`/`Deliver` `FUN_140047cb0` after subscribing to `UIA_AsyncContentLoadedEventId
   (0x4e26)` on the foreground element; rects = all control-view descendant `BoundingRectangle`s.
   Consumers:
   * the active tool's event chain: `FUN_140177d70 @ 0x140177d70` (basic mouse tool) on
     `msg == 0x510` — `plVar10 = *(longlong**)(param_3+2)` (payload); if `*plVar10 == tool+0x148`
     (ticket match) it **moves the vector out** (`payload[3]=0; payload[2]=0; payload[1]=0`) and
     feeds it into the hint pipeline (`FUN_1401a0060`, `FUN_1401f26a0`, `FUN_14019fda0`) as
     window-control hint boxes;
   * a second tool chain (~`FUN_14018be60`, decomp part_02:83048) on `msg == 0x510` calls
     `FUN_1401e2390(&x, tool+0x18, tool+0xb0, *(param_3+2))` to process the payload;
   * the main wndproc fallback `FUN_1400612c0 @ 0x1400612c0`, `case 0x510` (decomp:84801–84804):
     `if (payload) { FUN_14000de90(payload+1); free(payload); }` — drains/frees only (a safe no-op
     if a tool chain already stole the vector); it does not use the rects.

**Evidence.** decomp:417398 (`FUN_1401f91a0`), 346532 (factory case 3),
397916–397977 (`FUN_1401e1620`), part_02:97708 (`FUN_14019f9e0`), part_02:66041/83048 (the 0x510
consumers), 84801–84804 (wndproc case), 312844 (`FUN_140177800`);
vtable `0x14026d758` slot `+0x38`; `notes/report-interaction.md` §UIA (context).

**Confidence.** `[V]` for the method/slot, both call sites, the arg expressions, the ticket storage,
the payload layout/lifetime and the three consumers; `[I]` only for the exact window class behind
`CoreServices+0x7c0` (“overlay/hint window”) and the enclosing-function identity of the second
consumer (`~FUN_14018be60`).

**If undeterminable.** N/A — implement as: `requestWindowControls` ignores its first HWND argument,
re-captures the foreground window itself, and posts `{ticket, vector<Box>}` to the notify HWND with
message `0x510` (always at least one delivery, possibly with zero rects); the caller stores the
ticket and matches it when the payload arrives.

---

## 14. `stickyHints` re-anchoring details

**Finding.**
1. **`ImageRecognition` uses the GPU template matcher.** Re-anchoring re-finds the saved needle(s)
   with `nvr::detail::GpuTemplateMatcher::searchAll` (`FUN_1401311c0 @ 0x1401311c0`, the same
   12-probe SAD compute-shader matcher as `report-vision.md` §4.6) over a fresh capture, and works
   **only when the active provider is Vision**; any other provider yields
   `"'{}' cannot anchor by image recognition"` (anchor builder `FUN_1401dd770`, decomp part_03:29180).
   Params: `TemplateMatchParams{ double fraction @0, u32 tolerance @8 = 0x18 (24) }`;
   needle = `CpuImage{u32 w,u32 h,u32 stride,const u8* pixels}` BGRA; score = `1 − err/max`, NMS.
2. **`matchAccuracy`** = sticky-entity `+8` (float), serialised under key `matchAccuracy`
   (decomp part_02:79530). Fed as `TemplateMatchParams.fraction` — the minimum fraction of probes
   that must match (0..1; UI exposes a percentage; higher = stricter). `[I]` for the numeric wiring.
3. **`maxDistance`** = optional scalar at sticky-entity `+0x44`, emitted only when the presence flag
   `+9` is set (decomp part_02:79546). It bounds how far (px) a match may be from the saved anchor
   (search radius); absent = whole-capture search (**best default: absent → unbounded**). `[I]` for
   the numeric wiring.
4. **Value domains.**
   * `persistence` (string enum): **`OnePress`**, **`Persistent`**; fallback/default `Persistent`.
   * `closeBehavior` (string enum): **`CloseAfterPress` = 1** (verified); exactly one more member
     exists but its literal could not be isolated → **best default value 0 ≈ “keep open / do nothing”**.
   * `keyAssignment` (string enum): **`Automatic`** (default/fallback); one more member, most
     plausibly `Manual` `[I]`.
   * `visionStrategy`: **`ScreenPosition`** / **`ImageRecognition`**.
   * Note: `"Grid Mode is not available with the Image Recognition anchor."`
5. **Auto key assignment output.** When `keyAssignment = Automatic`, the tool reuses the **normal
   hint combo generator** over the current hint alphabet (`FUN_1401e2630` combo list,
   `FUN_1401e2750` pairing) to produce the same 1–4-char combos used for hints, dedupes against
   already-assigned bindings (`FUN_14010a3d0` collision check), and stores one combo per sticky slot
   as a normal key binding via `FUN_14018dac0` into `tool+0xe8` / `*tool+0x20`. The emitted label is
   the combo itself (e.g. `JJ`, `FJ`), not a synthetic label; a press dispatches
   `nvr::sticky_hints_tool::Tool::dispatchStickyClick(AppContext, win::Key, Point)`.
   Status strings: `"Assigned {} of {} hints. Not enough keys for the rest."`,
   `"No hint keys are available for automatic assignment."`, `"Press an assigned key to click its hint."`.

**Evidence.** `FUN_1401311c0` RTTI (part_02:8261), `FUN_1401dd770` (part_03:29180–29340),
serialiser part_02:79220–79600, parser `FUN_1401dbce0 @ 0x1401dbce0` (part_03:27919),
enum helpers part_02:83154–83266, auto-assign `FUN_1401e5440` (part_03:35800–36480),
strings `strings4.txt:41006-41011,41481,41487-41488`,
`notes/scratch-hints/part_02`, `part_03`.

**Confidence.** `[V]` for ImageRecognition using `searchAll`, the parameter types/serialisation, the
enum members `OnePress/Persistent/CloseAfterPress(=1)/Automatic/ScreenPosition/ImageRecognition`,
the auto-assign generator and messages; `[I]` for the exact numeric wiring of
`matchAccuracy`/`maxDistance` and for the missing enum literals.

**If undeterminable.** `fraction = matchAccuracy` (0..1), `radius = maxDistance` px or unbounded;
`closeBehavior` second member = value 0 = keep-open; `keyAssignment` second member = `Manual`.
