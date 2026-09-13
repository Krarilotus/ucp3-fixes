# Native unit lifecycle and idle tunneler corrections (draft)

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

The same unit module now contains an independently switchable idle-tunneler
response candidate. Native tunneler states5/6 omit the melee-response flag
which ordinary melee handlers set. The existing enemy-notice routine therefore
skips the group's stance when choosing whether to pursue a nearby enemy. Set
that flag in the two idle branches, then execute the displaced original
instruction. Group stance, assignment, target selection and recruitment remain
owned by the original game and AIC. This is not a new AIV slot or a change to
AI Swapper's native initial-defense placement.

## Reuse and binding review

| Capability | Inspected implementation | Decision |
| --- | --- | --- |
| Discovery and patching | Released UCP3.0.7 core.lua, data.cache.AOB, RPS1.5.1; existing AIV behavior caller | Use core.AOBScan, scanForAOB, insertCode, itob and writeCodeByte. No custom scanner, cache, allocator or hook bridge. |
| Crew tracking | Original SHC/Extreme unit pool and eight engine behavior handlers | Already preserves mounted engineer records. Retain native ownership and cleanup rather than rebuilding it. |
| General unit API | AI Swapper startup, AIC native-context/native-group-actions, Mapstate, running-units, Legacy ports, this repository's AIV behavior | None exports a general human/AI crew lifecycle API. AIC's group adapter is internal and its policy hooks remain its owner. |
| Unique discovery | Stock scanner and held framework PR149/RPS PR16 | Do not depend on or publish the held API proposals. Dispatch and fire use stock uniqueness checks. Each engine guard must belong to its independently decoded native handler and be unique in that interval. Measure startup cost before release. |
| Fire damage | Original health/attribution calculation and fatal classification; AIC PR17 at 28fd320, combat-native.lua entry observer | Retain the original damage owner. Extend only its fatal classification, using an independent interior context; do not detour or duplicate the function. AIC's five-byte entry observer remains untouched. Full composition acceptance is pending. |
| Idle melee response | Released AIC Loader1.1.2 at b494248, AI: AIV Troop Behaviour0.2.3 at b20dad6, AI Swapper at26e1b1f and original unit dispatch/notice callers | These configuration/placement owners expose no common idle-response capability. Reuse the existing unit module's decoded handler ownership, extracted to unit-handlers.lua; do not copy AIC group/recruitment handling. Restore the native eligibility field inside type5's own idle branches. |

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
This crew gate changes only the first death frame. The separate tunneler option
below intentionally changes live idle response eligibility.

Fire discovery identifies the fatal-health guard through the complete existing
dying initialization and thiscall RET12. The ten overwritten bytes contain the
type comparison and cycle reset. The trampoline extends the comparison to the
eight engine types, preserves registers and the displaced reset, and supplies
ZF to the existing conditional branch. It does not change the native damage
calculation or attribution. The original lord behavior is retained. Nine
framework allocations total217 bytes;66 original bytes are patched. All sites
are checked before any write and checked again when installing.

The tunneler binding derives the unit-record root from the type5 handler's
owner load and validates the native stride/prologue and three idle operands.
Each complete state5/6 signature must be unique within the independently
decoded handler. Two insertCode calls each retain a complete six-byte MOV and
add a word write at verified Unit+0x3FC; they preserve registers, flags and
stack. Two framework allocations total40 bytes, with12 original bytes patched.
There is no call, frame hook, Lua scan or extra persistent record. Both options
are prepared before either installs; all OFF performs no discovery or writes.
The shared resolver extraction retains the existing crew payloads unchanged.

