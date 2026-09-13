-- The original engine handlers retain ownership of crew records and casualties.
-- Prepare all bindings before applying any patch. This is a draft correction;
-- native lifecycle and collection integration acceptance are recorded in docs.
local guards = {
  {39, "39 AE ? ? ? ? 0F 85 93 00 00 00 66 39 AE ? ? ? ? 0F 85 86 00 00 00"},
  {40, "39 96 ? ? ? ? 0F 85 8B 00 00 00 66 39 96 ? ? ? ? 0F 85 7E 00 00 00"},
  {41, "39 BE ? ? ? ? 0F 85 83 00 00 00 66 39 BE ? ? ? ? 75 7A"},
  {58, "39 9E ? ? ? ? 0F 85 8D 00 00 00 66 39 9E ? ? ? ? 0F 85 80 00 00 00"},
  {59, "39 96 ? ? ? ? 0F 85 85 00 00 00 66 39 96 ? ? ? ? 0F 85 78 00 00 00"},
  {60, "39 90 ? ? ? ? 0F 85 8E 00 00 00 66 83 B8 ? ? ? ? 00 0F 85 80 00 00 00"},
  {61, "39 BE ? ? ? ? 0F 85 87 00 00 00 66 39 BE ? ? ? ? 75 7E"},
  {77, "39 AE ? ? ? ? 0F 85 8F 00 00 00 66 39 AE ? ? ? ? 0F 85 82 00 00 00"},
}
-- Fatal-health guard through native dying initialization and its thiscall RET12.
-- This interior context remains independent of AIC's five-byte entry observer.
local firePattern = "39 9E DC 09 00 00 66 89 86 4C 06 00 00 0F 8F 4A 01 00 00 " ..
  "66 83 FF 37 89 9E C4 08 00 00 66 89 AE 56 0A 00 00 75 2C " ..
  "5F 66 89 AE B4 08 00 00 66 89 AE 0A 07 00 00 8B C5 5D " ..
  "89 9E DC 09 00 00 89 9E C4 08 00 00 66 C7 86 D4 08 00 00 72 00 5E 5B C2 0C 00"

local function prepare(native)
  native = native or require("unit-handlers").resolve()
  local sites, recordRoot = {}, nil
  for _, guard in ipairs(guards) do
    local kind, pattern = guard[1], guard[2]
    local address = native.find(kind, pattern, 25)
    local cycle = core.readInteger(address + 2)
    local killed = core.readInteger(address + 15)
    local root = cycle - 0x2B0
    assert(killed == root + 0x3F0 and (not recordRoot or recordRoot == root),
      "unit-behaviour-fixes: inconsistent native crew layout")
    recordRoot = root
    local operand = kind == 60 and 0x90 or 0x96 -- [eax+disp32] or [esi+disp32], EDX
    sites[#sites + 1] = {address = address, size = 6, guard = true,
      original = core.readBytes(address, 25), code = {
      0x52,                         -- push edx
      0x8B, operand, core.itob(root + 0x50), -- mov edx, [animationAdvanced]
      0x39, operand, core.itob(cycle),       -- cmp [animationCycle], edx
      0x5A,                         -- pop edx (preserves comparison flags)
    }}
  end
  local fire = core.AOBScan(firePattern)
  assert(core.scanForAOB(firePattern) == fire
      and core.scanForAOB(firePattern, fire + 1) == nil,
    "unit-behaviour-fixes: ambiguous fatal fire initialization")
  local fireSite, fireCode = fire + 19, {}
  local dyingTypes = {55, 39, 40, 41, 58, 59, 60, 61, 77}
  for index, kind in ipairs(dyingTypes) do
    -- Preserve every register; only ZF selects the existing native death branch.
    fireCode[#fireCode + 1] = {0x66, 0x83, 0xFF, kind, 0x74, (#dyingTypes - index) * 6}
  end
  -- Retain the displaced cycle reset verbatim. No relative operand is moved.
  fireCode[#fireCode + 1] = core.readBytes(fireSite + 4, 6)
  sites[#sites + 1] = {address = fireSite, size = 10,
    original = core.readBytes(fireSite, 49), code = fireCode}
  local applied = false
  return function()
    if applied then return end
    for _, site in ipairs(sites) do
      for index, byte in ipairs(site.original) do
        assert(core.readByte(site.address + index - 1) == byte,
          "unit-behaviour-fixes: crew guard changed after preparation")
      end
    end
    for _, site in ipairs(sites) do
      core.insertCode(site.address, site.size, site.code)
      -- Keep the existing branch destination and complete native cleanup loop.
      -- Zero remains eligible after the generic death-action reset; one is
      -- eligible only when it advanced this tick. Later frames cannot repeat it.
      if site.guard then core.writeCodeByte(site.address + 7, 0x87) end -- JNE -> unsigned JA
    end
    applied = true
  end
end

return {prepare = prepare}
