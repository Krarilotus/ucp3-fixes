-- The scenario editor saves which troops can be recruited, which weapons can be made and which
-- goods can be traded with the map (MapPropertiesState: euro and mercenary troops at +0x582 and
-- +0x590, weapons at +0x59E, goods at +0x134D0). Every start loads them with the map, but:
--   commitBuildingAvailability, run by every start after loading, sets the saved archer flag to 1
--     when one of the map's first five buildings is allowed;
--   LaunchSkirmishGame (skirmish, multiplayer, trail missions) then allows every troop, weapon and
--     good again;
--   LaunchSinglePlayerGameUnk (Play a Map) applies troops and goods but allows every weapon again;
--   setupBuildingData starts every new fletcher on bows and every pole turner on spears, also
--     when only crossbows or pikes can be made.
-- This takes away what the map forbids. Nothing the game forbids itself is allowed again.
-- Campaign missions keep the game's behaviour.
local NAME = "scenario-settings-fix"

-- Its end: "cmp [level], 2 / jg / mov [flour], ebx", then the needed-goods flags.
local SKIRMISH_END = "83 3D ? ? ? ? 02 7F 06 89 1D ? ? ? ? 89 35 ? ? ? ? 89 35 ? ? ? ? 89 35 ? ? ? ? 89 35"
-- Its recruitable troops, euro and mercenary interleaved: "mov [euro], eax / mov [merc], eax"...
local SKIRMISH_UNITS = "A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? "
  .. "A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? A3 ? ? ? ? 89 44 24 10"
-- Play a Map's prologue (cdecl, one int: 0 starts a campaign mission).
local LAUNCHER = "81 EC E8 07 00 00 A1 ? ? ? ? 33 C4 89 84 24 E4 07 00 00 53 55 56 8B 35 ? ? ? ? 57 BF 01 00 00 00 6A 04 B9"
-- After loadMap: "cmp eax, 3" for the next jump, then the saved and the current value of every
-- weapon set to 1: crossbow, bow, pike, spear, sword, mace.
local LAUNCHER_RESET = "B9 ? ? ? ? E8 ? ? ? ? 8B 0D ? ? ? ? A1 ? ? ? ? 83 F8 03 89 0D ? ? ? ? 8B 0D ? ? ? ? "
  .. string.rep("66 89 3D ? ? ? ? 89 3D ? ? ? ? ", 6) .. "77"
-- Play a Map reads the map's mercenaries and euro troops.
local LAUNCHER_UNITS = "0F BF 0D ? ? ? ? 0F BF 15 ? ? ? ? 0F BF 35 ? ? ? ? 0F BF 3D ? ? ? ? 0F BF 05 ? ? ? ? 85 C0"
-- importTradingCosts: the map's goods to the current tradeable goods.
local TRADE = "56 57 33 FF 8D B1 ? ? ? ? 89 3D ? ? ? ? 89 3D ? ? ? ? C7 05 ? ? ? ? 0A 00 00 00 C7 05 ? ? ? ? 06 00 00 00 "
  .. "89 3D ? ? ? ? 89 3D ? ? ? ? B8 ? ? ? ? 33 C9 8D 49 00 8B 91 ? ? ? ? 89 90 C8 00 00 00 89 10 8B 91 ? ? ? ? "
  .. "89 90 CC 00 00 00 89 50 04 89 B9 ? ? ? ? 89 B9 ? ? ? ? 8B 16 89 91 ? ? ? ? 83 C0 08"
-- setupBuildingData: the product of a new pole turner or fletcher, then its next product. The
-- bytes Custom Skirmish Trails detours before it are left out.
local WORKSHOP = "66 89 84 37 A2 02 00 00 66 89 84 37 A4 02 00 00 E9 ? ? ? ? ? ? ? ? ? EB E4"
-- commitBuildingAvailability's loop: "cmp [table], -1" first, "mov ebx, base / sub ebx, id /
-- mov [map + ebx*2], ax" for a negative id. A table row is a key (-1 ends the table) and up to
-- nine ids (0 ends the row).
local COMMIT = "83 3D ? ? ? ? FF 8D 7D 01 0F 84 ? ? ? ? 8D 82 ? ? ? ? 53 33 C9 89 44 24 0C 56 8B 74 24 10 33 C0 "
  .. "66 39 06 8D B1 ? ? ? ? 0F 95 C0 8B 4E FC 85 C9 7E 0A 66 89 84 4A ? ? ? ? EB 11 7D 5D 85 C0 74 0B "
  .. "BB ? ? ? ? 2B D9 66 89 04 5A"

