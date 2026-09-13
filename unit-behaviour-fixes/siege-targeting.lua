-- Catapult/trebuchet unit attacks become ground shots. That native command
-- branch omits the path cleanup used by ground/wall attacks and other shooters.
local attackPattern = "C6 86 ? ? ? ? 05 66 C7 86 ? ? ? ? 05 00 " ..
  "66 8B 83 ? ? ? ? 66 89 86 ? ? ? ? 66 8B 8B ? ? ? ? 66 89 8E ? ? ? ? " ..
  "66 C7 86 ? ? ? ? 0B 00 66 C7 86 ? ? ? ? 0A 00"
local groundPattern = "66 89 96 ? ? ? ? 66 89 8E ? ? ? ? 66 89 8E ? ? ? ? " ..
  "50 B9 ? ? ? ? E8 ? ? ? ? 66 C7 86 ? ? ? ? 0A 00"
local dispatchPattern = "0F BF 8E ? ? ? ? 83 C1 FB 83 F9 48 0F 87 ? ? ? ? " ..
  "0F B6 89 ? ? ? ? FF 24 8D ? ? ? ? 8B 54 24 3C 50 B9 ? ? ? ? " ..
  "66 C7 86 ? ? ? ? 04 00 66 89 BE ? ? ? ? 89 96 ? ? ? ? C6 86 ? ? ? ? 00 E8 ? ? ? ?"
local stopBody = {0x8B,0x44,0x24,0x04,0x69,0xC0,0x90,0x04,0,0,0x03,0xC1,0x33,0xC9,
  0x66,0x89,0x88,0x0E,0x07,0,0,0x66,0x89,0x88,0x10,0x07,0,0,
  0x66,0x89,0x88,0xE6,0x08,0,0,0x66,0x89,0x88,0xA8,0x08,0,0,0xC2,0x04,0}

local function prepare()
  -- unit-handlers.find owns type-update functions; this site belongs to the
  -- synchronized tribe-command dispatcher, outside that owner's boundaries.
  local sites = {}
  for i, pattern in ipairs({attackPattern, groundPattern, dispatchPattern}) do
    local address = core.AOBScan(pattern)
    assert(core.scanForAOB(pattern) == address
        and core.scanForAOB(pattern, address + 1) == nil,
      "unit-behaviour-fixes: ambiguous siege attack command")
    local _, size = pattern:gsub("%S+", "")
    sites[i] = {address = address, original = core.readBytes(address, size)}
  end
  local attack, ground = sites[1].address, sites[2].address
  local units = core.readInteger(ground + 23)
  local root = units + 0x614
  local dispatch = sites[3].address
  assert(core.readInteger(dispatch + 3) == root + 0x8E,
    "unit-behaviour-fixes: inconsistent attack dispatch layout")
  local selectors, branches = core.readInteger(dispatch + 22), core.readInteger(dispatch + 29)
  for kind = 5, 77 do
    local selector = core.readByte(selectors + kind - 5)
    assert(selector < 5, "unit-behaviour-fixes: incompatible attack dispatch selector")
    local target = core.readInteger(branches + selector * 4)
    assert((target == attack) == (kind == 39 or kind == 40),
      "unit-behaviour-fixes: unexpected owner of siege attack branch")
  end
  sites[4] = {address = selectors, original = core.readBytes(selectors, 73)}
  sites[5] = {address = branches, original = core.readBytes(branches, 20)}
  for _, field in ipairs({{2,0x3C5},{10,0x39C},{19,0xC4},{26,0x3E8},
      {33,0xC6},{40,0x3EA},{47,0x3A4},{56,0x3D8}}) do
    assert(core.readInteger(attack + field[1]) == root + field[2],
      "unit-behaviour-fixes: inconsistent siege attack layout")
  end
  for _, field in ipairs({{3,0x3A4},{10,0xF0},{17,0xF2},{35,0x3D8}}) do
    assert(core.readInteger(ground + field[1]) == root + field[2],
      "unit-behaviour-fixes: inconsistent ground attack layout")
  end
  local stop = ground + 32 + core.readInteger(ground + 28)
  for i, byte in ipairs(stopBody) do
    assert(core.readByte(stop + i - 1) == byte,
      "unit-behaviour-fixes: incompatible native path cleanup ABI")
  end
  sites[6] = {address = stop, original = stopBody}
  local applied = false
  return function()
    if applied then return end
    for _, site in ipairs(sites) do
      for i, byte in ipairs(site.original) do
        assert(core.readByte(site.address + i - 1) == byte,
          "unit-behaviour-fixes: incompatible or changed siege command binding")
      end
    end
    -- EAX is still the selected unit ID at this branch entry. Preserve flags
    -- and all registers, call the existing thiscall/RET4 owner once, then replay
    -- the displaced command write. Native movement finishes its current step;
    -- the original engine state machine retains aiming, reload and release.
    core.insertCode(attack, 7, {
      0x9C, 0x60, 0x50, 0xB9, core.itob(units), core.callTo(stop), 0x61, 0x9D,
      {table.unpack(sites[1].original, 1, 7)},
    })
    applied = true
  end
end
return {prepare = prepare}
