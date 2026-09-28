# Gatehouse Capture Fix

Gatehouse control now depends on living occupants. The original gatehouse
occupancy loop used a unit's selectable flag to add its troop value, even after
the unit started dying. The game's own living-unit census also checks the
native dying flag. This module adds that check to the existing occupancy loop;
native tile lists, troop values, teams and capture handling remain in charge.

The **Bugfixes → Living gatehouse defenders** switch defaults to on and needs a
restart when changed. No save or map data is added. The module is optional;
maps remain usable without it, although gatehouse control follows the original
rules when it is off.

Read-only static and isolated machine-code checks passed on the two locally
available 1.41 executables (SHC and Extreme). Gameplay, save/load, replay and
other supported distribution/language variants still need acceptance. Players
own multiplayer testing.

Suggested single-player test:

- [ ] Place opposing living troops on a gatehouse and check normal control.
- [ ] Kill the last defender while an attacker remains; the corpse must not keep control.
- [ ] Kill the last attacker while a defender remains; the corpse must not take control.
- [ ] Repeat with an assassin and a unit with a long death animation.
- [ ] Save and load during the death animation, then repeat with the switch off.
