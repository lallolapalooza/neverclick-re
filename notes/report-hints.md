# Neverclick 0.4.1 — Hint labels, assignment & target geometry (static analysis report)

> **Artifact availability.** `neverclick.exe`, `ghidra/neverclick-decomp.c` and the raw scratch dumps
> (`notes/scratch-hints/part_0[0-3]`, `strings4.txt`) have been removed from this tree. Citations of the form
> `part_NN:line` and `strings4.txt:line` refer to those removed dumps and cannot be re-opened; the analysis
> and reconstructed pseudocode remain authoritative.

Scope: `extracted/app/neverclick.exe` (4,529,424 B, MSVC x64, ns `nvr`), decomp `ghidra/neverclick-decomp.c`.
All addresses are image VAs (`0x140……`); function names are Ghidra `FUN_` labels — the binary has no
RTTI for most classes, so identities below are established by RTTI *lambda* names, closure vtables and
string references (each identification shows its evidence). Claims marked `[INFERENCE]` are reasoned
but not directly observable.

Cross-references: `notes/public/behavior-external.md`, upstream README (quoted as README:NN).

---

## 1. Summary

* **Hints are 1–4 character combos**, depth chosen adaptively (`d = min d∈[1,4] : |A|^d ≥ needed`,
  `FUN_140146430 @ 0x140146430`), 2 chars for normal screens. Candidate keys = **`keyCodes` config
  order**, filtered to alphabetic characters (`FUN_140104330 @ 0x140104330`); that order **is the
  Key Priority Map** (most convenient first). Default = a hardcoded 48-key priority list
  (`FUN_1400056f0 @ 0x1400056f0`), whose 26 letters give the default alphabet
  `J F K D L S A V M E I C N O W R U G H T B Y X Q P Z`.
* **Combo convenience order** (`FUN_1401464f0 @ 0x1401464f0` + `FUN_140146c90 @ 0x140146c90`):
  generate combos group-by-group by the *worst* (highest index) key used; inside a group sort
  **ascending by the sum of key-priority indices**. With the default alphabet this puts `JJ` first,
  then `FJ/JF`, then `FF` — matching the author's "JJ and FF at the top" (HN, unquoted here).
* **Assignment** (`FUN_14014b160 @ 0x14014b160`, `hintAssignment = CenterFirst` = default):
  all hint slots are sorted **ascending by squared distance to the centre of the foreground window's
  DWM extended frame** (fallback: centre of the first box), then combo *i* is paired with slot *i* —
  a straight sorted-pairwise greedy. `hintAssignment = Random` shuffles combos with MT19937
  (`FUN_14014a200 @ 0x14014a200`) instead. Author's "centre of the screen" is refined →
  **foreground-window centre**.
* **Grid modes** (`GridProvider::run = FUN_1401f8330`, `FullScreenGridProvider::run = FUN_1401f8c10`):
  uniform cells with `cols=floor(W/spacing)`, `rows=floor(H/spacing)`, `spacing = 100 px × dpi_scale`,
  cell size = exact `W/cols × H/rows` (float), row-major order.
* **Target geometry**: box centre by default; arrows / `Shift+JIKL` → `SnapTargets` action
  (direction → box edge); number row → `MoveTargets` (direction/stride/percent parameters exist in
  the action schema). The per-target *slot* list (`vector<Box>` at target+0x38) is what
  distance-sorting and edge logic operate on. Exact digit→point formula not located (§9 Gaps).
* **Rendering**: DirectWrite (`DWriteCreateFactory`, `IDWriteFactory3`, custom font collection loaded
  from `<exe>/fonts`), Direct2D (bitmap RT, glow), DirectComposition overlays; window classes
  `Neverclick`, `NeverclickLayer`, `NeverclickWindowBorder`, `NeverclickAnimationWindow/Overlay`.
* **Sticky hints**: JSON config (`stickyHints`/`stickyButtons` + `anchor`, `persistence`,
  `visionStrategy=ScreenPosition|ImageRecognition`, `matchAccuracy`, `maxDistance`, `clickOffset`,
  `keyAssignment`, …); auto key assignment reuses the same combo generator (`FUN_140146350` call
  sites at `0x140177…` region, part_02:86225/99229).

---

## 2. Hint pipeline flow

### 2.1 Session → coordinator

Two nearly identical session drivers, `FUN_1401e1620 @ 0x1401e1620` (part_03:32659) and
`FUN_14019f9e0 @ 0x14019f9e0` (part_02:97639):

```
session+0x88 = primary provider      (HintProvider&)
session+0x90 = secondary provider    (HintProvider*, may be null)
session+0x98 = {FovMode : u32, flags : u32}       (also mirrored at session+0xa8)
session+0xa0 = cached layout ptr
FovMode ← session+0x98.low, else **(u32**)(config + 0xfa8)   // live fovMode config
FUN_1401f2510(session, &Result, FovMode, primary, secondary)
```

`FUN_1401f2510 @ 0x1401f2510` (part_03:46559) = **`HintCoordinator::run` core** (identified by:
it constructs the closure whose RTTI is
`` `<lambda_1>@?CC@??run@HintCoordinator@nvr@@…` `` via `*param_2 = &PTR_FUN_14026d518`, whose ctor
`FUN_1401f4880` and typeinfo accessor `FUN_1401f4870` carry exactly that RTTI name):

1. cache key = `vtable[3] (+0x18)` of primary provider (u64 id/version);
2. FNV-1a lookup in coordinator's `unordered_map` (`FUN_1401f3f50 @ 0x1401f3f50`):
   *hit* → copy cached layout into `Result`, `Result+0x58 = 1`;
3. *miss* → `uVar = vtable[1] (+0x08)(primary, sret, FovMode)` = **provider->run(FovMode)** returning
   `HintProviderResult`, then `FUN_1401f26a0 @ 0x1401f26a0` does assignment/layout (§4), producing
   `Result+0x58 = 0`.
   Mode-switch actions clear the cache via `FUN_1401f4030 @ 0x1401f4030` (e.g. `FUN_14019ba50`
   case 6/0xc/0xd, part_02:94700–94790).

### 2.2 HintProviderResult (104 bytes, sret)

Observed layout (Vision run `FUN_1401f5f70` writes it; `FUN_1401f26a0` consumes it):

| offset | field | evidence |
|---|---|---|
| +0x00..+0x17 | `vector<Target>` (begin,end,cap) | `*param_6 == param_6[1]` empty test |
| +0x18 (u8) | variant tag: `0` = needs assignment; `1` = pass-through | `(char)param_6[3]` branch; Custom run writes `*(param_2+3)=1` |
| +0x20..+0x38 | `std::function` closure built by the provider's `run` lambda | Vision: `local_b8=&PTR_FUN_14026d548; FUN_1401f7ff0(&local_b8, param_2+2)` (param_2 is `u8(*)[16]`, `+2` → +0x20) |
| +0x58 (i32) | result status: 0 fresh, 1 cached, 2 secondary-fallback | `*(param_2+0xb)=…` writes |

`Target` (0x68 bytes; stride constant `0x4ec4ec4ec4ec4ec5` = /104):
box L/T/R/B at **+0x08/+0x0c/+0x10/+0x14** (centre computed as `(i@+0x10 + i@+0x08)/2`,
`(i@+0x14 + i@+0x0c)/2` in `FUN_14014b160`), **`vector<Box>` slots at +0x38..+0x4f** (16-byte
`{left,top,right,bottom}` each), members at +0x50..+0x67 (strings/ids).

