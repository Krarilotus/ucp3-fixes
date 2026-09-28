# Hunter Targeting Fix

Hunters now consider deer close to them, including deer beside the hut. When a
chosen deer is behind an obstacle, the hunter can continue along its existing
native path and try shooting again from a closer position. The hunter stops
approaching if the path ends or it gets within three tiles without a clear shot.
No new pathfinder, target list or saved state is introduced.

The **Bugfixes → Hunter targeting** switch defaults to on and needs a restart
when changed. Maps and saves keep their original format and remain usable
without this optional module.

Read-only signatures and isolated x86 branch execution passed on the local
SHC and Extreme 1.41 executables. Gameplay, save/load, replay, performance
and other supported executable variants remain to be checked. Players own
multiplayer testing.

Suggested single-player test:

- [ ] Put a deer beside a hunter's hut; the hunter should choose and shoot it.
- [ ] Offer a near and far deer; the hunter should prefer the nearer clear shot.
- [ ] Block the first shot with terrain or a wall; the hunter should approach, then shoot when clear.
- [ ] Give the hunter no usable path or no clear shot within three tiles; it should give up cleanly.
- [ ] Save/load and replay a hunt; compare behavior with the switch off.
