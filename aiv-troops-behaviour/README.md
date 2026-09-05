# AI: AIV Troop Behaviour

Version 0.2.0 combines restored AIV positions with opt-in controls for initial
troop assignments and defensive slot movement across all 15 supported troop types.
The base patch restores rows **9, 11 and 18** (pikemen and both swordsman types).
Requires Crusader / Crusader Extreme 1.41, framework >=3.0.4, frontend >=1.0.16,
and aicloader >=1.1.0. The proposed store target is UCP 3.0.7.

## Name and migration

The module ID and package folder are now **`aiv-troops-behaviour`**, reflecting
the broader scope. The Content list uses **AI: AIV Troop Behaviour**. German
Customizations and description headings use **KI: AIV-Truppenverhalten**;
the current frontend's Content-list `display-name` is a single untranslated string.

For an existing local `aiv-troop-spot-fix` installation, deselect the old module
and select `aiv-troops-behaviour`. Do not enable both; they patch the same loader.
Plugin dependencies and configuration keys must use the new ID. Move any existing
`aiv-troop-spot-fix` configuration block to `aiv-troops-behaviour`, keeping its
`enabled` and `behavior` contents. The `AIVTroops_*` AIC field names are unchanged.
The frontend does not automatically migrate a renamed module. Restart and use a
new match. This rename is part of the feature PR, before the proposed store release.

**Umstieg:** Das alte Modul `aiv-troop-spot-fix` abwählen und
`aiv-troops-behaviour` auswählen. Nicht beide gleichzeitig aktivieren.
Abhängigkeiten und den Konfigurationsschlüssel auf den neuen Namen umstellen;
`enabled`, `behavior` und die AIC-Feldnamen `AIVTroops_*` bleiben erhalten.
Der Umstieg erfolgt nicht automatisch. Danach das Spiel neu starten und eine
neue Partie beginnen.

## Base fix

AIV section 2012 is a 24 by 10 matrix of local positions encoded as `y * 100 + x`.
The engine rotates/translates those coordinates into game map tiles. Its loader
processes rows 0–21 but explicitly skips rows 9, 11 and 18 after resetting their
counts. The base fix replaces those three six-byte `je` instructions with NOPs.

**The base fix does not change slaves (row 13), which already load.** The original
description's narrow troop list was correct. Other units failing to reach their
spots need changes to assignment or movement, separately from AIV decoding.
The author's original Extreme gameplay test reported affected troops moving;
the new review independently checks instructions, not that gameplay observation.

## Customizations: defaults for every AI

Select the module and open **AI → AIV Troop Behaviour**. The base fix is enabled by default for
a selected module. **Troop settings** is off by
default; enable it to activate the additional controls. Missing configuration
keeps the base-only behaviour of 0.1.x.

The defaults group provides two common choices and separate choices for all
15 supported troop types. No AIC file or AI replacement is needed to use them.

Troop settings and all their controls share one collapsible switch section, as
in the legacy menu style. Enabling opens the section; disabling closes it. The
arrow can also expand/collapse it without changing the switch. The AIC override
checkbox remains enabled by default inside this section. Field guidance lives
in the module description and wiki, not in Customizations.

The table has Defend/Dig and Hold/Patrol sword-checkbox columns. It marks fixed
native states without storing explicit overrides. Native role assignments are
not the same as loaded AIV positions: swordsmen have native defense roles even
though the base game skips their position rows. The three skipped rows therefore
have no native slot-movement mark, even with the loading fix enabled. Engineers'
special assignment/oil duties do not have a direct equivalent in these columns.

Spearmen, pikemen, macemen and slaves can defend or dig depending on the AI's
DefDiggingUnitMax and live digging capability. Their untouched role has no selected box. Archers and crossbowmen always take the native defense branch.
Explicit choices and common defaults replace the native display; reset restores
inheritance. Opening the menu does not change runtime behavior or saved defaults.

- **Initial assignment:** native behaviour, or defend AIV slots. Each troop may
  inherit that choice. Digging-capable troops additionally offer moat digging.
- **Defensive slot movement:** native behaviour, hold an assigned slot, or patrol
  between slots. Each troop can inherit the common choice or choose its own.
- **Use AIC overrides:** enabled by default.
  Turn it off to use only the menu defaults, even if an AIC file supplies values.

For example, choose common **Defend AIV positions** and **Stay at the assigned position**,
then choose **Dig moats** for slaves and **Patrol between AIV positions**
for spearmen. This applies to every AI unless an enabled AIC override says otherwise.

Initial assignment affects live, selectable, unassigned starting/scenario troops
when the native AI first processes them. It is **not a timestamp-only hook**:
later scenario-spawned unassigned troops can also pass through that routine.
Normal defense recruits keep their separate recruitment path. Already assigned
troops are not reassigned; the existing moat-recruitment AIC fields remain intact.

Only **Crusader archers, spearmen, pikemen, macemen, engineers and slaves** can
be selected as diggers. Crossbowmen, Arabian archers and swordsmen cannot.
The hook also checks the unit's live digging capability. If it is disabled,
an explicit digging request falls back to defense. Digging still needs moat tiles.

