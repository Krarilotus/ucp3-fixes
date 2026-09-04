--[[
  Hop Farm Limit Fix

  When the AI wants to build a farm it passes through a gate (0x4CB470)
  that counts its existing farms and compares the count against the farm
  limit from its AIV data (field +0x74). The counting routine it uses,
  0x40AA20, checks building types 0x1E (wheat), 0x20 (apple) and 0x21
  (dairy) but omits 0x1F (hops). Hop farms are therefore not counted
  towards the shared farm limit, so they slip through the gate as long as
  the food-farm count stays under the limit. Over long games this lets hop
  farms accumulate beyond their intended share.

  A second, correct copy of the same count (0x40CB20, used elsewhere)
  checks all four farm types; the jump distances prove 0x40AA20 is missing
  the 6 bytes of the 0x1F comparison.

  This patch replaces the three separate comparisons with a single range
  check covering all four farm types (0x1E-0x21), so hop farms count
  towards the same limit as the food farms. The replacement occupies the
  exact 18 bytes of the original comparisons; no code is relocated.

  Note: 0x40AA20 has exactly one caller (the farm gate), so the change is
  local to farm-building and does not affect food/economy planning. Because
  hop farms now share the limit, AIs with a tight limit build slightly
  fewer food farms in exchange.

  Details: the analysis document accompanying this module.
]]--

-- Unique to the broken routine: 0x1E and 0x20 compared back-to-back
-- (the correct routine at 0x40CB20 has the 0x1F check in between).
local AOB = "66 83 F9 1E 74 0C 66 83 F9 20 74 06 66 83 F9 21 75 11"

return {
  enable = function(self, config)
    local target = core.AOBScan(AOB, 0x400000)
    if target == nil then
      log(WARNING, "hopfarm-limit-fix: pattern not found, game version not supported. No changes applied.")
      return
    end
    core.writeCode(target, {
      0x83, 0xE9, 0x1E,        -- sub ecx, 0x1E
      0x83, 0xF9, 0x03,        -- cmp ecx, 3
      0x77, 0x1B,              -- ja  +0x1B  (= target of the original jne)
      0x90, 0x90, 0x90, 0x90, 0x90,
      0x90, 0x90, 0x90, 0x90, 0x90,
    })
    log(INFO, string.format("hopfarm-limit-fix: patched farm counter at 0x%X", target))
  end,

  disable = function(self, config)
    log(WARNING, "hopfarm-limit-fix: disable at runtime not supported, restart the game without this plugin.")
  end,
}
