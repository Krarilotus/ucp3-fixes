--[[
  Route Search (route-search): one owner for a unit's route search.

  UnitsState::setDestinationForUnit asks PathFindingState::doPathfinding(owner, canClimb)
  for a unit's route through one five-byte call. That function is thiscall: ecx is the
  PathFindingState, the two arguments are on the stack, it returns with ret 8 and eax is the
  route length (0 or less: no route). esi holds the unit there (UnitsState + index * 0x490).

  Modules that change how a unit's route is searched register a policy here instead of each
  redirecting that call on their own. This module redirects it once, to a short stub that
  runs the enabled policies in a fixed order around the game's own search, and keeps the
  unit where every policy can read it.

  Installed alone it changes nothing: the call is redirected when the first policy is
  enabled. README.md documents the contract (calling convention, order bands, lifecycle).
]]

local NAME = "route-search"

-- The contract version. Additive changes keep it; a change existing policies would notice
-- raises it.
local CONTRACT = 1

-- setDestinationForUnit: movsx ecx, word [esi + owner] / mov eax, [esp + 0x14] (canClimb) /
-- push eax / push ecx / mov ecx, PathFindingState / call doPathfinding / cmp eax, ebx /
-- mov [climb flag], ebx / jle <no route>. ebx is 0 there.
local SITE = "0F BF 8E AA 06 00 00 8B 44 24 14 50 51 B9 ? ? ? ? E8 ? ? ? ? 3B C3 89 1D ? ? ? ? 0F 8E"
local SITE_CALL = 18

-- PathFindingState::doPathfinding, from its first instruction to its first return: it
-- compares the start and target tiles' areas and gives up with xor eax, eax / ret 8.
local SEARCH = "56 8B F1 8B 46 0C 8B 4E 14 8D 04 40 8B 04 85 ? ? ? ? 03 46 08 8D 0C 49 "
  .. "8B 0C 8D ? ? ? ? 03 4E 10 0F B7 14 45 ? ? ? ? 0F B7 04 4D ? ? ? ? 57 33 FF 66 3B D0 "
  .. "74 ? 39 BE 84 00 00 00 75 ? 39 BE 88 00 00 00 75 ? 66 3B C7 75 ? 5F 33 C0 5E C2 08 00"
-- The row table and the area map are each read twice there, the same address both times.
local SEARCH_SAME_OPERANDS = { { 0x0F, 0x1C }, { 0x27, 0x2F } }

local ORDER_LOW, ORDER_HIGH = 1, 999

local site            -- { call, search } once resolved
local problem         -- why route policies cannot run, once known
local open = false    -- policies may be added and enabled (route-search enabled, game not started)
local closed = false  -- the game has started
local unitSlot, firstSlot, head
local policies = {}   -- by id
local byOrder = {}    -- order -> id

local function fail(message, ...)
  error(NAME .. ": " .. string.format(message, ...), 0)
end

local function u32(value)
  return value & 0xFFFFFFFF
end

local function found(address)
  return address ~= nil and address ~= 0
end

local function callTarget(call)
  return u32(call + 5 + core.readInteger(call + 1))
end

-- The one match of a pattern, or nil and why not.
local function unique(pattern, purpose)
  local ok, first = pcall(core.AOBScan, pattern)
  if not ok or not found(first) then
    return nil, string.format("%s was not found; this executable is not supported", purpose)
  end
  local earliest = core.scanForAOB(pattern)
  if found(earliest) then first = earliest end
  if found(core.scanForAOB(pattern, first + 1)) then
    return nil, string.format("%s matches more than once; refusing to guess", purpose)
  end
  return first
end

local function resolve()
  if site or problem then return end
  local call, searchAt, why
  call, why = unique(SITE, "setDestinationForUnit's route search call")
  if call then
    call = call + SITE_CALL
    searchAt, why = unique(SEARCH, "the game's route search (PathFindingState::doPathfinding)")
  end
  if searchAt then
    for _, pair in ipairs(SEARCH_SAME_OPERANDS) do
      if u32(core.readInteger(searchAt + pair[1])) ~= u32(core.readInteger(searchAt + pair[2])) then
        why = "the game's route search does not read its tables the way this module knows"
      end
    end
  end
  if not why then
    local target = callTarget(call)
    if target ~= searchAt then
      why = string.format("setDestinationForUnit's route search call at 0x%X already goes to "
        .. "0x%X instead of the game's search at 0x%X. Another module has changed it; update "
        .. "that module to a route-search policy or turn its route feature off", call, target,
        searchAt)
    end
  end
  if why then
    problem = why
    log(WARNING, NAME .. ": route policies are unavailable: " .. why)
    return
  end
  site = { call = call, search = searchAt }
end

local function dword(value)
  value = u32(value)
  return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF
end