### 2.3 Provider virtual interface (vtable slots seen)

| slot | offset | role | evidence |
|---|---|---|---|
| 1 | +0x08 | `HintProviderResult run(FovMode)` (sret) | `(**(*param_5+8))(param_5,&local_14c8)`; `uVar5 = (**(*param_4+8))(param_4,local_a8,param_3)` in FUN_1401f2510 |
| 2 | +0x10 | layout-state getter → `config+0xF10` state | `return *param_2 + 0xf10;` part_02:21603 |
| 3 | +0x18 | cache-key u64 | FUN_1401f2510 |
| 5 | +0x28 | predicate (bool) | mode-switch `(**(*(…+0x88)+0x28))()` |
| 6 | +0x30 | predicate (bool) | session drivers |
| 7 | +0x38 | `(mode, hwnd, 0x1510?)` helper | session drivers |

### 2.4 Provider implementations

| provider | function | notes |
|---|---|---|
| `VisionProvider::run(FovMode)` | **`FUN_1401f5f70 @ 0x1401f5f70`** (part_03:49449) | builds l2/l34 closures (`PTR_FUN_14026d548` @50320, `14026d578` @49714 whose RTTI accessors `FUN_1401f7f50/FUN_1401f8010` name `run@VisionProvider`). FOV rect selection (part_03:49643–49700): `FovMode 0` = foreground-window rect (validated by `FUN_1401f5ae0 @ 0x1401f5ae0`: visible, not cloaked (`DwmGetWindowAttribute 0xd`), not hung, not iconic, non-empty titled frame); `1` = monitor of fg window (`FUN_140102210`); `2` = all-monitors rect. Special foreground windows (`FUN_140039640`) **force mode 2** (`iVar51 = 2; if (cVar8=='\0') iVar51 = param_3;`). |
| `GridProvider::run(FovMode)` | **`FUN_1401f8330 @ 0x1401f8330`** (part_03:51309) | closure `PTR_FUN_14026d5f8` set at 51600; RTTI accessor `FUN_1401f8940`. |
| `FullScreenGridProvider::run(FovMode)` | **`FUN_1401f8c10 @ 0x1401f8c10`** (part_03:51815) | closure `PTR_FUN_14026d678` @51839; RTTI accessor `FUN_1401f8cf0`; body = `FUN_1401f8960(this+0x50)` (per-monitor cells). |
| `UiAutomationProvider::run(FovMode)` | **`FUN_1401f9070 @ 0x1401f9070`** (part_03:52073) | fg-window only: `FUN_1401f8d10` capture check → empty Result (closure `14026d728`) or UIA query (`FUN_1400f7b90`) → `ToResult`. |
| `UiAutomationProvider::ToResult(vector<Box>, ForegroundTarget)` | **`FUN_1401f8e20 @ 0x1401f8e20`** (part_03:51946) | RTTI `` `…ToResult…vector<UBox@nvr@@…>,ForegroundTarget@UiAutomationProvider…` `` matches signature; pads rect by ±2 px, dpi at target+0x18; empty → closure `14026d728` (`EmptyResult`, `FUN_1401f9070`'s empty path). |
| `EmptyResult()` | `FUN_1401f9070` empty path / `FUN_1401f9470` closure | RTTI `FUN_1401f9450`. |
| `CustomProvider::run(FovMode)` | **`FUN_1401f9c80 @ 0x1401f9c80`** (part_03:52748) | queries fg window + `FUN_1401f9470(this+8)` custom box source, falls back to stored boxes at `this+0x20`; sets **tag = 1** → boxes pass through *without* combo assignment (coordinator else-branch `FUN_1401f4840`, part_03:46796/47927 area). |

### 2.5 Merging / switching (vision ↔ clairvoyance `[`, grid `;`)

* `HintCoordinator::run(FovMode, HintProvider&, HintProvider*)` takes a primary and an *optional*
  secondary. Merge rule inside `FUN_1401f26a0`: **if primary's target vector is empty and secondary
  != null → run secondary and return its Result with status = 2** (part_03:46665–46690:
  `if ((*param_6==param_6[1]) && (param_5!=0)) { (**(*param_5+8))(param_5,&local_14c8); … *(param_2+0xb)=2 }`).
  If primary non-empty, the secondary is not consulted.
* Mode switching itself replaces the session's provider and clears the layout cache:
  `FUN_14019ba50` case 1 (`FUN_1401e8e30` = vision), case 2 (`FUN_1401e8ec0` = clairvoyance),
  case 6 = grid (`FNV hash of "GridProvider"`), then `FUN_1401f4030(coordinator_cache)`.
  Provider display names: `VisionProvider/UiAutomationProvider/GridProvider` strings at .rdata
  `0x14028a970`; enum strings `Vision, Grid, FullScreenGrid, Clairvoyance, Custom`.
* `FovMode` enum (config table @ `0x14027f780`, key `fovMode`, default **AllMonitors**):
  `0=Window, 1=Monitor, 2=AllMonitors` (README: Tab cycles it; action `CycleFieldsOfVision`).

### 2.6 State object (`config+0xF10`, provider vtable[2])

Built by `FUN_140140c60 @ 0x140140c60`:
`{ +0x00: const vector<u32>* alphabet, +0x08: i32 hintAssignment (0=Random,1=CenterFirst),
+0x10: f32 1.0 (load factor), +0x18: unordered_set sentinel, +0x20: cache ptr (0 = invalid),
+0x28..+0x48: hash buckets {mask=7, n=8}, +0x50: i32 cached depth }`.
Cache validity check everywhere: `state[4]==0 || (i32)state[10] != depth → rebuild`
(`FUN_1401f26a0` part_03:46713, `FUN_1401499c0` part_02:28250).
`enableProgressiveHints` is written to `config+0x158`/`+0xd7d` (`FUN_1400f0b00`) but **no reader was
found** — see Gaps.

---

## 3. Combo generation & scoring (formulas)

### 3.1 Alphabet = priority-ordered keys

`FUN_140104330 @ 0x140104330` builds the hint alphabet:

```
for code in config.keyCodes (ORDER PRESERVED):          # scan codes
    if keyOverrides[code] exists:
        if value == 1 ("Off") -> skip
        if value == 0 ("On")  -> include, no filter
    else:
        resolve code -> unicode char via layout (config+0xe80 position→unicode map)
        fail  -> log "Layout \"{}\" maps no key to position {}. Dropping it from the hint alphabet."
        include ONLY if GetStringTypeW(CT_CTYPE1) & C1_ALPHA (0x100)   # letters only
letters empty? -> use all resolved keys + log "…puts no letters on any hinted position; falling back to {} non-letter key(s)…"
both empty    -> fall back to ASCII 'A'(0x41)..'Z'(0x5A) + log "…falling back to the Latin A-Z keys."
```

`FUN_1400ee700 @ 0x1400ee700` wraps it (if ≤1 usable key after overrides → warn
`"Key overrides leave {} usable key(s) on layout \"{}\"; ignoring the overrides…"` and rebuild with
empty overrides). Validation `FUN_1400f04e0`: fewer than 2 enabled keys → error
`"At least {} keys must stay enabled for hints."`; `keyCodes must not be empty / must not contain duplicates`.

**Default Key Priority Map** — `FUN_1400056f0 @ 0x1400056f0` (CRT init) allocates the global default
vector (`DAT_1402dec38..40` = begin/end, 48 × u32) from 24 qwords `0xHHH…LLL`:

```
 0: 36,33   1: 37,32   2: 38,31   3: 39,30   4: 47,50   5: 18,23
 6: 46,51   7: 49,24   8: 17,19   9: 22,34  10: 35,20  11: 48,21
12: 45,52  13: 16,25  14: 44,53  15: 40, 5  16:  8, 4  17:  9, 3
18: 10,26  19: 27, 2  20: 11, 6  21:  7,12  22: 13,43  23: 41,86
```

Flat priority sequence (scan codes → QWERTY positions):

| rank | 1–8 | 9–16 | 17–24 | 25–32 | 33–40 | 41–48 |
|---|---|---|---|---|---|---|
| keys | J F K D L S ; A | V M E I C , N O | W R U G H T B Y | X . Q P Z / ' D4 | D7 D3 D8 D2 D9 [ ] | D1 D0 D5 D6 - = \ ` |

(letter ranks only — the default **alphabet** is the 26 letters in this order:)
`J F K D L S A V M E I C N O W R U G H T B Y X Q P Z`

The order is symmetric-pair-wise (right/left home-row outward: J/F, K/D, L/S, ;/A, then bottom-index
V/M, top-index E/I …). Empty/absent `keyCodes` in app-config falls back to this vector
(`memmove(…, DAT_1402dec38, …)` in config-apply, part_01:77596). **No numeric weights exist —
priority is pure rank = array position.** (The GUI "Key Priority Map" edits `keyCodes` order;
`/key-position-to-key-code-map` & `/key-code-to-unicode-map` HTTP routes exist for it.)

### 3.2 Depth

`FUN_140146430 @ 0x140146430` (also inlined in `FUN_14014a200`, `FUN_14014b160`, `FUN_1401f26a0`):

```
N = (existing_combos) + (number_of_slots)     # slots = Σ per-target vector<Box> size
d = 1; while d<4 and |A|^d < N: d++   ; cap d=4
```
For ≤676 slots with |A|=26 → **d = 2** (the normal case).

### 3.3 Generation order = the "convenience" sort

`FUN_1401464f0 @ 0x1401464f0` (group loop, ~320 lines) — pseudocode reconstructed from
part_02:25555–25882:

```
out = []
g = 1
while g <= |A| and len(out) < N:
    group = []
    for c in 0 .. g^d - 1:
        digits = []                      # mixed radix, LEAST significant first
        t = c
        for i in 0..d-1:  digits.append(t % g); t /= g
        flag = any(digit == g-1 for digit in digits)      # touches the newest key
        combo = reverse([A[digit] for digit in digits])    # FUN_1401fd4c0 = std::reverse
        sum_key = Σ digits
        if flag and combo not in seen_set:                 # FNV-1a hash set, dedupe
            group.append({combo, sum_key})                 # 32-byte entry, key at +24
    FUN_140146c90(group, depth_limit)                       # std::introsort by key ASC
    move group entries into out until len(out) == N
    g += 1
```

* Group `g` = combos whose **worst (max-index) key has rank g** — primary sort key = `max digit index`.
* Secondary key = **sum of digit indices** (`local_e0 += digit` per position, stored at entry+24,
  compared in `FUN_140146c90` as `entry[3]` ascending).
* Small groups (≤32 entries) hit the insertion-sort path → ties are stable in build order
  (`c` increasing).

**Resulting top of list with default alphabet:**
`JJ` (g=1), then `FJ`, `JF`, `FF` (g=2: sums 1,1,2), then g=3 with K/D… — i.e. "JJ and FF at the
top" ✓; exact per-combo score = **(max rank, sum of ranks)** lexicographic, not a weighted cost.

The group context (fresh per call) is built by `FUN_140146350 @ 0x140146350` (unordered_set, 16-byte
buckets, mask 7, load factor 1.0). `enableUppercaseHints` does **not** affect generation — it is
passed into the render pipeline (§7).

---

## 4. Assignment algorithm

### 4.1 CenterFirst (default) — `FUN_14014b160 @ 0x14014b160`

```
combos = generate(alphabet, depth, needed = Σ slots)          # §3 order

# reference point:
ref = center(DwmGetWindowAttribute(GetForegroundWindow(), 9 /*EXTENDED_FRAME_BOUNDS*/))   # FUN_14003d330
if no fg window or rect invalid:
    ref = center(first target's box)                          # (i@+0x10 + i@+0x08)/2, …

# per slot record (24 B): {target_idx, slot_idx, dist2}
for t in targets:                        # stride 0x68
    for j,box in t.slots(+0x38):         # stride 0x10
        dx = ref.x - (box.left + box.right)/2
        dy = ref.y - (box.top  + box.bottom)/2
        dist2 = (int)(dy*dy + dx*dx)                    # integer truncation
        records.append({t, j, dist2})

sort records ASC by dist2                                # FUN_14014cf60 (introsort)
K = min(len(combos), len(records))
for i in 0..K-1:                                         # sorted-pairwise greedy
    targets[records[i].t].slots[records[i].j] ← move combos[i]
if len(combos) < slots:
    log "Hint alphabet covers only {} of {} targets; the farthest targets get no hints."
```

* Metric: **squared Euclidean distance in integer screen coords** (window coords for `FovMode=Window`
  since boxes come from the same capture rect). Not normalised.
* Pairing is O(n log n) sort + linear pass — no Hungarian/Jonker-Volgenant; strictly
  "most convenient combo ↔ nearest slot".
* Multi-monitor: boxes may span the virtual desktop (`FovMode=AllMonitors`); the reference stays the
  **foreground window's** centre — the nearest slot on a far monitor still ranks behind all
  near-monitor slots, so assignment is monitor-ordered implicitly.
  Author's HN quote ("center of the screen") is *refined*: it's the FG-window centre with
  first-box-centre fallback.

### 4.2 Random — `FUN_1401499c0 + FUN_14014a200 + FUN_14014a550`

Selected when `state[1] (hintAssignment) == 0` (`FUN_1401f4120 @ 0x1401f4120`,
`if ((int)plVar3[1] != 0) FUN_14014b160; else FUN_1401499c0/14a200/14a550`).

* `FUN_1401499c0` builds the per-target slot lists (identity slot indices, with the same
  cache-validity check).
* `FUN_14014a200` generates the combo list at the needed depth, **shuffles it with a stack-local
  MT19937** (classic init: `seed=0x1e240, N=0x270, a=0x6c078965`, part_02:28795–28805 →
  `FUN_14014cce0` = `std::shuffle`), then walks targets/slots in natural order popping shuffled
  combos.
* Overflow message here: `"Hint alphabet covers only {} of {} targets; the rest get no hints."`
* `FUN_14014a550` merges the assignment back into the Result.

### 4.3 Depth/overflow behaviour (boxes > combos)

No 2nd-level/progressive re-generation was observed in the assignment path: when
`slots > |A|^d`-capped combo count, depth grows (up to 4 → 26⁴ = 456 976 combos), and only if the
alphabet still can't cover every slot, the **farthest (CenterFirst) / remaining (Random) targets get
no hints** (log strings above). `enableProgressiveHints` exists as config but its reader was not
found — see Gaps.

---

## 5. Grid algorithms

`FUN_1401fa950 @ 0x1401fa950` — the single cell generator:

```
cols = floor((right-left) / spacing)          # float floor
rows = floor((bottom-top) / spacing)
if rows > 0:
    cw = (right-left)  / cols                 # float cell size (exact division)
    ch = (bottom-top)  / rows
    for r in 0..rows-1:                       # ROW-MAJOR
        y0 = top + (int)(r * ch)
        for c in 0..cols-1:
            x0 = left + (int)(c * cw)
            emit Box{x0, y0, x0 + (int)cw, y0 + (int)ch}
# rows<=0 or cols<=0 -> empty vector
```

Spacing = **100 px × scale** everywhere:

* `GridProvider::run FUN_1401f8330`:
  * `FovMode=0` Window: fg window DWM rect; `scale = GetDpiForWindow(fg)/96` (fallback 1.0);
    `spacing = scale*100.0` (part_03:51400).
  * `FovMode=1` Monitor: `MonitorFromWindow(fg, MONITOR_DEFAULTTONEAREST)` → `FUN_140101bf0`
    monitor rect; `spacing = monitor_dpi_float * 100.0`; if monitor query fails → provider's cached
    last rect (`this+0x08`) with cached dpi at `this+0x34`.
  * `FovMode=2` AllMonitors & window-rect failures → `FUN_1401f8190 @ 0x1401f8190`: iterate
    provider's monitor table at `this+0x50` (56-byte entries: rect at +0x18..+0x28, `f32 dpi` at
    +0x34) and grid each with `dpi*100.0` → one grid per monitor (per-monitor DPI; `"Argument must
    not contain duplicate dpis."` validation).
