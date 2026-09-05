# Native states shown in the troop table

The table describes the unmodified game's roles and slot-movement modes. These
are presentation hints for `native` values after menu inheritance is resolved;
they do not replace saved defaults or enable any behavior hooks. Selecting a
marked native choice explicitly is still a customization.

| Troops | Starting role | Slot movement |
| --- | --- | --- |
| Engineers | No equivalent; excluded by the initial-role routine | Special oil duties, no ordinary hold/patrol mark |
| Crusader archers, crossbowmen | Defend | Hold |
| Spearmen, macemen | Conditional; no selected box | Patrol |
| Pikemen | Conditional; no selected box | No loaded position row in the unmodified game |
| Swordsmen, Arabian swordsmen | Defend | No loaded position row in the unmodified game |
| Knights, slingers, assassins, Arabian archers, fire throwers | Defend | Hold |
| Slaves | Conditional; no selected box | Hold |
| Horse archers | Defend | Patrol |

`aiAssignMoatDiggers` at Crusader `0x4D3F20` excludes engineers. For other listed
troops it chooses defense if `DefDiggingUnitMax` is zero, the unit is an archer
or crossbowman, or the live digging flag is zero; otherwise it chooses digging.
The capable non-archer types are spearmen, pikemen, macemen and slaves. The
vanilla AIC Loader data has zero digging capacity for the Rat and nonzero for
the Snake, so a single fixed role for these types would misrepresent some AIs.

The movement dispatch tables were read from the installed Crusader 1.41 PE
identified in [validation.md](validation.md). The row-number columns begin at
`0xB4271C` (ranged: 6, 7, 14, 16, 19), `0xB4274C` (ground: 9, 11, 12, 15, 18, 13),
and `0xB4277C` (patrol: 8, 10, 17). Ranged and ground routines at `0x4D4130` and
`0x4D4220` use fixed ordinal slots; `0x4D4340` cycles patrol slots. The base loader
skips rows 9, 11 and 18, so those rows receive no native movement mark even when
the module's loading fix is enabled. Defense assignment remains distinct from
position loading.

The display describes the ordinary role/movement paths, not a promise that a
unit is moving right now. AIV availability, patrol-group counts, danger responses,
pathfinding and special duties still affect actual gameplay. The shared menu
cannot predict per-personality AIC overrides supplied later by another module.
