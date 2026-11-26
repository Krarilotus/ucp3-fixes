-- Gatehouse occupancy already uses the native tile unit list and troop values.
-- Exclude a unit once native death starts, as the game's living-unit census does.
local pattern = "69 F6 90 04 00 00 66 83 BE ? ? ? ? 00 74 54 " ..
  "0F BF 86 ? ? ? ? 0F BF BE ? ? ? ? 50 B9 ? ? ? ? E8 ? ? ? ? " ..
  "8B 1D ? ? ? ? 01 44 BC 38"

-- The end of the executable section that holds an address, from the PE header of the image
-- around it, which starts on a 64 KiB boundary below the address.
local function sectionEnd(address)
  local base = address - address % 0x10000
  while base > 0 do
    local header = base + core.readInteger(base + 0x3C)
    if (core.readInteger(base) & 0xFFFF) == 0x5A4D and header > base and header < base + 0x1000
        and core.readInteger(header) == 0x4550 then
      local section = header + 0x18 + (core.readInteger(header + 0x14) & 0xFFFF)
      for _ = 1, core.readInteger(header + 6) & 0xFFFF do
        local first = base + core.readInteger(section + 12)
        local stop = first + core.readInteger(section + 8)
        if address >= first and address < stop and core.readInteger(section + 36) & 0x20000000 ~= 0 then
          return stop
        end
        section = section + 40
      end
      break
    end
    base = base - 0x10000
  end
  error(string.format("gatehouse-capture-fix: no executable section holds 0x%X", address))
end

local function prepare()
  local block = core.AOBScan(pattern)
  local stop = sectionEnd(block)
  local again = core.scanForAOB(pattern, block + 1, stop - 1)
  assert(again == nil or again == 0 or again >= stop,
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
