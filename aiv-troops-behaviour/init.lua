--[[
  AI: AIV Troop Behaviour

  AI start troops placed at unit positions in the AIV (section 2012, a
  24-row x 10-column matrix of AIV-local positions, value = y*100 + x)
  are supposed to walk to those positions at the start of a skirmish.
  For several troop rows they do not, and the units stay idle at the keep.
  The base patch fixes only the three loader exclusions described below.
  Optional behavior controls are implemented separately in behavior/.

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

  The original author reported on Crusader Extreme, with live memory + observation: with the
  three skip jumps removed, row 18 loads its positions and the troops
  march to them.

  The fix disables the three conditional jumps (each a 6-byte
  `je 0x4EFB87`) by overwriting them with NOPs, so all rows 0-21 load
  their positions. The comparisons themselves are left in place and become
  harmless; no code is relocated and no other row handling changes.
  Loading a row does not assign a starting role: pikemen selected by the
  native moat-digger routine still dig. Only an explicit behavior setting
  changes that assignment.
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

local function installRows()
  local target, reason = core.AOBScanUnique(AOB)
  if not target then error(reason, 0) end
  local original = {}
  for index, offset in ipairs(SKIP_OFFSETS) do
    original[index] = core.readBytes(target + offset, #NOP6)
  end
  for index, offset in ipairs(SKIP_OFFSETS) do
    local ok, failure = pcall(core.writeCode, target + offset, NOP6)
    if not ok then
      for touched = index, 1, -1 do
        pcall(core.writeCode, target + SKIP_OFFSETS[touched], original[touched])
      end
      error(failure, 0)
    end
  end
end

return {
  enable = function(self, config)
    if self.started or config == nil then return end
    if type(config) ~= "table" then
      log(ERROR, "AIV troop settings must be a table.")
      return
    end
    if config.enabled ~= nil and type(config.enabled) ~= "boolean" then
      log(ERROR, "AIV troop rows enabled must be a boolean.")
    end
    if config.enabled ~= true then return end
    local behavior, install = config.behavior
    if behavior ~= nil and type(behavior) ~= "table" then
      log(ERROR, "AIV troop behaviour settings must be a table.")
    elseif behavior and behavior.enabled == true then
      local ok, prepared = pcall(function()
        return require("behavior").prepare(behavior)
      end)
      if ok then
        install = prepared
      else
        log(ERROR, "AIV troop behaviour controls are off: " .. tostring(prepared))
      end
    elseif behavior and behavior.enabled ~= nil and type(behavior.enabled) ~= "boolean" then
      log(ERROR, "AIV troop behaviour enabled must be a boolean.")
    end

    local rowsOk, reason = pcall(installRows)
    if rowsOk then
      self.applied = true
    else
      log(ERROR, "AIV troop rows are off: " .. tostring(reason))
    end

    if install then
      local ok, policy = pcall(install)
      if ok then
        self.policy = policy
      else
        log(ERROR, "AIV troop behaviour controls are off: " .. tostring(policy))
      end
    end
    self.started = true
  end,

  -- Read-only policy answers for other modules; nil means the game's own value.
  -- ai is the aicloader personality (1 Rat .. 16 Abbot).
  defenseRowFor = function(self, ai, unitType)
    return self.policy and self.policy:ownRow(ai, unitType) or nil
  end,

  defenseGroupsFor = function(self, ai, row, slots, patrolGroups)
    return self.policy and self.policy:groups(ai, row, slots, patrolGroups) or nil
  end,

  disable = function(self, config)
    return false, "aiv-troops-behaviour: restart the game to change this option"
  end,
}
