# extension-aiv-troop-spot-fix

UCP3 module for Stronghold Crusader / Crusader Extreme.

Makes AI **start troops walk to the unit positions placed in the AIV** at the start of a skirmish. Fixes a long-standing engine bug where troops from three AIV rows were silently discarded on load and stayed idle at the keep — most visibly the Arabic lords' swordsmen. Firefly fixed this for the Definitive Edition; the original engine never was.

See [`description.md`](description.md) for the full write-up.

## Technical summary

AIV section 2012 (24×10 matrix of packed map positions, `value = y*400 + x`) is decoded into the per-AI spot array (`0x11F1754`) by the loop at `0x4EF460`. At `0x4EF840`–`0x4EF869` it skips rows **9, 11 and 18** — zeroing their count and jumping to the loop increment — so troops placed in those rows never receive a target position. Stock AIVs place real start troops there (row 18: every Arabic lord + Sheriff/Wazir/Wolf; row 9: Wolf; row 11: Phillip).

The fix NOPs the three `je 0x4EFB87` jumps so all rows `0`–`21` load. Patch site located via AOB scan; fails cleanly on non-matching versions.

Verified on Crusader Extreme by live memory read (rows 9, 11, 18 go from empty to loaded after the patch, across Sultan and Wolf) and by observation (troops march to their positions).

- Type: **module** (needs `core` access — not a plugin)
- Author: Samurai
- Requires "Disable Security" while unsigned; will be submitted to the UCP3 extension store.
