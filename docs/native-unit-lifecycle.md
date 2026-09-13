# Native unit lifecycle correction (draft)

This branch addresses [UCP issue79](https://github.com/UnofficialCrusaderPatch/UnofficialCrusaderPatch/issues/79).
The initial implementation preserves the eight original engine handlers' crew
ID/UID validation and casualty logic. It changes their animation-cycle gate so
that advancement before the first death dispatch cannot skip cleanup. Fatal
fire damage now enters the existing dying initialization for siege engines
instead of converting them to corpses before their crew handlers run. No second
crew array, native deletion service, census, DLL bridge or patch manager is added.

The supporting unit behavior surface is proposed in
[the ownership handoff](https://github.com/UnofficialCrusaderPatch/UnofficialCrusaderPatch/issues/79#issuecomment-5654553608).
The existing AIV and hop-farm modules are unchanged. No collection manifest or
store recipe is added. AIC PR17 retains recruitment/census/moat/reserve/group
ownership; the active AIC branch is unchanged. Final integration is pending.

## Reuse and binding review

| Capability | Inspected implementation | Decision |
| --- | --- | --- |
| Discovery and patching | Released UCP3.0.7 core.lua, data.cache.AOB, RPS1.5.1; existing AIV behavior caller | Use core.AOBScan, scanForAOB, insertCode, itob and writeCodeByte. No custom scanner, cache, allocator or hook bridge. |
| Crew tracking | Original SHC/Extreme unit pool and eight engine behavior handlers | Already preserves mounted engineer records. Retain native ownership and cleanup rather than rebuilding it. |
| General unit API | AI Swapper startup, AIC native-context/native-group-actions, Mapstate, running-units, Legacy ports, this repository's AIV behavior | None exports a general human/AI crew lifecycle API. AIC's group adapter is internal and its policy hooks remain its owner. |
| Unique discovery | Stock scanner and held framework PR149/RPS PR16 | Do not depend on or publish the held API proposals. Dispatch and fire use stock uniqueness checks. Each engine guard must belong to its independently decoded native handler and be unique in that interval. Measure startup cost before release. |
| Fire damage | Original health/attribution calculation and fatal classification; AIC PR17 at 28fd320, combat-native.lua entry observer | Retain the original damage owner. Extend only its fatal classification, using an independent interior context; do not detour or duplicate the function. AIC's five-byte entry observer remains untouched. Full composition acceptance is pending. |

Preparation occurs before enable-time writes. Dispatch context includes the
16-bit type load, original handler-table operand, indirect call and current-unit
reload/stride. Handler table entries establish ownership intervals independently
of guard matches. Each guard identifies the cycle comparison, conditional
branch and already-attributed predicate. Decoded cycle/attribution roots must
agree across all eight handlers. Absolute game addresses and executable hashes
are not production bindings. The native unit stride and verified record offsets
are layout constants, not addresses.

The patch displaces one complete six-byte comparison. Its trampoline preserves
EDX and stack balance and intentionally supplies flags to the original branch,
whose destination is retained. There is no native function call or per-frame
Lua callback. Existing ID/UID cleanup and casualty bodies remain untouched.
Only the first death-frame guard changes; live unit behavior is unchanged.

Fire discovery identifies the fatal-health guard through the complete existing
dying initialization and thiscall RET12. The ten overwritten bytes contain the
type comparison and cycle reset. The trampoline extends the comparison to the
eight engine types, preserves registers and the displaced reset, and supplies
ZF to the existing conditional branch. It does not change the native damage
calculation or attribution. The original lord behavior is retained. Nine
framework allocations total217 bytes;66 original bytes are patched. All sites
are checked before any write and checked again when installing.

## Acceptance status

The actual source through released UCP3.0.7 core/cache/byte compiler passes
1,440 original-instruction cases across local, official EFIGS and Polish
SHC/Extreme fixtures. These cover both native animation timings, the generic
death-action reset, partial crews, a reused slot occupied by a different lord
UID, the existing already-attributed predicate and a second complete update
without repeated crew-state writes. Native callees are not stubbed. Another
66 binding checks reject missing/occupied, duplicate and changed-layout cases
before writes, including changes between preparation and installation, and
verify discovery remains independent of a patched fire entry. Another1,392
paired whole-function fire comparisons cover all80 unit types and selected
damage-owner/half-damage combinations. Non-engine and nonfatal controls retain
the original unit record, native write sequence and return registers. Fatal
engine cases enter dying state and the native engine cleanup on the following
update. These remain synthetic-state instruction tests, not gameplay acceptance.

Controlled Polish SHC gameplay, original executable SHA256
`2aab6b3da99148b0796bd00a92b4b19db7548d1e2c50fa4372035f716fd33cab`,
UCP3.0.7 and the unsigned development ZIP
`e8b889ce3950309c33d813139146ce9412251ff2ae83788e2cf6fad960bc663e`:
loaded preserved `temixedadvused`, collected 149 read-only samples over 50.20s,
ticks45924..61758. Mangonel232/UID5883 retained both engineers123/UID6033 and
229/UID5859 before death. At stable tick58884 it had health0/dying1/action111;
both crew slots had been released and reused by new peasants with different
UIDs. The engine was absent by59094..59100. This corrects the earlier unmodified
run's persistent mounted crew in this one scenario; combat timing differs after
earlier corrected deaths. It does not establish every damage path or the exact
first cleanup instruction. The original save was not overwritten.

Module enable to bootstrap completion took 1.413s, including native binding and
patch setup. There is no per-frame Lua callback or census. Final controlled
composition/performance acceptance remains pending. The native process28168
closed normally, its absence was checked and the desktop released18:51:34CEST.
The private fixture configuration was restored. This ZIP tested only the timing
correction at commit586d5c9. Later fire and description/localization changes are
not represented by this ZIP hash. Native fire gameplay and complete casualty
accounting remain unverified; the component comparisons do not discharge them.

Remaining: corrected native gameplay, live first-transition trace, damage and
casualty matrix, partial/stale crew, dismount/remount identity and health,
save/load/offline restoration, AI lifecycle/composition, supported variants,
performance, full option/localization/GUI/package work and normal PR/release
review. Multiplayer testing belongs to players. This is not a finished release
or the downloadable AI Swapper starting-troops test package.

The draft option and descriptions cover the nine frontend languages and the
switch defaults to true. GUI placement/default/persistence, translation review,
runtime error localization and collection ownership still require acceptance.
The repository packager now uses stored ZIP entries like the framework/store
packager, preserving its existing explicit locale-directory entries.

## Reproducing component checks

Supply a licensed executable manifest (JSON array with `path` and `sha256`) and
the released framework's `code.zip`. No game binary is included here.

```text
python tests/check_crew_bindings.py --framework code.zip --fixtures matrix.json
python tests/check_crew_native.py --framework code.zip --fixtures matrix.json --baseline
python tests/check_crew_native.py --framework code.zip --fixtures matrix.json
python tests/check_crew_native.py --framework code.zip --fixtures matrix.json --crew-mode partial
python tests/check_crew_native.py --framework code.zip --fixtures matrix.json --crew-mode reused-slot
python tests/check_crew_native.py --framework code.zip --fixtures matrix.json --crew-mode already-attributed
python tests/check_crew_native.py --framework code.zip --fixtures matrix.json --reset-death-action
python tests/check_crew_fire.py --framework code.zip --fixtures matrix.json
python -m unittest discover -s tests -p test_packaging.py -v
```
