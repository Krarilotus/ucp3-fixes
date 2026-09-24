# Fixed Engineers: focused test candidate

Fresh branch from main `b20dad6`. This replaces the engineer portion of
Unit Behaviour Fixes; it contains no tunneler patch, recruitment census,
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
module name in diagnostics. Both corrections preflight before installation.

## Ownership and runtime integration

| Capability | Reused owner / decision |
|---|---|
| Memory, patch byte compiler and initialization | UCP 3.0.7 core/cache (`77c6acc`), exercised by `tests/crew_framework.py`; no private patch manager |
| Engine update handlers | Native dispatch table decoded from UCP AOB context; handler-bounded signatures and layout validation |
| Fatal fire | Original damage/calculation/attribution; interior classification correction preserves the AIC entry observer |
| Dismount | Original synchronized group command, instruction17; validate ID/UID then retain original loop and placement |
| Variant capacity | Framework `data.version.isExtreme()` and independently checked native context; no fixed executable bindings |
| AI recruitment/group policies | AIC Tactics PR12/16/17, untouched; no policy code copied |
| Tunnelers | ImprovedTunnelers for behaviour; AI Swapper1.5.0 for starting counts/native initialization; neither required here |

The existing module-local handler resolver is needed for the eight engine
handlers. It resolves once at initialization, checks context and rejects occupied
or ambiguous sites. Research addresses/hashes appear only in fixture tests.
Crew correction allocates217 bytes and replaces66 original bytes; dismount
allocates83 bytes and replaces7. No per-tick Lua callback, scan or census.

## Setting, migration and testing

`fixed-engineers.crew_lifecycle` defaults to true in runtime and options. Its
single control remains under the established localized **Bugfixes** category.
All nine frontend option and description catalogs are included; root description
equals English. Human translation review and new installed-GUI checks are pending.

Disable the old Unit Behaviour Fixes module when selecting this replacement.
If `unit-behaviour-fixes.crew_lifecycle` was explicitly OFF, set the new control
OFF too: the rename cannot automatically migrate another module's configuration.
Do not leave both native patch owners selected. Existing historical packages
remain unchanged. Starting troops still default to zero unless authored/configured.

Short single-player check: crew and damage an engine, dismount surviving
engineers and check health/identity; destroy a crewed engine and check for hidden
survivors. Restart with the switch OFF to compare. Save/load, repeated dismount,
fire deaths, SHC/Extreme composition and the new package's GUI/gameplay still need
acceptance; no multiplayer test is claimed or required from this worker.

Portable entry/default/packaging checks and six-fixture binding/dismount instruction
checks cover this split. Prior crew/fire instruction and limited gameplay evidence
belongs to the old source; it is not an in-game run of this renamed package.
Engineer role-quota accounting and newly requested siege placement, harassment,
capacity/resource policies are not included or advertised as fixed.