* `FullScreenGridProvider::run FUN_1401f8c10` → `FUN_1401f8960` = same loop over `this+0x50`
  (all monitors), each cell additionally tagged with a `u32 = 2` per-cell vector (slot metadata)
  (part_03:51750). Fallback message string: `"Falling back to Full Screen Grid Mode"`.
* Grid boxes become ordinary Targets (each target: box = cell rect?, slots = cells grouped per
  monitor via `FUN_1401f8030`), then the same §4 assignment applies — labels therefore follow the
  same convenience ordering (nearest-to-FG-window-centre cell gets `JJ`).

---

## 6. Target geometry

**What the box/target struct gives us (verified):**

* Target box: L/T/R/B at +0x08..+0x14; default target = **box centre**
  (`(right+left)/2, (bottom+top)/2` — the same expression used for the reference point and
  consistent with README "target point = centre of bbox by default"). `[INFERENCE for click path:
  the actual click point is derived from the selected slot, see below]`
* Every target carries `vector<Box> slots` at +0x38 (16-byte boxes). The distance sort in §4 pairs
  combos **per slot**, not per target — i.e. a target with several slots (multi-word box) can
  receive several hints; this is also what Dual/Multi/Path select and `PathSelect` operate on.

**Manipulation actions (schema verified; handler bodies partially traced):**

