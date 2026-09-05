--[[
  AIV Troop Spot Fix

  AI start troops placed at unit positions in the AIV (section 2012, a
  24-row x 10-column matrix of AIV-local positions, value = y*100 + x)
  are supposed to walk to those positions at the start of a skirmish.
  For several troop rows they do not, and the units stay idle at the keep.
  This module fixes only the three loader exclusions described below; it
  does not replace troop assignment, patrol, or movement behavior.

  Root cause: the routine that decodes section 2012 into the per-AI spot
  arrays (position array 0x11F1754, decode loop at 0x4EF460) explicitly
  skips three rows. At 0x4EF840-0x4EF869 it tests the row index against
  9, 11 and 18 and, on a match, jumps straight to the loop increment
  (0x4EFB87) after zeroing that row's count - so those rows are never
  loaded and their placed troops receive no target position.

  Firefly's own stock AIVs
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
local SKIP_OFFSETS = {
  15, -- row 9: pikemen
  26, -- row 11: swordsmen
  37, -- row 18: Arabian swordsmen
}

return {
  enable = function(self, config)
    if config.enabled == false or self.applied then
      return
    end
    -- AOBScan raises on failure. Validate the entire block before any write.
    local ok, target = pcall(core.AOBScan, AOB)
    if not ok then
      error("aiv-troop-spot-fix: cannot locate the AIV row checks; unsupported executable or conflicting patch. No changes applied. " .. tostring(target))
    end
    for _, offset in ipairs(SKIP_OFFSETS) do
      core.writeCode(target + offset, NOP6)
    end
    self.applied = true
    log(INFO, string.format("aiv-troop-spot-fix: patched AIV spot decoder at 0x%X", target))
  end,

  disable = function(self, config)
    return false, "aiv-troop-spot-fix: restart the game to change this option"
  end,
}
