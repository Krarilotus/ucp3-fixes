-- Keep native deer enumeration, line of sight, pathfinding and projectile logic.
-- The hunter may approach a blocked target along its existing native path.
local selectorPattern = "89 44 24 14 89 54 24 1C 89 4C 24 18 " ..
  "C7 44 24 24 14 00 00 00 EB 0B"
local movementPattern = "83 3D ? ? ? ? 14 7F 0B A1 ? ? ? ? 50 " ..
  "E9 ? ? ? ? 83 FF 1E 8B 35 ? ? ? ? 7E 21"
local passPattern = "8B 44 24 14 85 C0 75 14 83 7C 24 24 14 75 0D " ..
  "C7 44 24 24 05 00 00 00 E9 ? ? ? ?"
local sightPattern = "83 C0 FF 3D AF 01 00 00 77 13 A1 ? ? ? ? " ..
  "3B 44 24 10 7D 08 89 44 24 10"
local reachedPattern = "83 FF 1E 8B 35 ? ? ? ? 7E 21 56 B9 ? ? ? ? " ..
  "E8 ? ? ? ? 85 C0 74 12 69 F6 90 04 00 00"
local stepPattern = "83 FF 20 7E 1E 69 F6 90 04 00 00 5F " ..
  "C7 86 ? ? ? ? 81 00 00 00 66 C7 86 ? ? ? ? 04 00 5E 5D 5B C3"
local failedShotPattern = "56 B9 ? ? ? ? 66 C7 80 ? ? ? ? 04 00 " ..
  "E8 ? ? ? ? 85 C0 A1 ? ? ? ? 0F 84 ? ? ? ? 8B C8 69 C9 90 04 00 00"

local function unique(pattern, name)
  local address = core.AOBScan(pattern)
  assert(core.scanForAOB(pattern) == address
      and core.scanForAOB(pattern, address + 1) == nil,
    "hunter-targeting-fix: ambiguous " .. name)
  return address
end

local function signedInteger(value)
  return value < 0x80000000 and value or value - 0x100000000
end

local function prepare()
  local selector = unique(selectorPattern, "deer selector") + 16
  local movement = unique(movementPattern, "hunter movement") + 6
  local pass = unique(passPattern, "deer selection passes")
  local sight = unique(sightPattern, "deer line of sight") + 3
  local reached = unique(reachedPattern, "native path completion")
  local step = unique(stepPattern, "native walking step") + 5
  local failed = unique(failedShotPattern, "blocked shot") + 27
  local units = core.readInteger(reached + 13)
  local destinationReached = reached + 22 + signedInteger(core.readInteger(reached + 18))
  local fallback = failed + 6 + signedInteger(core.readInteger(failed + 2))
  assert(selector < sight and sight < pass and pass < reached
      and reached < step and step < failed and failed - fallback > 0x100
      and core.readInteger(failed - 25) == units
      and core.readByte(selector) == 20 and core.readByte(movement) == 20
      and core.readByte(pass + 12) == 20 and core.readByte(pass + 19) == 5
      and core.readByte(sight) == 0x3D and core.readByte(failed) == 0x0F
      and core.readByte(failed + 1) == 0x84,
    "hunter-targeting-fix: unsupported native hunter layout")
  local originals = {
    selector = core.readByte(selector), movement = core.readByte(movement),
    pass = core.readBytes(pass + 12, 8),
    sight = core.readBytes(sight, 7), failed = core.readBytes(failed, 6),
  }
  local applied = false
  return function()
    if applied then return end
    assert(core.readByte(selector) == originals.selector
      and core.readByte(movement) == originals.movement,
      "hunter-targeting-fix: range checks changed after preflight")
    for i, byte in ipairs(originals.pass) do
      assert(core.readByte(pass + 11 + i) == byte,
        "hunter-targeting-fix: selection pass changed after preflight")
    end
    for i, byte in ipairs(originals.sight) do
      assert(core.readByte(sight + i - 1) == byte,
        "hunter-targeting-fix: sight check changed after preflight")
    end
    for i, byte in ipairs(originals.failed) do
      assert(core.readByte(failed + i - 1) == byte,
        "hunter-targeting-fix: blocked-shot branch changed after preflight")
    end
    -- The first pass keeps native sight/range admission at any positive
    -- distance. The second pass considers blocked deer beyond one tile.
    core.writeCodeByte(selector, 0)
    core.writeCodeByte(movement, 0)
    core.writeCodeByte(pass + 12, 0)
    core.writeCodeByte(pass + 19, 1)
    core.insertCode(sight, 5, {
      0x83, 0x7C, 0x24, 0x24, 0x01, -- second selection pass?
      0x74, 0x07,                   -- yes: accept a blocked candidate
      {table.unpack(originals.sight, 1, 5)},
      0xEB, 0x02,
      0x33, 0xC0,                   -- clears the native JA condition
    })
    -- Recheck each update and abandon the target if the native path ends or
    -- the hunter comes within three tiles without a clear shot.
    core.insertCode(failed, 6, {
      0x0F, 0x85, core.relTo(failed + 6, -4),
      0x83, 0xFF, 0x03,
      0x0F, 0x8E, core.relTo(fallback, -4),
      0x56, 0xB9, core.itob(units), core.callTo(destinationReached),
      0x85, 0xC0,
      0x0F, 0x85, core.relTo(fallback, -4),
      core.jmpTo(step), -- native walking-speed block and return
    })
    applied = true
  end
end

return {prepare = prepare}