* Actions present: `SnapTargets`, `MoveTargets` (`strideX, strideY, percentX, percentY, direction`),
  `UndoHintSelection`, `ToggleHintPlacement`, `RevealOverlappedHints`, `RefreshHints`,
  `LockTargets`, `DualSelect/MultiSelect/PathSelect`, `Forward/Backward`
  (strings at `strings4.txt:40715-41140`; JSON parsers at part_02:41226 (`direction`),
  41737/41796 (`strideX`), 41875/41934 (`percentX`); `"Invalid direction: {}"` at 41373/43659).
* README:44-51 semantics: **arrows / `Shift+JIKL` → snap target to the edge of the bounding box**
  ("beginning or end of a word"); **number row `1`–`9` → position the target anywhere in between**.
  Binary-side this maps to `SnapTargets{direction}` for the former; the latter plausibly maps to
  `MoveTargets{direction, strideX/percentX}` with digit-derived stride/percent
  (`percentX = k·10 %`?) — **[INFERENCE]**, handler body not pinned (§9).
* A segment-interpolation helper exists: `FUN_1401fa640 @ 0x1401fa640` emits exactly **10 points**
  along a segment: endpoints plus t = 1/9 … 8/9 — consistent with digit-row subdivision of an edge
  into 10 stops `[INFERENCE]`. Its observed caller (`FUN_1401bf980`) builds a ±20 px back-and-forth
  scan line (animation/curve), so this is *circumstantial* for digits.
* Live target point state (session struct): **`session+0x184/+0x188` = target x/y, `+0x18c` = valid
  flag, `+0x180` = mode** — initialised to the **box centre** by shared-actions dispatcher
  `FUN_14019ba50` case 0x18: `*(i6+0x184) = (right + left)/2; *(i6+0x188) = (bottom + top)/2` from the
  last vector element (part_02:95083-95084), confirming centre-as-default. Action executors with
  direction/param payloads include `FUN_14019b2c0` (case 0x19; writes target-transform state at
  `session+0x16c..+0x17b`, variant tag `+0x174/+0x178`) and `FUN_14019e670(session+0x140, u32)`
  (case 0x1a); the concrete Snap/digit math is in this handler cluster (see Gaps 1).
* `hintPlacement` config enum (table `0x14027ee28`): **`0 = Centered` (default), `1 = BelowCenter`**;
  toggled live by `ToggleHintPlacement` which flips `config+0xd84` and `RedrawWindow`
  (`FUN_14019ba50` case 5, part_02:94586; setter `FUN_1400f0b80` writes `config+0x15c` + `+0xd84`).
  Semantics = where the 2-char label is drawn relative to the box (centre vs below) `[INFERENCE]`.
* Rounding: box/slot arithmetic is integer screen coordinates throughout; centre uses C-style
  truncating `/2` (`(l+r)/2`), grid uses `(int)` truncation of float cell offsets (§5); distance uses
  `(int)(dx*dx+dy*dy)`.

**FovMode → box space:** `Window` = fg-window DWM rect (validated; invalid → provider cached rect),
`Monitor` = monitor containing fg window, `AllMonitors` = full virtual desktop; Vision forces
AllMonitors for certain foreground windows (`FUN_140039640`, part_03:49643).

---

## 7. Rendering & fonts

* **Windows** (created via generic `FUN_1400fd900` RegisterClassExW, `DefWindowProcW`, class name
  passed in): wide-string classes present: `Neverclick`, `NeverclickLayer`,
  `NeverclickWindowBorder`, `NeverclickAnimationWindow`, `NeverclickAnimationOverlay`,
  `NeverclickAppBar`, plus message-only `NeverclickInputHookThread` / `NeverclickTaskThread`.
  The config-apply path recreates four windows named in logs: `"primary window"`,
  `"secondary window"`, `"animation window"`, `"window border window"`
  (part_01:77468–77507, `FUN_1400efb60`). Layered style: `SetLayeredWindowAttributes(hwnd,0,0xff,2)`
  (`FUN_1400ff550`, error "Failed to disable window transparency."); `WS_EX_LAYERED` /
  `WS_EX_NOREDIRECTIONBITMAP` referenced (part_00:52042/52105).
