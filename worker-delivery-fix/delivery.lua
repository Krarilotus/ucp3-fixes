-- Worker deliveries use the worker's region for the existing native building
-- entry check. The game still chooses the entrance and plans the actual route.
local PATTERNS = {
  accessible = "83 EC 0C 8B 44 24 10 85 C0 57 8B F9 89 7C 24 04 7F 09 33 C0",
  custom = "83 EC 08 8B 44 24 0C 85 C0 53 8B D9 89 5C 24 04 7F 09 33 C0",
  route = "6A 00 50 51 55 B9 ? ? ? ? E8 ? ? ? ? 85 C0 75 05 BB 01 00 00 00",
  heatmap = "0F BF 4E 02 83 3C 8D ? ? ? ? 00 75 3E 6A 00 57 B9 ? ? ? ? E8 ? ? ? ? 85 C0 75 07 66 C7 06 03 00 EB 12 83 F8 02 75 07 66 C7 06 03 00 EB 06 66 83 3E 03 75 14",
  row = "03 14 8D ? ? ? ? 0F B7 04 55 ? ? ? ? 66 85 C0",
  area = "0F BF 04 55 ? ? ? ? 3B C1 74 29 0F BF 96 E6 00 00 00",
  ox = "53 55 56 8B 35 ? ? ? ? 69 F6 90 04 00 00 0F BF 86 ? ? ? ? 0F BF 8E ? ? ? ? 33 ED 3B C5 57",
  afterOx = "51 53 8B 5C 24 0C 56 8B F3 69 F6 90 04 00 00 8B 86 ? ? ? ? 57",
  producers = "53 55 56 57 8B 3D ? ? ? ? 8B F7 69 F6 90 04 00 00 0F BF AE ? ? ? ? 0F BF 9E ? ? ? ? B9 0A 00 00 00",
  afterProducers = "51 8B 0D ? ? ? ? 8B C1 69 C0 90 04 00 00 53 55 0F BF A8 ? ? ? ? 89 6C 24 08",
  iron = "53 8B 1D ? ? ? ? 55 56 8B F3 69 F6 90 04 00 00 BD 05 00 00 00 33 D2",
  afterIron = "51 53 55 56 57 8B 3D ? ? ? ? 8B F7 69 F6 90 04 00 00 0F BF AE ? ? ? ? 0F BF 86 ? ? ? ?",
  storage = "53 55 56 8B 74 24 10 57 56 8B F9 E8 ? ? ? ? 83 F8 0A 0F 85 ? ? ? ?",
  armory = "8B 44 24 04 85 C0 57 8B F9 74 1B 8B 4C 24 14 8B 54 24 10 51",
  afterArmory = "83 EC 08 53 55 33 C0 8B E9 BB 01 00 00 00 39 5D 08",
}

local UNIT_STRIDE, BUILDING_STRIDE = 0x490, 0x32C
-- Stockpile (10) is exempt from this native keep-region check already.
local STORAGE_TYPES = {[11] = true, [19] = true}

local function unique(pattern, name)
  local address = core.AOBScan(pattern)
  assert(core.scanForAOB(pattern) == address
      and core.scanForAOB(pattern, address + 1) == nil,
    "worker-delivery-fix: ambiguous " .. name .. " binding")
  return address
end

local function signedShort(value)
  return value < 0x8000 and value or value - 0x10000
end

local function signedInteger(value)
  return value < 0x80000000 and value or value - 0x100000000
end

local function inRange(address, first, last)
  return first <= address and address < last
end