local SKIRMISH_SITE, SKIRMISH_SIZE = 0x0F, 6
local RESET_SITE, RESET_SIZE, PAIR = 0x24, 7, 13
local RESET_FROM_LAUNCHER = 0x15C
local WORKSHOP_SITE, WORKSHOP_SIZE = 8, 8
local COMMIT_ROWS, COMMIT_BASE, ROW, IDS = 2, 72, 40, 9
local EURO_SAVE, MERC_SAVE, WEAPON_SAVE = 0x582, 0x590, 0x59E
local BOW, CROSSBOW, SPEAR, PIKE = 0x11, 0x12, 0x13, 0x14

local SKIRMISH = [[
  pushfd
  push ecx
  push edx
  xor ecx, ecx
troops:
  cmp word [EURO_SAVE + ecx*2], 0
  jne euro_kept
  mov dword [EURO + ecx*4], 0
euro_kept:
  cmp word [MERC_SAVE + ecx*2], 0
  jne merc_kept
  mov dword [MERC + ecx*4], 0
merc_kept:
  inc ecx
  cmp ecx, 7
  jb troops
  xor ecx, ecx
weapons:
  cmp word [WEAPON_SAVE + ecx*2], 0
  jne weapon_kept
  mov edx, [weapon_now + ecx*4]
  mov dword [edx], 0
weapon_kept:
  inc ecx
  cmp ecx, 6
  jb weapons
  xor ecx, ecx
goods:
  cmp dword [GOODS_SAVE + ecx*4], 0
  jne good_kept
  mov dword [GOODS + ecx*4], 0
good_kept:
  inc ecx
  cmp ecx, 25
  jb goods
  pop edx
  pop ecx
  popfd
]]
-- The current values of the six weapons, in the order of their saved values.
local SKIRMISH_DATA = "weapon_now dd NOW1, NOW2, NOW3, NOW4, NOW5, NOW6\n"

local LAUNCHER_KEEP = [[
  cmp dword [esp + PARAM], 0
  je reset
  cmp eax, 3
  jmp KEEP
reset:
  cmp eax, 3
]]

local WORKSHOP_PRODUCT = [[
  pushfd
  cmp ax, BOW
  jne pole_turner
  cmp dword [BOW_NOW], 0
  jne chosen
  cmp dword [CROSSBOW_NOW], 0
  je chosen
  mov ax, CROSSBOW
  jmp changed
pole_turner:
  cmp ax, SPEAR
  jne chosen
  cmp dword [SPEAR_NOW], 0
  jne chosen
  cmp dword [PIKE_NOW], 0
  je chosen
  mov ax, PIKE
changed:
  mov word [edi + esi + 0x2A2], ax
chosen:
  popfd
]]

local function find(pattern, purpose)
  local ok, address = pcall(core.AOBScan, pattern)
  if not ok or address == nil then
    error(NAME .. ": cannot locate " .. purpose)
  end
  local duplicate = core.scanForAOB(pattern, address + 1)
  if duplicate and duplicate ~= 0 then
    error(NAME .. ": " .. purpose .. " matches more than once")
  end
  return address
end

local function bytes(address, size)
  local out = {}
  for i = 1, size do out[i] = core.readByte(address + i - 1) & 0xFF end
  return out
end

local function check(condition, purpose)
  if not condition then error(NAME .. ": unsupported " .. purpose) end
end