* **Text**: DirectWrite — `DWriteCreateFactory` (part_01:86913), `IDWriteFactory3 not available.`
  fallback, `nvr::LoadFontsAsync(IDWriteFactory&) → future<CustomFontCollection>` loads every file in
  `<exe>\fonts` (`local_318 = "fonts"` part_01:33173; error `Failed to load custom fonts: {}`).
  Bundled fonts (`extracted/app/fonts/`): DMSans-Regular, FiraMono-Regular, Geist-Regular,
  IBMPlexMono-Regular, Inter-Regular, JetBrainsMono-Regular, NunitoSans-Regular, Outfit-Regular,
  PlusJakartaSans-Regular, RobotoMono-Regular, SourceCodePro-Regular.
  Config keys `hintFontName` (string, default **"Inter"** — default literal in
  `FUN_1400ead30`-family defaults, part_00:76397/part_01:4097) and `hintFontSize` (numeric;
  defaults writer stores `0x1c = 28` adjacent to the font-name string — `[INFERENCE]` default 28).
  Errors: `Failed to set text alignment to center.`, `Failed to set paragraph alignment to center.`,
  `Failed to get text metrics.`, `Failed to prepare text layout.`, `Failed to render hints: {}`.
* **Hint Painter** (`FUN_140156190 @ 0x140156190`, logs `[Hint Painter] Layout cache: {} miss(es),
  {} stored (size {})`, `[Hint Painter] Unicode cache miss for {}/{} hint(s).`): per-font-size
  (key = `round(size*100)`) unordered_map of metrics, per-label trie cache keyed by the UTF-16
  label (`FUN_1401ffed0` conversion, `memcmp` radix lookup); cached layout entry = 0x24 bytes of
  glyph metrics (9 × u32). The layout cache lives on the coordinator (`[Hint Painter] …` printed from
  `FUN_…` around part_02:38161).
* **Render pipeline build** (`rebuildGraphicsPipeline`, `FUN_1400cc820`, part_01:46577+): reads
  `config+0x45` = **enableUppercaseHints** (bool, applied at part_01:77312) and font-size float
  (`(float)(i32)(config+0x48)`) and the alphabet at `config+0xf08`, then constructs two pipeline
  objects (timeout 1000 / `0x42100000`=36.f) via `FUN_1400b3d30`/`FUN_1400cdcb0`.
  → `enableUppercaseHints` affects only how labels are rasterised, not generation.
* **Box drawing**: `drawBoundingBoxes` (bool), `boundingBoxOpacity`, `hintBackgroundOpacity`,
  `drawHintBorders` config keys; glow via Direct2D (`Failed to create glow effect.`, `Failed to create
  Bitmap Render Target.`), DirectComposition (`DCompositionCreateDevice`, part_01:90019).
* **Detection-side knobs affecting boxes** (config): `detectionModel` enum (table `0x14027f540`:
  `0=Balanced (default), 1=Narrow, 2=UltraNarrow, 3=Wide`), `removeHallucinations` (bool,
  setter `FUN_1400f10d0` → config+0x174), `vision` sub-object (per-field settings incl.
  `checkCount`, `AdjustGap`, `g_edge_threshold`, `enablePerfectDesktopAndTaskbarIconDetection`),
  messages `No hints detected`, `Failed to render hints: {}`.

---

## 8. Config touchpoints (app-config.json)

Parsed/written by `FUN_1400a9550`-table code (part_01:15499–16060 parse, part_01:77300–77760 apply,
serializer at part_00:124099+). Enums decoded from .rdata tables:

| key | type | values (int = table order) | default |
|---|---|---|---|
| `keyCodes` | int[] scan codes | any of the 117-name position table `0x14027e270` (`Escape…IntlBackslash`) | 48-key priority list (§3.1); must be non-empty, unique, ≥2 enabled |
| `keyOverrides` | object pos→`On`/`Off` | table `0x14027e250 = {0:On, 1:Off}` | `{}` |
| `keyboardLayout` | string | layout id; `""`→ system layout | — |
| `keyboardLayoutPolicy` | enum `0x14027f7c8` | `0=Auto, 1=Manual` | `Manual` |
| `hintAssignment` | enum `0x14027f510` | `0=Random, 1=CenterFirst` | **`CenterFirst`** |
| `enableProgressiveHints` | bool | — | (parsed; reader not found) |
| `hintPlacement` | enum `0x14027ee28` | `0=Centered, 1=BelowCenter` | `Centered` (live flip `config+0xd84`) |
| `fovMode` | enum `0x14027f780` | `0=Window, 1=Monitor, 2=AllMonitors` | `AllMonitors` (live value at `**(config+0xfa8)`) |
| `enableUppercaseHints` | bool (`config+0x45`) | — | false `[INFERENCE]` |
| `hintFontName` / `hintFontSize` | string / number | bundled fonts | `"Inter"` / ~28 `[INFERENCE]` |
| `drawBoundingBoxes`, `boundingBoxOpacity`, `hintBackgroundOpacity`, `drawHintBorders` | bool/ints | render | — |
| `detectionModel` | enum `0x14027f540` | Balanced/Narrow/UltraNarrow/Wide | `Balanced` |
| `removeHallucinations` | bool | — | — |
| `vision` | object | detection tuning | — |
| `graphicsPreferencePolicy` | enum `0x14027f800` | LetNeverclickDecide/LetWindowsDecide/HighPerformance/PowerSaving/Manual | `LetNeverclickDecide` |
| `appBarTheme` / `compactAppBar` | enum(16)/bool | Graphite…Tanzanite | `Graphite` |

Non-config storage: hotkeys in `hotkey-config.json.gz` (`/hotkeys`, `/shared-keybinds` HTTP routes);
sticky hints under settings (`stickyHints`); HTTP API on loopback (`/key-position-to-key-code-map`,
`/key-code-to-unicode-map`). No plain-text config file claim in README refers to user-edited files.

**Sticky hints schema** (`FUN_1401dbce0 @ 0x1401dbce0`, part_03:27919):
`stickyHints | stickyButtons` (array), `anchor`, `autoClick` (bool), `persistence`
(`OnePress|Persistent`), `closeBehavior` (`CloseAfterPress|…`), `keyAssignment`
(`Automatic|…` — strings `Automatic`, plus manual), `keybinds`, `visionStrategy`
(`ScreenPosition | ImageRecognition`), `finalMousePosition` (`Stay|ReturnToOrigin`, `offset`),
plus `savedImages`, `matchAccuracy`, `maxDistance`, `clickOffset`, `origin`, `data`.
Re-anchoring: `ScreenPosition` = fixed saved point; `ImageRecognition` = re-find `savedImages` on
capture within `matchAccuracy`/`maxDistance` `[INFERENCE from schema + strings]`.
Auto key assignment regenerates combos via `FUN_140146350` (call sites part_02:86225 & 99229) and
reports `Assigned {} of {} hints. Not enough keys for the rest.` / `No hint keys are available for
automatic assignment.`. Dispatch: `nvr::sticky_hints_tool::Tool::dispatchStickyClick(AppContext, win::Key, Point)`
(RTTI part_02:83975+) with `final_mouse_position::ReturnToOrigin` handling.

---

## 9. Gaps (not resolved in this pass)

1. **Number-row & arrow handler bodies — CLOSED in `## Follow-up` §F2/F3** (executor formulas and
   default binds extracted; see there). Original investigation trail: Actions
   `SnapTargets`/`MoveTargets` and their JSON schema
   (`direction`, `strideX/Y`, `percentX/Y`) are located, and README/author describe the behaviour,
   but the key→handler function that computes the in-box point was not pinned. The executor cluster
   is `FUN_14019ba50` cases 0x11–0x1a (handlers `FUN_14019ad70`=CycleWindows, `FUN_14019b080`,
   `FUN_14019b2c0`, `FUN_14019e670`) operating on `session+0x16c..+0x18c`; next step = map case ids
   to action names via the id table beside `"SnapTargets"` (part_02:41207/41340, 53534/54287) and
   read the direction/percent math. Two hypotheses for digits: (a) `MoveTargets` with
   `percentX = k·10 %` of box width; (b) 10-stop interpolation (`FUN_1401fa640` emits exactly
   endpoints + t=i/9).