local function resolve()
  local sites = {}
  for name, pattern in pairs(PATTERNS) do
    if name ~= "row" then sites[name] = unique(pattern, name) end
  end
  -- The same row-index instruction occurs in the keep and custom resolvers.
  -- Select the occurrence inside the keep resolver, before the delivery gate.
  local row = core.AOBScan(PATTERNS.row)
  assert(inRange(row, sites.accessible, sites.route),
    "worker-delivery-fix: row lookup is outside the native keep check")
  local nextRow = core.scanForAOB(PATTERNS.row, row + 1)
  assert(nextRow and inRange(nextRow, sites.custom, sites.storage),
    "worker-delivery-fix: unexpected row lookup context")
  assert(inRange(sites.area, row, sites.route)
      and inRange(sites.route, sites.accessible, sites.custom)
      and sites.ox < sites.afterOx
      and sites.producers < sites.afterProducers
      and sites.iron < sites.afterIron
      and sites.storage < sites.armory
      and sites.armory < sites.afterArmory,
    "worker-delivery-fix: unsupported native layout")
  -- This call belongs to the AI building heatmap. Its result alone decides
  -- whether an otherwise valid store is marked for removal.
  assert(core.readInteger(sites.heatmap + 7) == core.readInteger(sites.route - 7)
      and sites.heatmap + 27 + signedInteger(core.readInteger(sites.heatmap + 23))
          == sites.accessible,
    "worker-delivery-fix: unexpected AI store accessibility call")

  -- These operands name existing native roots; no reference VA is retained.
  local currentSlot = core.readInteger(sites.producers + 6)
  local units = core.readInteger(sites.producers + 0x15) - 0x348
  local rowOffsets = core.readInteger(row + 3)
  local areas = core.readInteger(sites.area + 4)
  local maxUnitsAddress = units - 0x614
  assert(core.readInteger(sites.producers + 0x1C) - 0x338 == units
      and core.readInteger(nextRow + 3) == rowOffsets
      and core.readInteger(sites.ox + 5) == currentSlot
      and core.readInteger(sites.iron + 3) == currentSlot
      and core.readInteger(sites.afterIron + 7) == currentSlot
      and core.readInteger(maxUnitsAddress) <= 2500,
    "worker-delivery-fix: inconsistent unit state")

  local original = core.readBytes(sites.route, 5)
  assert(original[1] == 0x6A and original[2] == 0
      and original[3] == 0x50 and original[4] == 0x51
      and original[5] == 0x55,
    "worker-delivery-fix: native route call is occupied")
  return {
    sites = sites, currentSlot = currentSlot, units = units,
    maxUnitsAddress = maxUnitsAddress, rowOffsets = rowOffsets, areas = areas,
    original = original,
  }
end

local function install(native)
  local s = native.sites
  for i, byte in ipairs(native.original) do
    assert(core.readByte(s.route + i - 1) == byte,
      "worker-delivery-fix: route call changed after preflight")
  end
  local function workerDeliveryCaller(returnAddress)
    return inRange(returnAddress, s.ox, s.afterOx)
        or inRange(returnAddress, s.producers, s.afterProducers)
        or inRange(returnAddress, s.iron, s.afterIron)
        or inRange(returnAddress, s.storage, s.armory)
        or inRange(returnAddress, s.armory, s.afterArmory)
  end
  core.detourCode(function(r)
    -- Here the original function has already excluded a same-area entry and
    -- is about to ask whether the keep area can reach that entry. Its four
    -- original pushes and native pathfinder call remain unchanged.
    if r.EBX ~= 0 or not STORAGE_TYPES[core.readSmallInteger(r.ESI + 0xE6)] then
      return r
    end
    local caller = core.readInteger(r.ESP + 28)
    if caller == s.heatmap + 27 then
      -- The AI heatmap otherwise removes a usable store solely because its
      -- keep route is blocked. A valid entry remains a store; each worker's
      -- actual route is checked by the native movement code before delivery.
      -- Same-area queries are a native fast path, with no area graph search.
      if r.EAX > 0 then r.ECX = r.EAX end
      return r
    end
    if not workerDeliveryCaller(caller) then return r end
    local building = core.readInteger(r.ESP + 32)
    local buildings = core.readInteger(r.ESP + 16) -- saved `this`
    if building < 1 or building >= core.readInteger(buildings + 8)
        or r.ESI ~= buildings + building * BUILDING_STRIDE then return r end
    local slot = core.readInteger(native.currentSlot)
    local maxUnits = core.readInteger(native.maxUnitsAddress)
    if slot < 1 or slot >= maxUnits or maxUnits > 2500 then return r end
    local unit = native.units + slot * UNIT_STRIDE
    if core.readInteger(unit + 0x98) == 0
        or core.readSmallInteger(unit + 0x96) ~= core.readSmallInteger(r.ESI + 0xEA) then
      return r
    end
    local x, y = core.readSmallInteger(unit + 0xC4), core.readSmallInteger(unit + 0xC6)
    if x < 0 or y < 0 or x >= 400 or y >= 400 then return r end
    local tile = core.readInteger(native.rowOffsets + y * 12) + x
    if tile < 0 or tile >= 160000 then return r end
    local area = signedShort(core.readSmallInteger(native.areas + tile * 2))
    if area > 0 then r.ECX = area end
    return r
  end, s.route, 5)
end

return {resolve = resolve, install = install}