local function prepare()
  local skirmish = find(SKIRMISH_END, "the skirmish start's availability reset") + SKIRMISH_SITE
  local units = find(SKIRMISH_UNITS, "the skirmish start's recruitable troops")
  local launcher = find(LAUNCHER, "Play a Map's launcher")
  local reset = find(LAUNCHER_RESET, "Play a Map's weapon reset")
  local saved = find(LAUNCHER_UNITS, "Play a Map's recruitable troops")
  local trade = find(TRADE, "the map's tradeable goods")
  local workshop = find(WORKSHOP, "the new workshops' products") + WORKSHOP_SITE
  local commit = find(COMMIT, "the start's building availability")

  local map = core.readInteger(reset + 1)
  local site = reset + RESET_SITE
  check(site - launcher == RESET_FROM_LAUNCHER, "Play a Map launcher")
  local now = {}
  for i = 0, 5 do
    check(core.readInteger(site + PAIR * i + 3) == map + WEAPON_SAVE + 2 * i, "weapon layout")
    now[i + 1] = core.readInteger(site + PAIR * i + 9)
  end
  check(core.readInteger(saved + 31) == map + EURO_SAVE and core.readInteger(saved + 3) == map + MERC_SAVE,
    "troop layout")

  local hooks = {
    { site = skirmish, size = SKIRMISH_SIZE, script = SKIRMISH, data = SKIRMISH_DATA, values = {
      EURO_SAVE = map + EURO_SAVE, MERC_SAVE = map + MERC_SAVE, WEAPON_SAVE = map + WEAPON_SAVE,
      EURO = core.readInteger(units + 1), MERC = core.readInteger(units + 6),
      NOW1 = now[1], NOW2 = now[2], NOW3 = now[3], NOW4 = now[4], NOW5 = now[5], NOW6 = now[6],
      GOODS_SAVE = map + core.readInteger(trade + 6), GOODS = core.readInteger(trade + 109),
    } },
    { site = site, size = RESET_SIZE, script = LAUNCHER_KEEP, values = {
      PARAM = core.readInteger(launcher + 2) + 4 * 4 + 4, KEEP = site + PAIR * 6,
    } },
    { site = workshop, size = WORKSHOP_SIZE, script = WORKSHOP_PRODUCT, values = {
      BOW = BOW, CROSSBOW = CROSSBOW, SPEAR = SPEAR, PIKE = PIKE,
      CROSSBOW_NOW = now[1], BOW_NOW = now[2], PIKE_NOW = now[3], SPEAR_NOW = now[4],
    } },
  }
  -- The building table's ids that set the saved archer flag end their rows instead.
  local archer = core.readInteger(commit + COMMIT_BASE) - EURO_SAVE // 2
  local row = core.readInteger(commit + COMMIT_ROWS)
  local links = #hooks
  while core.readInteger(row) ~= -1 do
    for i = 1, IDS do
      local id = core.readInteger(row + 4 * i)
      if id == 0 then break end
      if id == archer then
        check(i == IDS or core.readInteger(row + 4 * i + 4) == 0, "building table")
        hooks[#hooks + 1] = { site = row + 4 * i, size = 4, patch = { 0, 0, 0, 0 } }
      end
    end
    row = row + ROW
  end
  check(#hooks > links, "building table")
  for _, hook in ipairs(hooks) do hook.original = bytes(hook.site, hook.size) end

  return function()
    local written = {}
    local ok, message = pcall(function()
      for _, hook in ipairs(hooks) do
        local original = bytes(hook.site, hook.size)
        for i, byte in ipairs(hook.original) do
          check(original[i] == byte, "code at 0x" .. string.format("%X", hook.site) .. " changed after preflight")
        end
        local patch = hook.patch
        if not patch then
          hook.values.RESUME = hook.site + hook.size
          local cave = core.allocateAssembly(hook.script .. "  db " .. table.concat(original, ", ")
            .. "\n  jmp RESUME\n" .. (hook.data or ""), hook.values)
          patch = { 0xE9, core.itob(core.getRelativeAddress(hook.site, cave, -5)) }
          for _ = 6, hook.size do patch[#patch + 1] = 0x90 end
        end
        core.writeCode(hook.site, patch)
        written[#written + 1] = hook
      end
    end)
    if not ok then
      for i = #written, 1, -1 do core.writeCode(written[i].site, written[i].original) end
      error(message, 0)
    end
  end
end

return { prepare = prepare }