2. **`enableProgressiveHints` reader — NARROWED in `## Follow-up` §F5** (setter + behavioural gate
   identified; direct dereference not found). Written to `config+0x158`/`+0xd7d`
   (`FUN_1400f0b00`, part_01:76265) and mirrored through config copies; no dereference found.
   Possible effects: (a) allow depth growth while typing prefixes; (b) after typing the 1st char,
   regenerate level-2 hints for the surviving prefix. The `existing + new` term in
   `FUN_140146430` (`*(param_4+0x10) + param_3`) hints at incremental generation `[INFERENCE]`.
3. **Tag ≠ 0 pass-through** (`FUN_1401f4840`): only `CustomProvider` observed writing tag 1 —
   whether sticky/other modes also bypass assignment is unverified.
4. **`FullScreenGridProvider` AllMonitors fallback & `Vision` box postprocessing**
   (`FUN_1401f78a0`/`FUN_1401f7b60` filter/merge steps) not detailed.
5. **Clairvoyance box extraction** (`FUN_1400f7b90`, UIA element walk) — out of scope here.
6. Exact byte offsets for `hintFontSize`/`hintFontName` inside the config struct conflict between
   the serializer layout (string at +0x40, u32 at +0x48) and the defaults writer (+0x50 = 0x1c);
   key names are reliable, offsets are not.

Scratch artifacts kept under `notes/scratch-hints/`: `part_00..part_03` (3.5 MB line-numbered
splits of `ghidra/neverclick-decomp.c`, regenerable with
`split -b 3500000 -d -a 2 ghidra/neverclick-decomp.c notes/scratch-hints/part_` — cited as
`part_NN:LINE` throughout), `strings4.txt` (string dump with line numbers),
`fn_1401464f0.c` (combo generator extract), `rtti_map.py` (PE/RTTI mapper — class RTTI is absent
because the binary is compiled `/GR-` for app classes; only lambda `typeid`s exist).

---

## 10. Spec-ready statements

1. **Hint alphabet** = the enabled keys of `keyCodes` (scan codes), mapped through the active
   `keyboardLayout` to Unicode, keeping **only alphabetic chars** (unless force-enabled by
   `keyOverrides: On`), **preserving `keyCodes` order**; the order *is* the priority ranking.
   Fallbacks: all resolved keys → Latin `A–Z`. At least 2 keys must stay enabled.
2. **Depth**: smallest `d ∈ [1,4]` with `|A|^d ≥ #required slots` (2 in practice).
3. **Combo order** (deterministic given the alphabet): for `g = 1..|A|`, emit all depth-`d` combos
   whose maximum key index equals `g-1`, sorted ascending by Σ index; stop at the required count.
   Consequence: with the default alphabet the list starts `JJ, FJ, JF, FF, …`.
4. **Assignment (CenterFirst, default)**: reference = centre of the foreground window's DWM
   extended frame (fallback: centre of the first box); sort every hint slot ascending by
   integer squared distance to that reference; pair combo *i* with slot *i*. Uncovered slots
   (alphabet exhausted) are the farthest ones and get no hint.
5. **Assignment (Random)**: identical slot iteration in natural order, combos shuffled by MT19937.
6. **Cache**: coordinator caches the assigned layout keyed by the provider's cache-key; invalidated
   on provider/mode/fov/config changes (`FUN_1401f4030`).
7. **Grid cell size**: `spacing = 100px × dpiScale`; `cols = floor(W/spacing)`,
   `rows = floor(H/spacing)`; cells are `(W/cols)×(H/rows)` in float, truncated to int, row-major;
   per-monitor grids (per-monitor DPI) for AllMonitors/FullScreenGrid.
8. **FovMode**: `Window` → fg-window rect; `Monitor` → monitor of fg window; `AllMonitors` → virtual
   desktop; certain foreground windows force AllMonitors in Vision.
9. **Label rendering**: DirectWrite text layout, font = `hintFontName` (default "Inter", bundled
   fonts in `<exe>/fonts`) at `hintFontSize`, optional uppercase transform
   (`enableUppercaseHints`), placement `hintPlacement ∈ {Centered, BelowCenter}`;
   boxes drawn per `drawBoundingBoxes/boundingBoxOpacity/drawHintBorders`.
10. **Target**: default = centre of the hint's box/slot; `SnapTargets` snaps to box edges
    (arrows / `Shift+JIKL`); number row 1–9 subdivides (README), implementation traced to
    `MoveTargets{stride/percent}` schema — exact formula pending (§9.1).

---

## Follow-up: target geometry + progressive hints closure

### F1. Hint target state (shared by all tools)

Session→state pointer at `session+0x158` / `session+0x48` (`param_1[0x2b]`,
`*(param_1[0x2b] + 0x48)` — part_02:65873/65951, dispatcher `FUN_14019ba50` case 0xe part_02:94807).
State layout (stride constants verified):

| field | type | evidence |
|---|---|---|
| `state[0..2]` | `vector<Target>` stride **0x88** (136 B) | `(end-begin>>3)*-0x0f0f0f0f0f0f0f0f` = /17 → 136; slots `vector<Box>` at **+0x38..+0x40** (16 B/box); `f32 dpi_scale` at **+0x34**; per-slot **kind** `vector<i32>` at **+0x50** | `FUN_140198b20`/`FUN_1401e8fb0`/`FUN_1401981e0` |
| `state[3..5]` | `vector<PointRec>` stride **0x58** (88 B) per target | `uVar7*0x58 + state[3]` |
| PointRec | `point array @+0x00` (`vector<{i32 x,i32 y}>`, 8 B/slot), `bitset<u32> @+0x38` | part_02:92150-92230 |
| kind values | **2 = grid cell** (grid run fills every slot-kind with 2 — `FUN_1401f8960` part_03:51753 `*puVar16 = 2`), **3 = sticky-hint slot** (sticky auto-assign fills kinds with 3 — part_02:86208), others = vision slots | |

Bit semantics (derived from all three executors): **bit SET = point is still the untouched default
(box centre)**; any manipulation clears it; kind==2 (grid) always takes the "move" branch.

### F2. Number row → exact digit→point formula (Gap 1 CLOSED for digits)

**Default binds** (hint-tool shared keybinds builder `FUN_140175660 @ 0x140175660`, part_02:63267,
aggregated by `FUN_14015e970` for `GET /shared-keybinds/defaults` — handler `FUN_14008fcb0 @ 0x14008fcb0`):
`SnapTargets` binds (payload tag byte `0xe` = action id in the *deserialize* numbering; bind record =
`{modifier-head 4×i32, u32 VK @+0x10, payload {f32,f32} @+0x18/+0x1c, tag @+0x60/+0x78}` via
`FUN_1401683f0`):

