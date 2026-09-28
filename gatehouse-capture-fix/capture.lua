-- Gatehouse occupancy already uses the native tile unit list and troop values.
-- Exclude a unit once native death starts, as the game's living-unit census does.
local pattern = "69 F6 90 04 00 00 66 83 BE ? ? ? ? 00 74 54 " ..
  "0F BF 86 ? ? ? ? 0F BF BE ? ? ? ? 50 B9 ? ? ? ? E8 ? ? ? ? " ..
  "8B 1D ? ? ? ? 01 44 BC 38"

local function prepare()
  local block = core.AOBScan(pattern)
  assert(core.scanForAOB(pattern) == block
      and core.scanForAOB(pattern, block + 1) == nil,
    "gatehouse-capture-fix: ambiguous native occupancy check")
  local site = block + 6
  local original = core.readBytes(site, 10)
  assert(original[1] == 0x66 and original[2] == 0x83 and original[3] == 0xBE
      and original[8] == 0 and original[9] == 0x74,
    "gatehouse-capture-fix: occupied native occupancy check")
  local selectable = core.readInteger(site + 3)
  local dying = selectable - 4 -- Native Unit fields 0x2A4 and 0x2A0.
  local skip = site + 10 + original[10]
  assert(original[10] == 0x54 and core.readByte(skip) == 0x0F,
    "gatehouse-capture-fix: unsupported gatehouse branch")
  local applied = false
  return function()
    if applied then return end
    for i, byte in ipairs(original) do
      assert(core.readByte(site + i - 1) == byte,
        "gatehouse-capture-fix: occupancy check changed after preflight")
    end
    -- Preserve the original selectable test and its branch. A dying unit takes
    -- the same skip branch, so no troop value or owner presence is recorded.
    core.insertCode(site, 8, {
      0x66, 0x83, 0xBE, core.itob(dying), 0,
      0x0F, 0x85, core.relTo(skip, -4),
      {table.unpack(original, 1, 8)},
    })
    applied = true
  end
end

return {prepare = prepare}
