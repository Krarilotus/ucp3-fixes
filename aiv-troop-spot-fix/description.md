Restores loading of AIV troop positions for **pikemen, swordsmen and Arabian swordsmen** (rows 9, 11 and 18), which the original loader skips.

This fixes those three rows, not every case of troops staying at the keep. **Slaves and other troop types are unchanged.** Slaves use row 13, which already passes through the loader. Troop assignment, movement, patrols and the AI's responses to threats still follow the existing rules.

The fix has an enable switch under **AI → Fixes**. Restart the game after changing it. Requires UCP3 and Stronghold Crusader / Crusader Extreme 1.41.
