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
  local sites = game.sites
  local function install(original, touching)
    local gate = core.allocateCode({0x90, 0x90, 0x90, 0x90, 0x90, 0xC3})
    core.detourCode(function(r)
      -- This point is reached only for live, selectable, unassigned AI units.
      -- EBP is PlayerData.aiType-1 (the aicloader ID); ESI points at the type field. Recruits use a
      -- separate dispatch in aiRecruitUnits and never pass through this gate.
      r.EAX = policy:initialRole(r.EBP, core.readSmallInteger(r.ESI),
        core.readSmallInteger(r.ESI + 0x2E0) ~= 0)
      return r
    end, gate, 5)
    local entry = initialGate(gate, sites.initial + 119, sites.initial + 109)
    entry[#entry + 1] = original[sites.initial]
    entry[#entry + 1] = core.jmpTo(sites.initial + 7)
    local bridge = core.allocateCode(core.calculateCodeSize(entry))
    core.writeCode(bridge, entry)
    local initialPatch = core.compile({core.jmpTo(bridge), 0x90, 0x90}, sites.initial)

    -- Override group capacity after the vanilla special cases for rows 8/10/17.
    touching[#touching + 1] = sites.groupLimit
    core.detourCode(function(r)
      local groups = policy:groups(game.ai(r.EBP), r.EAX, game.slots(r.EBP, r.EAX), r.EDX)
      if groups then r.EBX = groups end
      return r
    end, sites.groupLimit, 9)

    -- Let held native-patrol rows retain a group for every slot. Adjust before
    -- the original cmp, so its condition flags and local group counts agree.
    touching[#touching + 1] = sites.patrolLimit
    core.detourCode(function(r)
      local groups = policy:groups(game.ai(r.EBP), core.readInteger(r.EBX), r.ECX, r.EAX)
      if groups then r.EAX = groups end
      return r
    end, sites.patrolLimit, 8)

    touching[#touching + 1] = sites.mapper
    local originalMapper
    originalMapper = core.hookCode(function(this, unitID, firstPause)
      local unit, ai = game.unit(unitID)
      local row = unit and policy:ownRow(ai, unit)
      if row then return row end
      return originalMapper(this, unitID, firstPause)
    end, sites.mapper, 3, 1, 10)

    touching[#touching + 1] = sites.movement
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
    touching[#touching + 1] = sites.initial
    core.writeCodeBytes(sites.initial, initialPatch)
  end
  return function()
    local original, touching = {}, {}
    for address, size in pairs({
      [sites.initial] = 7, [sites.groupLimit] = 9, [sites.patrolLimit] = 8,
      [sites.mapper] = 10, [sites.movement] = 7,
    }) do
      original[address] = core.readBytes(address, size)
    end
    local unregister = require("behavior.aic")(policy)
    local ok, reason = pcall(install, original, touching)
    if not ok then
      for _, address in ipairs(touching) do
        pcall(core.writeCodeBytes, address, original[address])
      end
      unregister()
      error(reason, 0)
    end
    return policy
  end
end

return {prepare = prepare, initialGate = initialGate}
