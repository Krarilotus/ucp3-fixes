# Local gameplay check, 2026-09-05

Runtime tested: feature commit `e739eecafbee0ca3cb6376c60bb57c2e419f9f25`,
unsigned local packages, UCP 3.0.7 (`77c6accf`), aicloader 1.1.2,
aivloader 1.0.0, files 1.3.0, Graphics API Replacer 1.3.0 and
winProcHandler 1.0.0. Both game executables are the exact-hash 1.41 binaries
listed in [validation.md](validation.md). The hop fix was enabled alongside
the troop module. The real RPS hooks initialized without an error in both games.

## Controlled Crusader setup

The first stock-AIV observation was **not** counted as proof of correct slot
movement: Arabian swordsmen moving near the keep was ambiguous. The subsequent
test used named, modified copies of `caliph1.aiv`, `phillip1.aiv` and `wolf1.aiv`.
Only section 2012 changed. All 15 supported troop rows were given four AIV-local
points: `(20,20)`, `(75,20)`, `(75,75)`, `(20,75)` (encoded as `y*100+x`).
All eight castle choices for each of those AIs were mapped to its same test file
through aivloader before restarting and creating a fresh match. The original
game AIV files were not modified.

The loaded per-player arrays were read from game memory and confirmed to contain
four positions for every tested troop row, including rows 9, 11 and 18. These
arrays include the engine's orientation, translation and map-edge handling;
the AIV-local numbers are not world coordinates. Some destinations were adjusted
by native pathfinding around occupied tiles.

A local fixture set three starting units of each supported type for every AI.
The module itself was unmodified. The match used normal starting conditions on
the regular Crusader map displayed as **Dicht gedrängt**,
with Wolf, Caliph and Philip. All troop menu settings were Defend/Hold, and the
fixture applied these additional AIC values through aicloader after initialization:

| AI | Field | Value |
| --- | --- | --- |
| Wolf (4) | `AIVTroops_InitialRole_Pikeman` | `dig` |
| Caliph (6) | `AIVTroops_InitialRole_Slave` | `dig` |
| Philip (10) | `AIVTroops_Movement_Knight` | `patrol` |
| All test AIs | `DefWallPatrolGroups` | `1` |

## Results

- All 15 supported starting troop types were observed with assignments in the
  live Crusader match. Wolf's pikemen and Caliph's slaves received digger role 5;
  the same types on other test AIs received defender role 1. This demonstrates
  per-personality AIC priority over the global menu choices with the real loader.
- Engineers explicitly set to Defend received defender assignments, exercising
  the bypass of their native initial-assignment exclusion.
- Caliph's surviving held Arabian swordsmen settled at the separated ground
  destinations. Two later snapshots retained destinations `(238,237)` and
  `(294,238)`, beside loaded slots `(238,240)` and `(293,240)` respectively.
  Their positions also remained unchanged across those snapshots.
- Philip's three starting knights shared a patrol group. Consecutive snapshots
  showed destination clusters moving from around `(186,91)` to `(241,91)`,
  matching two of his loaded patrol positions. Their world positions changed as
  well. Other held groups remained at their assigned destinations. The user also
  observed the changed knight patrol behavior in the game window.
- The game error log remained empty apart from its header during these checks.

Extreme also loaded the pinned arrays and ran the real hooks without errors.
Wolf's pikemen received digging assignments, and explicitly configured engineers
received defensive assignments. However, the selected Extreme map had outpost
spawners: combat eliminated test troops before a clean second movement sample.
That run is an **initialization/assignment smoke check**, not a controlled
Extreme Hold/Patrol pass. A further run on a copied regular map was stopped at
the user's request; no such result is claimed.

## GUI verification and remaining scope

The Windows GUI 1.0.16 combined build at `86716ab` passed the 15-row/four-column
layout, 21 native marks, default-on AIC checkbox, complete description/control
collapse, independent resets, and reset-over-border checks. A troop radio choice
and a Starting Troops numeric edit survived Apply and reload; the original
preview configuration was restored afterward. Its source tree matches GUI PR
#368 merged onto the creator-controls changes. The combined suite has 84 passing
tests; the module suite has 33. TypeScript passes.

This confirms the representative role and movement cases above. It does not
complete the stable-release matrix in [validation.md](validation.md): actual
moat excavation for all six capable types, every orientation and path condition,
AI replacement, coexistence with ucp2-legacy/ai_defense, save/load, multiplayer,
long-run hook cost and the hop fix's economy impact still need their own checks.
The GUI merge does not publish a module or change the 3.0.7 store recipe.
