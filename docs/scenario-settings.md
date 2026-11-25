# Scenario Settings Fix

The scenario editor saves with the map which troops can be recruited, which
weapons can be made and which goods can be traded. Every start loads these
values with the map, but the game then ignores some of them:

- The skirmish start (also multiplayer and Custom Skirmish Trails missions)
  allows every troop, weapon and good again.
- Play a Map applies the troops and goods but allows every weapon again.
- A new fletcher always starts on bows and a new pole turner on spears, even
  when only crossbows or pikes can be made. The blacksmith already checks this.

This module takes away what the map forbids, after the game has set its own
values. It never allows something the game forbids itself. Building
availability is applied by the game in all of these starts already. Campaign
missions keep the game's behaviour: several shipped campaign maps hold weapon
and trade limits that the game has never applied.

The **Bugfixes → Map availability settings** switch is off by default and needs
a restart when changed. In multiplayer every player needs the same setting.
No save data is added; saved games keep the values the game was started with.
A Custom Skirmish Trails mission that sets `recruitable_*`, `producible_*` or
`tradeable_*` still overrides the map for those columns.

Some shipped skirmish maps hold old limits that the game ignored until now.
For example, Oasis by the Sea forbids bows, spears and maces.

Read-only static and isolated machine-code checks passed on the two locally
available 1.41 executables (SHC and Extreme). In-game acceptance is pending.