local function append(code, ...)
  for _, byte in ipairs({ ... }) do
    code[#code + 1] = byte
  end
end

-- What the redirected call runs: the same arguments, ecx untouched, handed to the outermost
-- policy; the unit is kept in [unit] for the policies, the previous value put back after.
local function headCode()
  local code = {}
  append(code, 0xFF, 0x35, dword(unitSlot))   -- push dword [unit]
  append(code, 0x89, 0x35, dword(unitSlot))   -- mov [unit], esi
  append(code, 0xFF, 0x74, 0x24, 0x0C)        -- push dword [esp + 0x0C]   canClimb
  append(code, 0xFF, 0x74, 0x24, 0x0C)        -- push dword [esp + 0x0C]   owner
  append(code, 0xFF, 0x15, dword(firstSlot))  -- call dword [first]
  append(code, 0x8F, 0x05, dword(unitSlot))   -- pop dword [unit]
  append(code, 0xC2, 0x08, 0x00)              -- ret 8
  return code
end

local function relativeCall(from, to)
  return { 0xE8, dword(to - (from + 5)) }
end

local function chain()
  local enabled = {}
  for _, policy in pairs(policies) do
    if policy.entry then enabled[#enabled + 1] = policy end
  end
  table.sort(enabled, function(a, b) return a.order < b.order end)
  return enabled
end

local function describe(enabled)
  local names = {}
  for _, policy in ipairs(enabled) do
    names[#names + 1] = string.format("%s (%d)", policy.id, policy.order)
  end
  names[#names + 1] = "the game's search"
  return table.concat(names, " -> ")
end

local function relink()
  local enabled = chain()
  for _, policy in pairs(policies) do
    core.writeInteger(policy.next, site.search)
  end
  for index, policy in ipairs(enabled) do
    local inner = enabled[index + 1]
    core.writeInteger(policy.next, inner and inner.entry or site.search)
  end
  core.writeInteger(firstSlot, enabled[1] and enabled[1].entry or site.search)
  log(INFO, NAME .. ": unit route search: " .. describe(enabled))
end

local function redirect()
  if head then
    if callTarget(site.call) ~= head then
      fail("setDestinationForUnit's route search call at 0x%X was changed by another module "
        .. "after route-search redirected it", site.call)
    end
    return
  end
  if core.readByte(site.call) & 0xFF ~= 0xE8 or callTarget(site.call) ~= site.search then
    fail("setDestinationForUnit's route search call at 0x%X was changed by another module "
      .. "before the first route policy was enabled; update that module to a route-search "
      .. "policy or turn its route feature off", site.call)
  end
  head = core.allocateCode(headCode())
  core.writeCodeBytes(site.call, relativeCall(site.call, head))
end

local function checkOpen(what)
  if closed then
    fail("%s is only possible while modules are enabled, before the game starts", what)
  end
  if not open then
    fail("%s was called before route-search was enabled; declare route-search as a dependency "
      .. "and call it from your module's enable()", what)
  end
end

local function addPolicy(self, spec)
  checkOpen("addPolicy")
  if type(spec) ~= "table" then
    fail("addPolicy expects { id = <string>, order = <integer> }")
  end
  local id, order = spec.id, spec.order
  if type(id) ~= "string" or id == "" then
    fail("addPolicy needs a policy id (a non-empty string)")
  end
  if policies[id] then
    fail("the route policy '%s' is already registered", id)
  end
  if math.type(order) ~= "integer" or order < ORDER_LOW or order > ORDER_HIGH then
    fail("the route policy '%s' needs an integer order from %d to %d", id, ORDER_LOW, ORDER_HIGH)
  end
  if byOrder[order] then
    fail("the route policies '%s' and '%s' both ask for order %d; equal orders are refused "
      .. "because their nesting would depend on load order", byOrder[order], id, order)
  end
  resolve()
  if problem then
    fail("%s", problem)
  end
  if not unitSlot then
    unitSlot = core.allocate(8, true)
    firstSlot = unitSlot + 4
  end
  local next = core.allocate(4, true)
  core.writeInteger(next, site.search)
  policies[id] = { id = id, order = order, next = next }
  byOrder[order] = id
  return { next = next, unit = unitSlot }
end

local function enablePolicy(self, id, entry)
  checkOpen("enablePolicy")
  local policy = policies[id]
  if not policy then
    fail("enablePolicy: the route policy '%s' was not registered with addPolicy", tostring(id))
  end
  if math.type(entry) ~= "integer" or entry == 0 then
    fail("enablePolicy: the route policy '%s' needs the address of its code", id)
  end
  if policy.entry then
    fail("the route policy '%s' is already enabled", id)
  end
  redirect()
  policy.entry = u32(entry)
  relink()
end

local function policyList(self)
  local list = {}
  for _, policy in ipairs(chain()) do
    list[#list + 1] = { id = policy.id, order = policy.order, entry = policy.entry,
      next = policy.next }
  end
  return list
end

-- The game is about to run: no more policies, and say so if someone redirected the call
-- again behind this module's back.
local function afterInit()
  open, closed = false, true
  if head and callTarget(site.call) ~= head then
    log(ERROR, string.format("%s: setDestinationForUnit's route search call at 0x%X no longer "
      .. "goes to route-search (it goes to 0x%X): a module loaded later changed it. The route "
      .. "policies %s may see the wrong unit or not run.", NAME, site.call,
      callTarget(site.call), describe(chain())))
  end
end

return {
  version = CONTRACT,
  addPolicy = addPolicy,
  enablePolicy = enablePolicy,
  policies = policyList,

  enable = function(self, config)
    if open or closed then return end
    open = true
    if hooks and hooks.registerHookCallback then
      hooks.registerHookCallback("afterInit", afterInit)
    end
  end,

  disable = function(self, config)
    return false, NAME .. ": restart the game to change route policies"
  end,
}
