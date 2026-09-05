-- Resolve version-dependent addresses once, before installing any behavior hook.
-- Player/unit layouts are shared; the tribe stride differs in Extreme.
local PATTERNS = {
  mapper = "8B 44 24 04 69 C0 90 04 00 00 0F B7 88 ? ? ? ? 66 83 F9 01 0F BF 90 ? ? ? ? 75 09",
  movement = "51 53 55 8B 6C 24 10 8B C5 69 C0 ? ? 00 00 8B 98 ? ? ? ? 89 4C 24 08 8B CB 33 D2 33 C0",
  playerType = "69 C0 F4 39 00 00 53 8B D9 8B 88 ? ? ? ? 85 C9 0F 84",
  unitLimit = "83 C7 01 81 C6 90 04 00 00 3B 3D ? ? ? ? 0F 8C ? ? ? ? 5E 5F 5D 5B C2 04 00",
  slotCounts = "8B 1C 9D ? ? ? ? 3B DA 89 74 24 14 89 74 24 18 C7 44 24 10 E8 03 00 00",
  groupLimit = "85 DB 8B 04 85 ? ? ? ? 89 44 24 1C 7E 7E",
  tribeIDs = "69 ED FA 1C 00 00 03 C5 8D 0C 45 ? ? ? ? 89 44 24 20",
  patrolLimit = "33 FF 3B C8 89 4C 24 30 89 4C 24 10 7E 04 89 44 24 10 83 7C 24 10 00",
  initial = "0F B7 06 66 3D 37 00 74 76 66 3D 1E 00 74 70 66 3D 05 00 74 6A 66 3D 27 00 74 64 66 3D 28 00 74 5E 66 3D 29 00 74 58 66 3D 3A 00 74 52 66 3D 3B 00 74 4C 66 3D 3C 00 74 46 66 3D 3D 00 74 40 66 3D 4D 00 74 3A 8B CD 69 C9 A4 02 00 00 83 BC 19 5C 01 00 00 00 74 20 66 3D 16 00 74 1A 66 3D 17 00 74 14 66 83 BE E0 02 00 00 00 74 0A 57 8B CB E8 ? ? ? ? EB 08 57 8B CB E8 ? ? ? ? 83 C7 01",
}

local PLAYER_STRIDE, UNIT_STRIDE = 0x39F4, 0x490
local function resolve()
  local sites = {}
  for key, pattern in pairs(PATTERNS) do
    local ok, address = pcall(core.AOBScan, pattern)
    if not ok then error("aiv-troop-spot-fix: cannot resolve behavior hook " .. key .. ": " .. tostring(address)) end
    sites[key] = address
  end
  local unitType = core.readInteger(sites.mapper + 13)
  local unitOwner = core.readInteger(sites.mapper + 24)
  local aiType = core.readInteger(sites.playerType + 11)
  local unitLimit = core.readInteger(sites.unitLimit + 11)
  local slotCounts = core.readInteger(sites.slotCounts + 3)
  local rowToTribe = core.readInteger(sites.groupLimit + 5)
  local tribeIDs = core.readInteger(sites.tribeIDs + 11)
  local tribeOwner = core.readInteger(sites.movement + 17)
  local tribeStride = core.readInteger(sites.movement + 11)
  if tribeStride ~= 0x334 and tribeStride ~= 0x688 then
    error("aiv-troop-spot-fix: unsupported tribe layout")
  end
  -- PlayerData: IDs 0x310C, UIDs 0x329C, rally hits 0x2B54.
  local tribeUIDs, rallyHits = tribeIDs + 0x190, tribeIDs - 0x5B8
  local game = {sites = sites}
  function game.ai(player)
    if player < 1 or player > 8 then return 0 end
    -- PlayerData stores Rat=2 .. Abbot=17; aicloader uses Rat=1 .. Abbot=16.
    local ai = core.readInteger(aiType + player * PLAYER_STRIDE) - 1
    if ai < 1 or ai > 16 then return 0 end
    return ai
  end
  function game.unit(id)
    if id < 1 or id >= core.readInteger(unitLimit) then return nil end
    local unit = core.readSmallInteger(unitType + id * UNIT_STRIDE)
    -- Recruiting units can still be peasants; mirror the engine's conversion lookup.
    if unit == 1 then unit = core.readSmallInteger(unitType + id * UNIT_STRIDE + 0x23C) end
    local player = core.readSmallInteger(unitOwner + id * UNIT_STRIDE)
    return unit, game.ai(player)
  end
  function game.slots(player, row)
    local count = core.readInteger(slotCounts + player * PLAYER_STRIDE + row * 4)
    return math.max(0, math.min(10, count))
  end
  function game.patrolGroups(this, ai)
    return core.readInteger(this + ai * 0x2A4 + 0x114)
  end
  function game.movementContext(tribe, row)
    if tribe < 1 or row < 1 or row > 19 then return nil end
    local player = core.readInteger(tribeOwner + tribe * tribeStride)
    local ai = game.ai(player)
    if ai == 0 then return nil end
    local first = core.readInteger(rowToTribe + row * 4)
    if first < 0 or first + 9 >= 200 then return nil end
    local uid = core.readInteger(tribeOwner + tribe * tribeStride + 8)
    for ordinal = 0, 9 do
      local index = first + ordinal
      if core.readSmallInteger(tribeIDs + player * PLAYER_STRIDE + index * 2) == tribe
          and core.readInteger(tribeUIDs + player * PLAYER_STRIDE + index * 4) == uid then
        return ai, ordinal, game.slots(player, row), core.readInteger(rallyHits + player * PLAYER_STRIDE)
      end
    end
  end
  return game
end

return {resolve = resolve, patterns = PATTERNS}
