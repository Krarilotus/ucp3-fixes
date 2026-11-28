# Fixed Engineers

Fixed Engineers replaces the engineer and general equipment corrections from Unit
Behaviour Fixes. It contains no tunneler patch, recruitment census,
starting-troop configuration, siege planner or extra native tracking array.

Mounted engineers already retain native unit records, IDs/UIDs and health. The
eight original engine handlers can skip their crew death cleanup when animation
advances before dispatch. Fatal fire can take a generic corpse-conversion path
which also bypasses that cleanup. The exit-equipment command checks the engine's
identity but can mutate a recycled crew slot without checking its stored UID.

The corrections retain native cleanup/dismount behaviour: admit the first death
update after animation advancement, route fatal engine fire through native dying
state, and reject stale/out-of-pool crew references before mutation. Valid
dismounts retain identity, health and native placement. Catapults and trebuchets
receiving a direct attack order against an enemy unit call the existing native
path cleanup once, then continue through the original aim/reload/fire state
machine. Ground, wall and other unit orders keep their original path. All three
corrections resolve and preflight before installation.

## Ownership and runtime integration

| Capability | Reused owner / decision |
|---|---|
| Memory, patch byte compiler and initialization | UCP 3.0.7 core/cache (`77c6acc`), exercised by `tests/crew_framework.py`; no private patch manager |
| Engine update handlers | Native dispatch table decoded from UCP AOB context; handler-bounded signatures and layout validation |
| Fatal fire | Original damage/calculation/attribution; interior classification correction preserves the AIC entry observer |
| Dismount | Original synchronized group command, instruction 17; validate ID/UID then retain original loop and placement |
| Direct siege attack | Original synchronized attack dispatcher and decoded native stop function; preserve the original aiming and projectile owner |
| Variant capacity | Framework `data.version.isExtreme()` and independently checked native context; no fixed executable bindings |
| AI recruitment/group policies | AIC Tactics, untouched; no policy code copied |
| Tunnelers | ImprovedTunnelers for behaviour; AI Swapper 1.5.0 for starting counts/native initialization; neither required here |

The module-local handler resolver is needed for the eight engine handlers. It
resolves once at initialization and checks handler boundaries and instruction
context. Signature uniqueness is checked offline. Crew correction allocates
217 bytes and replaces 66 original bytes;
dismount allocates 83 bytes and replaces 7; target stop allocates 27 bytes and
replaces 7. No per-tick Lua callback, scan or census. The target-stop site belongs
to the tribe-command dispatcher, outside the bounded unit-handler resolver; it
uses `core.AOBScan`, decoded branch/call targets, `core.callTo` and
`core.insertCode` from the same framework version.

## Settings and testing

`fixed-engineers.crew_lifecycle` and `fixed-engineers.siege_target_stop` both
default to false in runtime and options, with independent controls under
the established localized **Bugfixes** category. All nine frontend option and
description catalogs are included; root description equals English.

Disable the old Unit Behaviour Fixes module when selecting this replacement.
If `unit-behaviour-fixes.crew_lifecycle` was explicitly OFF, set the new control
OFF too: the rename cannot automatically migrate another module's configuration.
Do not leave both native patch owners selected.

Short single-player check: crew and damage an engine, dismount surviving
engineers and check health/identity; destroy a crewed engine and check for hidden
survivors. Move a manned catapult/trebuchet, click an enemy unit in another
direction and check that the old path stops while normal aiming/firing continues.
Restart with each switch OFF to compare. Save/load, repeated dismount, fire deaths
and SHC/Extreme composition still need in-game acceptance.

The `tests/check_crew_*.py`, `check_unman_*.py` and `check_siege_target_stop.py`
probes cover crew bindings and preflight, dismount ID/UID cases, fire damage and
target-stop commands at the instruction level on licensed executables; they are
not an in-game run. Engineer role-quota accounting and siege placement,
harassment, capacity or resource policies are not part of this module.

## Release notes

- **0.3.0:** Both fixes are off by default. After updating, switch them on in
  Customizations unless you saved them on.