Holding fixes each defensive group's slot; it does not freeze the units or
disable combat. Patrolling uses the existing **DefWallPatrolGroups** and
**DefWallPatrolRallyTime** controls. With zero patrol groups, custom patrol retains
one stationary group; it does not cycle. With no AIV slots, normal recruitment
falls back to the keep/campfire; the custom movement hook issues no slot order.
Threat responses, pathfinding and special duties (including engineer oil duty)
still take priority in their existing routines.

Restart UCP and start a **new match** after changing these settings. Changes to
group capacities do not migrate existing armies. Do not hot-swap these fields
mid-match; save/load and multiplayer behaviour still need validation.

## Optional per-AI AIC overrides

`aicloader` is a declared dependency because it owns additional-field registration.
UCP's dependency schema has no optional-dependency declaration. The override
**behavior** is optional via the menu switch. `aiSwapper` is not required:
vanilla AI personalities work too. If aiSwapper is used, its character `aic`
objects can contain these fields; handlers register during module enable,
before aicloader and aiSwapper apply files in `afterInit`.

Precedence, highest first:

1. Explicit troop-specific AIC value for that personality.
2. Explicit common AIC value for that personality.
3. Troop-specific Customizations default.
4. Common Customizations default, then native behaviour.

Omitted AIC fields inherit the next applicable setting. There is no explicit
inherit/native AIC value: use lowercase strings, not numbers. Resetting an AI
clears its overrides and restores the menu defaults. Personalities are aicloader
IDs 1 (Rat) through 16 (Abbot), not player slots; players using one personality
share its settings. Restart and start a new match after editing files; omitting
a field from a later partial write does not clear an already applied override.

| AIC field | Allowed values |
| --- | --- |
| `AIVTroops_InitialRole` | `"defend"` |
| `AIVTroops_InitialRole_<Troop>` | `"defend"`; `"dig"` for capable troops only |
| `AIVTroops_Movement` | `"hold"`, `"patrol"` |
| `AIVTroops_Movement_<Troop>` | `"hold"`, `"patrol"` |

`InitialRole` controls the assignment of unassigned starting/scenario troops;
`Movement` controls defenders at their AIV slots. These are independent settings:
`"defend"` / `"dig"` are not movement values, and `"hold"` / `"patrol"` are not roles.

`<Troop>` is one of: `Engineer`, `Archer`, `Crossbowman`, `Spearman`, `Pikeman`,
`Maceman`, `Swordsman`, `Knight`, `Slave`, `Slinger`, `Assassin`, `ArabianArcher`,
`HorseArcher`, `ArabianSwordsman`, `FireThrower`. Names and values are case-sensitive.
Only Engineer, Archer, Spearman, Pikeman, Maceman and Slave accept `"dig"`.
The common initial-role field cannot select digging; select capable types explicitly.
Invalid values are logged and leave the previous setting intact. The AIC getter
returns the configured string, or nil when no override has been set.

Earlier unreleased builds accepted numbers. Replace role 1/2 with `"defend"`/`"dig"`
and movement 1/2 with `"hold"`/`"patrol"`; remove -1 and 0 fields. Removing an old
explicit 0 now inherits common/menu choices instead of bypassing them. No change
is needed to saved Customizations values.

Example file supplied through aicloader's `aicFiles` configuration:

```json
{
  "AICharacters": [
    {
      "Name": "Rat",
      "Personality": {
        "AIVTroops_InitialRole": "defend",
        "AIVTroops_InitialRole_Slave": "dig",
        "AIVTroops_Movement": "hold",
        "AIVTroops_Movement_Spearman": "patrol",
        "DefWallPatrolGroups": 2,
        "DefWallPatrolRallyTime": 10
      }
    }
  ]
}
```

Only Rat is overridden here. Other personalities inherit Customizations.
When custom rules are active for a troop, its ordinary AIV row is used instead
of the engine's early-pause ranged-to-slave-row alias. Custom slave rules also
separate ranged units from that row so they cannot join a configured slave group.
Native rules and this alias remain unchanged when all relevant choices are native.

## Implementation and validation

The troop list and capability/field definitions live in `behavior/policy.lua`.
Policy, AIC registration, address resolution and hook installation are separate.
The hooks reuse native assignment and movement routines rather than duplicating
their troop/group bookkeeping. They leave human players and unknown unit types alone.
All behaviour sites and the base row block resolve before patch installation.
Unsupported signatures fail initialization. Hook installation itself is not a
transaction; an allocation/runtime failure requires restarting the game.

| Site | Crusader 1.41 | Extreme 1.41 |
| --- | --- | --- |
| Base row checks (+15, +26, +37 patched) | `0x4EF4B0` | `0x4EF840` |
| Initial assignment | `0x4D3FA3` | `0x4D4353` |
| Unit-to-row mapper | `0x4CC390` | `0x4CC5E0` |
| Defense group capacity | `0x4CCA04` | `0x4CCC54` |
| Native patrol group capacity | `0x4D43B1` | `0x4D4761` |
| Slot movement | `0x4D2E00` | `0x4D31B0` |

These are audit references, not hardcoded addresses. Tribe strides are decoded
from the game: `0x334` in Crusader, `0x688` in Extreme. Both local executables pass
the read-only signature and instruction-boundary audit. Portable tests cover
policy, callbacks, menu/locale consistency, ABI arguments and x86 branch routing.
**This feature still needs live UCP 3.0.7 gameplay validation before release.**
See the source repository's `docs/validation.md` for the complete checklist.