| key (VK) | payload {percentX, percentY} | floats |
|---|---|---|
| `0x31` '1' | **{0.0, 0.5}** | — |
| `0x32` '2' | **{0.125, 0.5}** | 0x3e000000 |
| `0x33` '3' | {0.25, 0.5} | 0x3e800000 |
| `0x34` '4' | {0.375, 0.5} | 0x3ec00000 |
| `0x35` '5' | {0.5, 0.5} | 0x3f000000 |
| `0x36` '6' | {0.625, 0.5} | 0x3f200000 |
| `0x37` '7' | {0.75, 0.5} | 0x3f400000 |
| `0x38` '8' | {0.875, 0.5} | 0x3f600000 |
| `0x39` '9' | **{1.0, 0.5}** | 0x3f800000 |

→ **percentX = (digit−1)/8, percentY = 0.5; digit `0` is NOT bound.** Secondary binds with a
different modifier head (`uVar1..4 = {0,0,3,0}`): letters `a..i` → 3×3 anchor set
`a{0,1} b{0.5,1} c{1,1} / d{0,0.5} e{0.5,0.5} f{1,0.5} / g{0,0} h{0.5,0} i{1,0}` [same head as the
Shift+JIKL binds → most likely **Shift+A..I**, `+0x1000000000000000`-style modifier chord
[INFERRED: modifier slot-2 = Shift]].

**Executor** = `FUN_1401e8fb0 @ 0x1401e8fb0` (part_03:38571), reached from shared-actions dispatcher
`FUN_14019ba50` case **0xf** (action id 15 = SnapTargets in dispatch numbering; part_02:94818 passes
payload qwords as `float` params). For every target (stride 0x88) and every slot box
`{left@+0, top@+4, right@+8, bottom@+0xc}`:

```
x = (int)( (float)(right - left) * percentX + 0.5f ) + left      // round-half-up, integer px
y = (int)( (float)(bottom - top)  * percentY + 0.5f ) + top
point[target][slot] = {x, y}          // written into the per-slot point array
clear bit[target][slot]               // &= ~(1 << (slot & 31)) — point now custom
RedrawWindow(...)
```

Consequences:
* **Linear interpolation inside each slot box; NO glyph/word-boundary snapping and NO
  char-segmentation** — "position between letters" is pure percent-of-box.
* Digit k ⇒ `x = left + round(width·(k−1)/8)` at vertical centre: 1→left edge, 5→box centre,
  9→right edge (8 equal segments; the 9 stops are segment boundaries, not character cells).
* Applies to **all slots of all targets** in the state (dual/multi/path select and multi-slot
  targets included — the loop is unconditioned by selection mode).
* Horizontal-box assumption only in the sense that y is pinned to 0.5; vertical boxes get the same
  treatment (percentY fixed 0.5, percentX sweeps the width).
* Kind==2 (grid) slots are NOT skipped here (only the placement pass in F4 skips them).

### F3. Arrows / Shift+JIKL → SnapTargets-vs-MoveTargets semantics (Gap 1 CLOSED for arrows)

**Default binds** (same builder): payload tag `0xd` = **MoveTargets{i32 strideX, i32 strideY}**
(dispatch action id 14, case **0xe** in `FUN_14019ba50`, part_02:94807):

| bind set | modifier head (4×i32) | keys | stride |
|---|---|---|---|
| plain arrows | `{uVar5..8} = {0,0,0,0}` | VK `0x25/0x26/0x27/0x28` Left/Up/Right/Down | `{−4,0} {0,−4} {+4,0} {0,+4}` |
| plain JIKL | `{uVar1..4} = {0,0,3,0}` | VK `0x4a/0x49/0x4c/0x4b` J/I/L/K | `{−4,0} {0,−4} {+4,0} {0,+4}` |
| modified arrows | `{3,0,..}` | same four VKs | `{−2,0} {0,−2} {+2,0} {0,+2}` |
| modified JIKL | `{3,3,..}` | J/I/L/K | `{−2,0} {0,−2} {+2,0} {0,+2}` |

Head `{0,0,3,0}` on JIKL matches README's "`Shift` + J I L K" ⇒ **modifier slot 2 = Shift** (value 3)
[INFERRED]; the ±2 sets are a second chord [modifier encoding unresolved, GAP].

**Executor** = `FUN_140198b20 @ 0x140198b20` (part_02:92281), dispatcher case **0xe**, args
`(state, strideX, strideY)` (Ghidra elides 2nd/3rd args at the call site part_02:94807):

```
scale = target.dpi_scale (f32 @ target+0x34)
for each target (stride 0x88), each slot j:
    if (bit[target][j] == 0 || kind[target][j] == 2) {        # already customised, or grid cell
        point.x += (int)(strideX * scale)                     # MOVE by stride×DPI
        point.y += (int)(strideY * scale)
    } else {                                                  # first press: SNAP by stride SIGN
        x = (strideX < 0) ? slot.left
          : (strideX == 0) ? (slot.left+slot.right)/2
          : slot.right;                                       # strideX>0
        y analogous with slot.top / (top+bottom)/2 / slot.bottom
        point = {x, y}
    }
    clear bit[target][j]                                      # runs for BOTH branches
```

* **Direction map** (visual): stride **<0 → left/top edge midpoint; =0 → centre line;
  >0 → right/bottom edge** — arrow Left ⇒ `{slot.left, (top+bottom)/2}` (mid-height of the box —
  i.e. README's "beginning/end of a word" = the slot box edge, slots being CV text boxes / grid
  cells; no sub-box word search exists at this layer [evidence: only slot boxes are consulted]).
* **First press snaps regardless of stride magnitude** (bit set ⇒ snap branch; magnitude 4 vs 2 only
  matters for later presses). Subsequent presses nudge by `stride × dpi_scale` px (4 or 2 px × DPI)
  with **no clamp back into the box** (no clamp code present).
* Grid cells (kind 2) never snap: every press adds `stride×scale` — README's grid behaviour.
* Loop covers all targets/slots ⇒ dual/multi/path selections all adjust.

### F4. Default-point placement pass (enum at `state+0x74`, gate byte `state+0x78`)

`FUN_1401981e0 @ 0x1401981e0` (part_02:91853; called on every layout change — part_02:66012,
82841, 85498, 91507, 100664):

```
pass 1 (always): for every slot: point = {(left+right)/2, (bottom+top)/2}; SET bit
pass 2 (only if *(char*)(state+0x78) != 0 and enum74 = *(i32*)(state+0x74) != 0),
        skipping slots with kind==2:
   enum 1 -> {slot.left,  (top+bottom)/2}   bit CLEARED
   enum 2 -> {slot.right, (top+bottom)/2}   bit CLEARED
   enum 3 -> {(left+right)/2, slot.top}     bit CLEARED
   enum 4 -> {(left+right)/2, slot.bottom}  bit CLEARED
   enum 5 -> {slot.right - (int)(scale * -100.0), (top+bottom)/2}  # = right + round(scale*100)
```

Enum values 1–5 = {left,right,top,bottom, right+100px×dpi}. This does **not** match the persisted
`hintPlacement` config enum `{0=Centered,1=BelowCenter}` (table `0x14027ee28`) — identity of
`state+0x74` unresolved: could be an internal placement/anchor strategy with more values than the
config exposes (value 5 echoes the string `RightEdge100px`, strings4.txt:41124) [GAP — do not
conflate with `hintPlacement` without a writer trace].

### F5. `enableProgressiveHints` (Gap 2 — reader NOT found; behaviour bounded)

