-- Idle tunnelers must advertise melee-response eligibility to the original
-- enemy-notice consumer. Group stance, range, orders and target choice stay native.
local patterns = {
  {14, "BF 05 00 00 00 66 3B D7 0F 85 ? ? ? ? 89 BE ? ? ? ? 89 9E ? ? ? ? 66 C7 86 ? ? ? ? 0A 00 0F B7 86 ? ? ? ? 66 3B C3"},
  {12, "66 83 FA 06 0F 85 ? ? ? ? 84 C8 89 BE ? ? ? ? 89 9E ? ? ? ? 66 C7 86 ? ? ? ? 0A 00 75 15"},
}
local function prepare(native)
  native = native or require("unit-handlers").resolve()
  local first = native.entries[5]
  local prefix = core.readBytes(first, 20)
  local expected = {0x51, 0x8B, 0x0D}
  for i, byte in ipairs(expected) do assert(prefix[i] == byte,
    "unit-behaviour-fixes: incompatible tunneler handler") end
  local head = core.readBytes(first + 7, 13)
  local context = {0x8B, 0xC1, 0x69, 0xC0, 0x90, 0x04, 0, 0, 0x53, 0x55, 0x0F, 0xBF, 0xA8}
  for i, byte in ipairs(context) do assert(head[i] == byte,
    "unit-behaviour-fixes: incompatible tunneler record context") end
  local root = core.readInteger(first + 20) - 0x96
  local sites = {}
  for _, item in ipairs(patterns) do
    local _, size = item[2]:gsub("%S+", "")
    local match = native.find(5, item[2], size)
    local address = match + item[1]
    assert(core.readInteger(address + 2) == root + 0x44
        and core.readInteger(address + 8) == root + 0x30
        and core.readInteger(address + 15) == root + 0x2AC,
      "unit-behaviour-fixes: inconsistent tunneler idle layout")
    local original = core.readBytes(address, 6)
    sites[#sites + 1] = {address = address, original = original, code = {
      0x66, 0xC7, 0x86, core.itob(root + 0x3FC), 0x01, 0x00,
      original,
    }}
  end
  local applied = false
  return function()
    if applied then return end
    for _, site in ipairs(sites) do
      for i, byte in ipairs(site.original) do
        assert(core.readByte(site.address + i - 1) == byte,
          "unit-behaviour-fixes: tunneler idle handler changed after preparation")
      end
    end
    for _, site in ipairs(sites) do core.insertCode(site.address, 6, site.code) end
    applied = true
  end
end
return {prepare = prepare}