Research addresses, not runtime bindings: SHC54F04E/54F153 and
Extreme54F46E/54F573. The next native enemy-notice consumer is
SHC54A7B0/Extreme54ABD0: eligibility gate at+0x52, group stance load at+0xAD.
The central update clears eligibility before the type handler sets it for the
following update. Active-order transitions must therefore be tested explicitly,
not inferred solely from the idle patch locations. The exact ownership proposal
was [shared with AIC PR17](https://github.com/UnofficialCrusaderPatch/extension-aic-tactics/pull/17#issuecomment-5655323602).
AIC head28fd320 remained unchanged at the13September21:13 refresh.

## Acceptance status

Idle response:42 paired original-instruction cases across all six fixture
identities execute original spawn, role20 assignment, type handler and enemy
notice without callee stubs. Idle5/6 now reach native stance handling like
swordsman1/3; working4/7/9 controls retain their complete unit record. The only
expected idle differences are eligibility and the original no-enemy retry.
These are controlled states, not a nearby-threat gameplay reproduction.
Actual framework binding tests cover occupied/missing/ambiguous/layout changes,
changed-after-prepare rejection, repeat enable and both independent OFF paths.
The shared resolver also passes the66 existing crew binding checks unchanged.

Polish SHC, UCP3.0.7, unsigned candidate ZIP
`91bab0f7a7004757123cab8483bc7e5db12e9f2303f25610f98fb50e73f445e2`:
the same preserved `temixedadvused` save was loaded with crew OFF and response
OFF/ON, alongside signed AI Swapper26e1b1f and published AIV0.2.3. OFF107 samples
over40.03s (ticks45659..58282) had340 idle records with eligibility0. ON112
samples over40.18s (45067..57880) had387 idle records with eligibility1 and one
transient0. Both runs retained the same ten tunneler identities/roles and
continued through native tunneling states7/8/9. No tunneler target was observed;
this proves live flag installation/load compatibility, not nearby-threat
pursuit, active-order safety under threat or main-attack-slot acceptance.
The fixture contains old role15 tunnelers and is not the role20 reproduction.
Both processes closed normally; the desktop was released21:12:24CEST and the
private modules/config restored. No save was overwritten. The one source edit
after this ZIP only changes signature interval length validation; a final ZIP
must be rebuilt. Native Extreme response, controlled threats/stances, active
order transitions, save/reload and performance acceptance remain outstanding.

The new response option defaults ON under the existing AI / Fixes category and
has all nine option catalogs. GUI verification, runtime-error localization,
root descriptions and collection/store integration remain unfinished. The
signed AI Swapper preview does not contain this unit module.

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

Polish Extreme gameplay at92f838a used unsigned ZIP
`962151a1cd2985bd69d71ccb0beccf1005add711e5dc791956f735ebb0f2a9dc`
and unchanged executable
`e7e82625a39d3840bf44a84456967eeecafe7ec9d716afa67f1856ad59a9d460`.
The preserved `teextbaseline767signed7` save loaded successfully.148 read-only
samples over50.22s covered ticks7246..38842 and29 engine identities.17 catapult
or fire-ballista deaths had two valid living crew before death; none of those34
engineers remained alive in the first later sample without the original engine.
Death actions111/113/114 were observed, but the damage source was not traced;
this is not specific fire-path acceptance or a matched unmodified Extreme
control. The full native run also does not establish casualty totals. Enable
through bootstrap took4.728s, requiring further startup-performance work.
The game closed normally, PID27040 absence was checked, the desktop released
19:27:52CEST and the private fixture config restored. No save was overwritten.

A separate original-command regression now demonstrates that normal unman
validates the engine UID but not the individual crew UIDs. On all six fixtures,
reusing crew slot1300 for a different lord UID still causes29 writes, including
fade action109 and relocation. The entire original command and its callees
return with the correct ABI; valid injured engineers retain UID and health.
This is instruction evidence, not gameplay or historical-incident attribution.
The exact proposed instruction17 context was shared with AIC before production
changes in [the owner handoff](https://github.com/UnofficialCrusaderPatch/extension-aic-tactics/pull/17#issuecomment-5654832850).
No unman correction is included yet. The tower deployment's separate UID check
does not establish safety for the normal exit-equipment command.

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
python tests/check_tunneler_bindings.py --framework code.zip --fixtures matrix.json
python tests/check_tunneler_native.py --framework code.zip --fixtures matrix.json --baseline --report baseline.json
python tests/check_tunneler_native.py --framework code.zip --fixtures matrix.json --compare baseline.json
python -m unittest discover -s tests -p test_packaging.py -v
```
