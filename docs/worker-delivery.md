# Worker Delivery Fix

Workers sometimes fail to deliver goods when their route to a granary or
armory is open but the route from the keep to that store is blocked.
This module lets the existing building-entry check use the delivery worker's
area in that case. The game's native pathfinder and final movement check still
decide whether the worker can actually reach the store. The map-region limit
and general keep-entrance blockage are separate issues and are unchanged.
The AI also keeps a granary or armory with a valid entrance instead of removing
it solely because the keep route is blocked. Invalid entrances still follow
the native repair/removal path.
Stockpiles already bypass this particular keep-region check in the original
game, so this module does not change their delivery logic.

The **Granary and armory delivery** switch is under **Bugfixes** and is off by
default. Restart the game after changing it. The package provides option text and descriptions in
all nine currently supported UCP frontend languages. It adds no saved state or
map-format section.

## Code evidence and integration

Ghidra/OpenSHC show that `buildingIsAccessible` checks the store from the
player's keep area, while worker movement checks from the worker's own tile.
Granary and armory selection perform the keep check before the worker's direct
check. The module changes the origin of the existing area-to-area query only
for calls from delivery worker routines or their two storage selectors, and
only for granaries and armories with a live, same-owner worker. The AI heatmap's
call uses the native query's same-area fast path for a store with a valid
entrance. Other building checks retain the keep origin. The existing native
entrance selector, pathfinder and movement routine remain in place. The Ghidra probe and its read-only trace
are in the workspace's `Roadmap/Investigations/R080` directory; reference
addresses are not runtime bindings.

The AI heatmap removes a building when the check returns 0 (no entrance tile in
any area) or 2 (an entrance exists, but the keep can't reach it). UCP2 Legacy's
**Disable demolishing of inaccessible buildings** (`ai_access`, on in
ucp2-legacy-defaults) replaces the `jne` after that
call with `jmp`, which drops only the removal for result 0. That byte is its
patch site. This module accepts either form there, refuses anything else, and
writes nothing in that code. Its store query turns result 2 into 1 for a granary
or armory with a valid entrance, so the two changes add up, in either load order.

Runtime discovery uses the UCP 3.0.7 `core.AOBScan` cache and native detour
facility. Every required signature and operand relationship is checked before
the hook is installed. No static executable address, copied pathfinder,
per-tick scan, or new save data is shipped.

The read-only fixture probe passed on EFIGS and Polish normal/Extreme 1.41
images and the two installed local images. This verifies signatures and a
mocked register/stack path, not real gameplay or every possible distribution.
The native check also writes a shared building-access flag. Ghidra found no
direct reads of that flag in the named executable, but save/copy effects have
not been ruled out. The AI may retain an isolated store until its route opens;
workers still need a real route to deliver. In-game single-player acceptance
and GUI Customizations checks remain pending.

## Try it in single-player

Build `worker-delivery-fix-0.2.0.zip` with
`python tools/build_modules.py --output ./local-packages`, then put that ZIP in
`ucp/modules/`. It is unsigned, so enable **Disable Security** for this local
test, select **Worker Delivery Fix** in Content, and turn its Bugfixes switch
ON. Do not use it as a release package yet.

- [ ] With a farmer and weapon maker, confirm normal deliveries to a granary
  and armory while the keep route is open. Observe stockpile delivery as a
  separate unchanged control.
- [ ] Block the route from the keep to the granary and armory while leaving
  each worker's own route open. Confirm goods arrive and the workers remain alive.
- [ ] Block the worker's route too. Confirm no goods are delivered across the
  blockage and no worker disappears unexpectedly.
- [ ] With an AI player, block the keep route while a granary or armory has a
  valid entrance. Confirm it stays built and reachable workers can deliver.
  Repeat with an invalid entrance: the game removes it, unless UCP2 Legacy's
  `ai_access` is on, which keeps buildings without an entrance.
- [ ] Reopen the keep route, save and reload, and confirm delivery continues.
- [ ] Repeat with the switch OFF after restarting, then repeat ON in normal
  Crusader and Extreme. Note the game build and active modules.

Multiplayer testing is left to players. A save renamed to `.map` should remain
editable without this module because the module adds no map or save data; that
editor check has not yet been run.

## Release notes

- **0.2.0:** Starts next to UCP2 Legacy's "Disable demolishing of inaccessible
  buildings" (0.1.2 stopped the game at startup there). The fix is off by default;
  after updating, switch it on in Customizations unless you saved it on.
