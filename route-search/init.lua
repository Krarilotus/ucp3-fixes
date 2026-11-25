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

local function found(address)
  return address ~= nil and address ~= 0
end

local function find(pattern, purpose)
  local ok, at = pcall(core.AOBScan, pattern)
  if not ok or not found(at) then
    return nil, string.format("%s was not found; this executable is not supported", purpose)
  end
  if core.scanForAOB(pattern) ~= at or found(core.scanForAOB(pattern, at + 1)) then
    return nil, string.format("%s does not have exactly one match; this executable is not supported", purpose)
  end
  return at
end

local function resolve()
  if site or problem then return end
  local call, searchAt, why
  call, why = find(SITE, "setDestinationForUnit's route search call")
  if call then
    call = call + SITE_CALL
    searchAt, why = find(SEARCH, "the game's route search (PathFindingState::doPathfinding)")
  end
  if searchAt then
    for _, pair in ipairs(SEARCH_SAME_OPERANDS) do
      if core.readInteger(searchAt + pair[1]) ~= core.readInteger(searchAt + pair[2]) then
        why = "the game's route search does not read its tables the way this module knows"
      end
    end
  end
  if not why then
    local target = (call + 5 + core.readInteger(call + 1)) & 0xFFFFFFFF
    if target ~= searchAt then
      why = string.format("setDestinationForUnit's route search call at 0x%X already goes to "
        .. "0x%X instead of the game's search at 0x%X. Another module has changed it; update "
        .. "that module to a route-search policy or turn its route feature off", call, target,
        searchAt)
    end
  end
  if why then
    problem = why
    log(WARNING, "route policies are unavailable: " .. why)
    return
  end
  site = { call = call, search = searchAt }
end

-- What the redirected call runs: the same arguments, ecx untouched, handed to the outermost
-- policy; the unit is kept in [unit] for the policies, the previous value put back after.
local STUB_SIZE = 35
local function headCode()
  return {
    0xFF, 0x35, core.itob(unitSlot),    -- push dword [unit]
    0x89, 0x35, core.itob(unitSlot),    -- mov [unit], esi
    0xFF, 0x74, 0x24, 0x0C,             -- push dword [esp + 0x0C]   canClimb
    0xFF, 0x74, 0x24, 0x0C,             -- push dword [esp + 0x0C]   owner
    0xFF, 0x15, core.itob(firstSlot),   -- call dword [first]
    0x8F, 0x05, core.itob(unitSlot),    -- pop dword [unit]
    0xC2, 0x08, 0x00,                   -- ret 8
  }
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
  log(INFO, "unit route search: " .. describe(enabled))
end

-- The call must still be what route-search found (or redirected) before anything is written.
local function isCallTo(target)
  return core.readByte(site.call) == 0xE8
    and (site.call + 5 + core.readInteger(site.call + 1)) & 0xFFFFFFFF == target
end

local function checkCall()
  if head then
    if not isCallTo(head) then
      fail("setDestinationForUnit's route search call at 0x%X was changed by another module "
        .. "after route-search redirected it", site.call)
    end
  elseif not isCallTo(site.search) then
    fail("setDestinationForUnit's route search call at 0x%X was changed by another module "
      .. "before the first route policy was enabled; update that module to a route-search "
      .. "policy or turn its route feature off", site.call)
  end
end

-- Redirect the call once, after the chain it leads to is written.
local function redirect()
  if head then return end
  head = core.allocateCode(STUB_SIZE)
  core.writeCode(head, headCode())
  core.writeCode(site.call, { 0xE8, core.itob(head - (site.call + 5)) })
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
  checkCall()
  policy.entry = entry
  relink()
  redirect()
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
  if head and not isCallTo(head) then
    log(ERROR, string.format("setDestinationForUnit's route search call at 0x%X no longer "
      .. "goes to route-search (it goes to 0x%X): a module loaded later changed it. The game "
      .. "runs, but the route policies %s may see the wrong unit or not run.", site.call,
      (site.call + 5 + core.readInteger(site.call + 1)) & 0xFFFFFFFF, describe(chain())))
  end
end

local api = {
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

-- Other modules call this one through the framework's module proxy. In UCP 3.0.7 that proxy
-- fails on any method that returns a table unless the module lists its proxy options; the
-- two methods listed here return plain tables built for the caller.
return api, {
  proxy = {
    ignored = { "addPolicy", "policies" },
  },
}