* Written only by setter `FUN_1400f0b00 @ 0x1400f0b00` (part_01:76254): `config+0x158` (byte) and
  mirror `config+0xd7d`; apply-path part_01:77748; parse part_01:15826; serializer
  part_00:124194. `config` dword-group `+0xd70..+0xd7c` is memcpy'd by the config copy ctor
  (part_00:6513-6519). **No direct dereference of `+0x158`/`+0xd7d` exists in the decomp** —
  the consumer must alias the pointer (or lives in a memcpy'd view) — grep-undiscoverable.
* **Prime suspect (behavioural gate)** — session byte `*(session + 0x154)` in
  `FUN_140177d70 @ 0x140177d70` (part_02:65631+, event path at part_02:66140-66160):
  ```
  on event 0x510 (hint-layout request):
    if (eventTarget == session.hintTarget &&
        (byte(session+0x154) == 0 || (state.depth < 1 && state has no slots)))
        -> re-run FUN_1401f26a0 (full re-assignment / re-layout)
    else -> keep existing layout (FUN_1401a0110/FUN_140095c10 update path)
  ```
  i.e. byte==0 ⇒ **re-layout on every request** (labels regenerate while typing = progressive),
  byte==1 ⇒ re-layout **only when no hints exist yet** (stable labels).
  Whether `session+0x154` mirrors `config+0x158` is **[INFERRED]** (offset differs; sessions are
  built from config at creation). The alternative bounded effect is in the render label generator
  (next bullet).
* **Label generator** `FUN_1400b3d30 @ 0x1400b3d30` (part_01:25251; called from
  `rebuildGraphicsPipeline` part_01:47449/47465 with `(out, config+0xf08 alphabet, config+0x7b0,
  …)`; pipeline slots `config+0xc38` / `config+0xcb0`):
  ```
  if (budget != 0):                                  # budget = 1000 (pipeline 1) / 0 (pipeline 2)
      maxLen = FUN_1401462f0(alphabet, budget)       # depth(N): min d≤4 : |A|^d ≥ N
      for n in 1 .. min(3, maxLen):
          count = min(FUN_1401462d0(alphabet, n), budget)   # FUN_1401462d0 = |A|^n
          combos = FUN_140146350(alphabet, count)    # §3 generator (same order)
          append
      for each label: FUN_1401142a0(...)             # wstring
      if (param_9 != 0) towupper(label)              # param_9 = enableUppercaseHints ✓ CONSUMED HERE
  ```
  ⇒ render/typing space includes labels of lengths **1..min(3, depth(budget))** (with budget 1000
  and |A|=26 ⇒ n=1:26, n=2:676, n=3:1000 labels pre-cached for the Hint Painter trie).
  `enableUppercaseHints` **confirmed** as `param_9` → `towupper` per label (part_01:25455).
  Whether `enableProgressiveHints` alters this budget/length set (e.g. budget 0 ⇒ 2-char only) is
  **[INFERRED]** — the two pipeline call sites differ only visibly in budget/`local_190`
  (`1000` vs `0`, `local_160` vs `0`) at the call site (part_01:47449/47465).

### F6. Enter / Esc / Backspace mid-hint (new)

Action-id map (serializer/deserializer switches in `FUN_14016a7e0`/`FUN_14016b910`, part_02:52904+
and name-parser `FUN_14016f9c0`/`FUN_140172470`):
`1=Clear, 2=UndoHintSelection, 3≈Exit(len-4 name at DAT_140287704), 4=RevealOverlappedHints,
5=ToggleHintPlacement, 6=GridMode, 7=ClairvoyanceMode, 8=VisionMode, 9=RefreshHints,
10=ToggleFieldOfVision, 0xc=SetFieldOfVision | ShiftFocus (off-by-one between the two switches),
0xd/0xe=ShiftFocus|MoveTargets… 0xe/0xf=MoveTargets|SnapTargets (dispatch numbering vs
deserialiser numbering differ by one ≥0xc; `FinishSelection=0x15` in deserialiser,
parser `FUN_140175086` region part_02:62812).`

* **Esc** (VK `0x1b`): two default binds in the hint-tool builder (part_02:64043-64052) with payload
  **tag 2 = `UndoHintSelection`** (heads differ ⇒ plain + one modifier variant). So Esc undoes the
  typed prefix/selection (falls back through history); `Clear` (id 1) is the separate hard-clear.
* **Backspace** (VK `0x08`): a default bind record with key 8 exists in the same builder
  (part_02:786-788 region: `local_2b78 = 8`), payload tag ambiguous in the stack layout —
  **action not pinned [GAP]**; given `UndoHintSelection` (id 2) is Esc's bind and there is no
  separate "pop-prefix" action name, prefix-pop is most plausibly handled inside the session key
  dispatch (single-char prefix ⇒ nothing to pop; 2-char ⇒ pop one) **[INFERRED]**.
* **Enter**: `FinishSelection` (deserialiser id 0x15, paramless — `FUN_140166a90`,
  part_02:62812); no shared-keybind default record with VK `0x0d` was found in the tool builder —
  Enter is presumably a per-tool hotkey from `hotkey-config` defaults **[GAP]**. It finishes
  Dual/Multi/Path selections (strings "Select two hints to execute." etc.).
* Layout-stability: after any hint-layout request event (`0x510`) the session re-runs
  `FUN_1401f26a0` only per the `session+0x154` policy (F5) — i.e. typing either regenerates or
  preserves labels depending on that flag.

### F7. Corrections/confirmations vs the main report

* Dispatcher numbering for the geometry actions confirmed by executors: **case 0xe = MoveTargets →
  `FUN_140198b20`, case 0xf = SnapTargets → `FUN_1401e8fb0`** (both consistent with the serializer
  switch `0xe=MoveTargets, 0xf=SnapTargets`), so the earlier "case 0xb/0xc = fov" readings belong
  to `SetFieldOfVision`/`ToggleFieldOfVision` (ids 0xb/0xc), not to snapping.
* The four shared-keybind default builders map to four tool classes
  (`FUN_140175660` = basic/hint mouse tool [digits/JIKL/arrows], `FUN_140181cb0` = ?,
  `FUN_140184220` = window-move-style tool with stride tiers ±200/±50/±10 and direction
  payloads {0..3} for `MoveWindowToEdge`-family, `FUN_1401835e0` = ?) — the ±200/±50/±10 strides in
  the earlier draft belong to a **window** tool, NOT to hint targeting.
* `direction` enum `{0=Left,1=Right,2=Up,3=Down}` (table `0x140288370`) belongs to
  ShiftFocus/MoveWindowToEdge/MoveWindowToMonitor — **not** to Snap/MoveTargets (which take
  percent/stride payloads). Arrow "direction" for hint targeting is expressed purely by the
  **sign** of `strideX/strideY` (F3).

### F8. Open after follow-up (was Gap 1/2, now narrowed)

1. Modifier-head encoding {m0..m3} values (which slot = Shift/Ctrl/Alt/Win; what {3,3} and {3,0}
   chords mean) — Shift-ness of JIKL/a–i binds is INFERRED from README.
2. `state+0x74/+0x78` placement-enum writer (F4) and its relation (if any) to `hintPlacement`.
3. Direct reader of `enableProgressiveHints` (config+0x158/+0xd7d); session+0x154 link is
   INFERRED from `FUN_140177d70` semantics.
4. Backspace (VK 8) bind target action; Enter/`FinishSelection` default key source
   (hotkey-config, not shared keybinds).
5. Which of the two float-pipeline label sets (`config+0xc38` vs `+0xcb0`) corresponds to
   progressive on/off.
