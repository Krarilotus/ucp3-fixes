local Policy = require("behavior.policy")

-- The gate preserves EAX/EFLAGS and jumps to the engine's existing assignment
-- branches. On inherit it executes the seven displaced bytes before returning.
local function initialGate(gate, defend, dig)
  return {
    0x9C, 0x50,                         -- pushfd; push eax
    0xE8, core.relTo(gate, -4),          -- call Lua decision gate
    0x83, 0xF8, 0x01, 0x74, 0x09,      -- cmp eax,1; je defend
    0x83, 0xF8, 0x02, 0x74, 0x0B,      -- cmp eax,2; je dig
    0x58, 0x9D, 0xEB, 0x0E,            -- restore; jump to displaced code
    0x58, 0x9D, 0xE9, core.relTo(defend, -4),
    0x58, 0x9D, 0xE9, core.relTo(dig, -4),
  }
end

local function prepare(config)
  local policy = Policy.new(config)
  local game = require("behavior.game").resolve()
  return function()
    local sites = game.sites
    local gate = core.allocateCode({0x90, 0x90, 0x90, 0x90, 0x90, 0xC3})
    core.detourCode(function(r)
      -- This point is reached only for live, selectable, unassigned AI units.
      -- EBP is PlayerData.aiType-1 (the aicloader ID); ESI points at the type field. Recruits use a
      -- separate dispatch in aiRecruitUnits and never pass through this gate.
      r.EAX = policy:initialRole(r.EBP, core.readSmallInteger(r.ESI),
        core.readSmallInteger(r.ESI + 0x2E0) ~= 0)
      return r
    end, gate, 5)
    core.insertCode(sites.initial, 7, initialGate(gate, sites.initial + 119, sites.initial + 109), nil, "after")

    -- Override group capacity after the vanilla special cases for rows 8/10/17.
    core.detourCode(function(r)
      local mode = policy:get(game.ai(r.EBP), "Movement", r.EAX)
      if mode ~= 0 then r.EBX = Policy.groupCount(mode, game.slots(r.EBP, r.EAX), r.EDX) end
      return r
    end, sites.groupLimit, 9)

    -- Let held native-patrol rows retain a group for every slot. Adjust before
    -- the original cmp, so its condition flags and local group counts agree.
    core.detourCode(function(r)
      local mode = policy:get(game.ai(r.EBP), "Movement", core.readInteger(r.EBX))
      if mode ~= 0 then r.EAX = Policy.groupCount(mode, r.ECX, r.EAX) end
      return r
    end, sites.patrolLimit, 8)

    local originalMapper
    originalMapper = core.hookCode(function(this, unitID, firstPause)
      local unit, ai = game.unit(unitID)
      local row = unit and policy:ownRow(ai, unit)
      if row then return row end
      return originalMapper(this, unitID, firstPause)
    end, sites.mapper, 3, 1, 10)

    local originalMovement
    originalMovement = core.hookCode(function(this, tribe, row, slot)
      local ai, ordinal, slots, hits = game.movementContext(tribe, row)
      local mode = ai and policy:get(ai, "Movement", row) or 0
      if mode ~= 0 then
        local target = Policy.slotIndex(mode, ordinal, slots, game.patrolGroups(this, ai), hits)
        -- No AIV slots: do not issue a movement order towards map tile zero.
        if target == nil then return 0 end
        slot = target
      end
      return originalMovement(this, tribe, row, slot)
    end, sites.movement, 4, 1, 7)

    require("behavior.aic")(policy)
  end
end

return {prepare = prepare, initialGate = initialGate}
