--[[
  AIV Troop Spot Fix

  AI start troops placed at unit positions in the AIV (section 2012, a
  24-row x 10-column matrix of packed map positions, value = y*400 + x)
  are supposed to walk to those positions at the start of a skirmish.
  For several troop rows they do not, and the units stay idle at the keep.
  Firefly fixed this for the Definitive Edition; the original engine
  (Crusader / Crusader Extreme) was never patched.

  Root cause: the routine that decodes section 2012 into the per-AI spot
  arrays (position array 0x11F1754, decode loop at 0x4EF460) explicitly
  skips three rows. At 0x4EF840-0x4EF869 it tests the row index against
  9, 11 and 18 and, on a match, jumps straight to the loop increment
  (0x4EFB87) after zeroing that row's count - so those rows are never
  loaded and their placed troops receive no target position.

  This is a genuine bug, not intended behaviour: Firefly's own stock AIVs
  place real start troops in exactly these rows (row 18 is used by every
  Arabic lord - Saladin, Caliph, Sultan - and also by Sheriff, Wazir and
  Wolf; row 9 by Wolf, row 11 by Phillip). The most visible symptom is
  Arabic swordsmen standing idle, because the Arabic lords populate the
  skipped row 18 the heaviest.

  Verified on Crusader Extreme by live memory + observation: with the
  three skip jumps removed, row 18 loads its positions and the troops
  march to them.

  The fix disables the three conditional jumps (each a 6-byte
  `je 0x4EFB87`) by overwriting them with NOPs, so all rows 0-21 load
  their positions. The comparisons themselves are left in place and become
  harmless; no code is relocated and no other row handling changes.
]]--

-- The three back-to-back "cmp [esp+0x1C], imm8 / je 0x4EFB87" checks for
-- rows 9, 11 and 18, preceded by the row-count reset (c7 00 ...). Unique.
local AOB =
  "83 7C 24 1C 09 8B 44 24 38 C7 00 00 00 00 00 " ..
  "0F 84 32 03 00 00 " ..            -- je for row 9   (offset +15)
  "83 7C 24 1C 0B " ..
  "0F 84 27 03 00 00 " ..            -- je for row 11  (offset +26)
  "83 7C 24 1C 12 " ..
  "0F 84 1C 03 00 00"                -- je for row 18  (offset +37)

local NOP6 = { 0x90, 0x90, 0x90, 0x90, 0x90, 0x90 }

return {
  enable = function(self, config)
    local target = core.AOBScan(AOB, 0x400000)
    if target == nil then
      log(WARNING, "aiv-troop-spot-fix: pattern not found, game version not supported. No changes applied.")
      return
    end
    core.writeCode(target + 15, NOP6)   -- neutralise skip of row 9
    core.writeCode(target + 26, NOP6)   -- neutralise skip of row 11
    core.writeCode(target + 37, NOP6)   -- neutralise skip of row 18
    log(INFO, string.format("aiv-troop-spot-fix: patched AIV spot decoder at 0x%X", target))
  end,

  disable = function(self, config)
    log(WARNING, "aiv-troop-spot-fix: disable at runtime not supported, restart the game without this module.")
  end,
}
