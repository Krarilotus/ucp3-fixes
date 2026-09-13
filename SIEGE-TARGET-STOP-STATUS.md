# Direct enemy click: local correction, acceptance gap

13 September 2026. The user confirmed that the moving catapult report is a
direct click on an enemy unit, rather than Attack Here on ground or a wall.

## Confirmed cause and correction

The original `TribesState::giveTribeAnInstruction` instruction-4 branch converts
catapult and trebuchet attacks to ground orders without calling
`UnitsState::makeUnitStopWalkingByClearingPathProgressState`. The adjacent ground,
wall and Halt branches, and the other tested ranged unit branches, call it.
Consequently the old movement path survives the new attack order.

The local `unit-behaviour-fixes/siege-targeting.lua` correction calls that native
owner once at the affected branch. Native movement finishes its current step;
native aiming, animation, ammunition and release remain responsible for firing.
It does not promise instantaneous firing or replace range/pathfinding logic.
`siege_target_stop` defaults ON with an OFF UCP2Switch in the existing Bugfixes
category. Control/help translations exist in all nine current module locales.

## Reuse and binding review

Inspected owner base: ucp3-fixes `8a1a92f9216f7699c6e2f0d2f57ecfb854b8d647`.
Its `unit-handlers.find` resolves unit updates, not the synchronized tribe
command dispatcher. This correction belongs in the existing fixes owner rather
than a competing projectile update hook. UCP `core.AOBScan`, `core.insertCode`
and `core.callTo` provide discovery, patch installation and call relocation.
Three identifying instruction contexts resolve the branch, its kind selector
and the adjacent native cleanup call. Decoded roots, selector ownership, field
layout and the native thiscall/RET4 body are checked before installation and
again before patching. There are no fixed runtime executable addresses.
One 27-byte initialization allocation and one 7-byte command hook; no recurring
scan, target cache, new simulation timer, saved state or RNG call.

## Evidence and explicit remaining gap

`tests/check_siege_target_stop.py` passed 144 paired original-command cases across
six licensed normal/Extreme reference, EFIGS and Polish fixtures. It exercises
the complete original command and native cleanup without callee replacements,
checks register/stack return and record changes, and tests incompatible/occupied
bindings before writes. The existing 33 repository tests also passed.

**NOT shipped or complete:** corrected direct-enemy-click gameplay has not yet
been verified in the actual game. The desktop control test verified movement
and a subsequent wall order only, with this correction OFF. Multiplayer,
save/replay, actual GUI toggle/persistence/layout, collection integration,
runtime error localization and older executable versions remain unverified.
The binding fixtures are not a claim of full gameplay compatibility. The
projectile module's separate wrong-facing-after-Halt correction is also local
and must be tested in combination. Do not mark the store PR ready or advertise
a corrected downloadable build on the strength of these command tests alone.

Next focused acceptance: move a manned catapult and trebuchet, click an in-range
hostile unit in another direction, verify the path stops and native aiming
precedes release; repeat OFF, out of range, wall/ground orders and Halt. Obtain
the desktop through the cooperative queue. The slot was released at 21:43 CEST;
the isolated game configuration and module archive were restored.
