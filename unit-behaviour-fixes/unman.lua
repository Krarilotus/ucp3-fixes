-- Preserve the native exit-equipment command, but never detach a reused slot.
local dispatchPattern = "8D 41 FD 83 F8 23 89 7C 24 10 89 5C 24 28 89 54 24 1C " ..
  "89 54 24 24 89 54 24 20 89 6C 24 18 66 89 95 ? ? ? ? 66 89 95 ? ? ? ? " ..
  "0F 87 ? ? ? ? 0F B6 80 ? ? ? ? FF 24 85 ? ? ? ?"
local tailPattern = "0F BF 93 ? ? ? ? 83 C0 01 3B C2 89 44 24 34 0F 8C ? ? ? ? " ..
  "8B 44 24 38 50 B9 ? ? ? ? 66 C7 83 ? ? ? ? 00 00"
local function prepare()
  local dispatch = core.AOBScan(dispatchPattern)
  assert(core.scanForAOB(dispatchPattern) == dispatch
      and core.scanForAOB(dispatchPattern, dispatch + 1) == nil,
    "unit-behaviour-fixes: ambiguous command dispatch")
  local extreme = data.version.isExtreme()
  assert(core.readInteger(dispatch - 33) == (extreme and 0x688 or 0x334),
    "unit-behaviour-fixes: incompatible command group layout")
  local cases = core.readInteger(dispatch + 0x35)
  local targets = core.readInteger(dispatch + 0x3C)
  local entry = core.readInteger(targets + core.readByte(cases + 17 - 3) * 4)
  local failure = dispatch + 0x32 + core.readInteger(dispatch + 0x2E)
  assert(entry > dispatch and entry < failure,
    "unit-behaviour-fixes: exit-equipment case is outside its command owner")
  local function matches(address, expected)
    for i, byte in ipairs(expected) do
      assert(core.readByte(address + i - 1) == byte,
        "unit-behaviour-fixes: incompatible exit-equipment context")
    end
  end
  matches(entry, {0x8B,0x44,0x24,0x40,0xF7,0xD8,0x1B,0xC0,0x83,0xE0,0x10})
  matches(entry + 0x3C, {0x39,0x93})
  matches(entry + 0x42, {0x0F,0x85})
  assert(entry + 0x48 + core.readInteger(entry + 0x44) == failure,
    "unit-behaviour-fixes: incompatible engine identity guard")
  local root = core.readInteger(entry + 0x3E) - 0x98
  local loop = entry + 0x71
  matches(loop, {0x8B,0x44,0x24,0x30,0x0F,0xBF,0x30,0x66,0x8B,0x54,0x24,0x28,
    0x89,0x74,0x24,0x20,0x69,0xF6,0x90,0x04,0,0,0x33,0xC9,0x66,0x89,0x08})
  local site = loop + 27
  matches(site, {0x66,0x89,0x8E})
  assert(core.readInteger(site + 3) == root + 0x3C0
      and core.readInteger(entry + 0x54) == root + 0x3B4
      and core.readInteger(entry + 0x69) == root + 0x314,
    "unit-behaviour-fixes: inconsistent exit-equipment record layout")
  local tail = core.AOBScan(tailPattern)
  assert(tail > site and tail + 41 < failure
      and core.scanForAOB(tailPattern) == tail
      and core.scanForAOB(tailPattern, tail + 1) == nil
      and tail + 22 + core.readInteger(tail + 18) == loop
      and core.readInteger(tail + 3) == root + 0x3B4,
    "unit-behaviour-fixes: incompatible exit-equipment continuation")
  local original = core.readBytes(site, 7)
  local contexts = {
    {dispatch, core.readBytes(dispatch, 64)},
    {entry, core.readBytes(entry, site + 7 - entry)},
    {tail, core.readBytes(tail, 41)},
  }
  local code = {
    0x9C,0x50,0x51,                       -- preserve flags, EAX and ECX
    0x85,0xF6,0x0F,0x8E,core.relTo("invalid", -4),
    0x81,0xFE,core.itob((extreme and 10000 or 2500) * 0x490),
    0x0F,0x83,core.relTo("invalid", -4), -- reject empty/negative/out-of-pool IDs
    0x8B,0x44,0x24,0x40,                 -- original crew index at stack+0x34
    0x8B,0x8E,core.itob(root + 0x98),
    0x3B,0x8C,0x83,core.itob(root + 0x31C),
    0x0F,0x85,core.relTo("invalid", -4),
    0x59,0x58,0x9D,original,
    0xE9,core.relTo("done", -4),
    "invalid",0x59,0x58,0x9D,
    -- The original engine ID entry was already cleared. Advance its cursor,
    -- skipping all writes to the invalid unit, including the final two writes.
    0x8B,0x44,0x24,0x34,0x83,0x44,0x24,0x30,0x02,
    0xE9,core.relTo(tail, -4),
    "done",
  }
  local applied = false
  return function()
    if applied then return end
    for _, context in ipairs(contexts) do matches(context[1], context[2]) end
    core.insertCode(site, 7, code)
    applied = true
  end
end
return {prepare = prepare}
