# Fixed Engineers 0.2.0: focused test candidate

This branch replaces the engineer and general equipment corrections from Unit
Behaviour Fixes. It contains no tunneler patch, recruitment census,
starting-troop configuration, siege planner or extra native tracking array.

Mounted engineers already retain native unit records, IDs/UIDs and health. The
eight original engine handlers can skip their crew death cleanup when animation
advances before dispatch. Fatal fire can take a generic corpse-conversion path
which also bypasses that cleanup. The exit-equipment command checks the engine's
identity but can mutate a recycled crew slot without checking its stored UID.

The existing corrections retain native cleanup/dismount behaviour: admit the
first death update after animation advancement, route fatal engine fire through
native dying state, and reject stale/out-of-pool crew references before mutation.
Valid dismounts retain identity, health and native placement. Native payloads in
`crew.lua`, `unman.lua`, `unit-handlers.lua` match source `a29738a`, apart from the
module name in diagnostics. The separate `siege-targeting.lua` correction comes
from siege-target-stop PR #3 (`29eadc2`): catapults and trebuchets receiving a
direct attack order against an enemy unit call the existing native path cleanup
once, then continue through the original aim/reload/fire state machine. Ground,
wall and other unit orders keep their original path. All three corrections
resolve and preflight before installation.

## Ownership and runtime integration

| Capability | Reused owner / decision |
|---|---|
| Memory, patch byte compiler and initialization | UCP 3.0.7 core/cache (`77c6acc`), exercised by `tests/crew_framework.py`; no private patch manager |
| Engine update handlers | Native dispatch table decoded from UCP AOB context; handler-bounded signatures and layout validation |
| Fatal fire | Original damage/calculation/attribution; interior classification correction preserves the AIC entry observer |
| Dismount | Original synchronized group command, instruction17; validate ID/UID then retain original loop and placement |
| Direct siege attack | Original synchronized attack dispatcher and decoded native stop function; preserve the original aiming and projectile owner |
| Variant capacity | Framework `data.version.isExtreme()` and independently checked native context; no fixed executable bindings |
| AI recruitment/group policies | AIC Tactics PR12/16/17, untouched; no policy code copied |
| Tunnelers | ImprovedTunnelers for behaviour; AI Swapper1.5.0 for starting counts/native initialization; neither required here |

The existing module-local handler resolver is needed for the eight engine
handlers. It resolves once at initialization, checks context and rejects occupied
or ambiguous sites. Research addresses/hashes appear only in fixture tests.
Crew correction allocates217 bytes and replaces66 original bytes; dismount
allocates83 bytes and replaces7; target stop allocates27 bytes and replaces7.
No per-tick Lua callback, scan or census. The target-stop site belongs to the
tribe-command dispatcher, outside the bounded unit-handler resolver; it uses
`core.AOBScan`, decoded branch/call targets, `core.callTo` and `core.insertCode`
from the same framework version. PR #3's separate branch remains untouched.

## Setting, migration and testing

`fixed-engineers.crew_lifecycle` and `fixed-engineers.siege_target_stop` both
default to true in runtime and options, with independent OFF controls under
the established localized **Bugfixes** category. All nine frontend option and
description catalogs are included; root description equals English. Human
translation review and installed-GUI checks are pending.

Disable the old Unit Behaviour Fixes module when selecting this replacement.
If `unit-behaviour-fixes.crew_lifecycle` was explicitly OFF, set the new control
OFF too: the rename cannot automatically migrate another module's configuration.
Do not leave both native patch owners selected. Existing historical packages
remain unchanged. Starting troops still default to zero unless authored/configured.

Short single-player check: crew and damage an engine, dismount surviving
engineers and check health/identity; destroy a crewed engine and check for hidden
survivors. Move a manned catapult/trebuchet, click an enemy unit in another
direction and check that the old path stops while normal aiming/firing continues.
Restart with each switch OFF to compare. Save/load, repeated dismount, fire deaths,
SHC/Extreme composition and the new package's GUI/gameplay still need acceptance;
no multiplayer test is claimed or required from this worker.

The 35 repository tests pass. Six-fixture checks cover 66 crew binding/preflight
cases, dismount instruction and UID cases, 1,392 original/modified fire cases,
and 144 paired target-stop commands. These are native instruction checks, not
an in-game run of this combined package. Prior limited crew/fire gameplay
evidence belongs to the old source.
Engineer role-quota accounting and newly requested siege placement, harassment,
capacity/resource policies are not included or advertised as fixed.

Historical context: [UCP2 PR #658](https://github.com/UnofficialCrusaderPatch/UnofficialCrusaderPatch2/pull/658)
added a one-line ghost-engineer byte patch and described incomplete AI coverage;
[PR #951](https://github.com/UnofficialCrusaderPatch/UnofficialCrusaderPatch2/pull/951)
reverted it after reports of disappearing AI lords. Current [issue #79](https://github.com/UnofficialCrusaderPatch/UnofficialCrusaderPatch/issues/79)
records its unsafe index/address/record-clearing concerns. None of those bytes
are reused as a production binding here.
