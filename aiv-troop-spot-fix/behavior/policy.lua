-- AIC IDs are personalities 1 (Rat) through 16 (Abbot), not player slots.
local TROOPS = {
  {name = "Engineer", row = 1, unit = 30, digs = true},
  {name = "Archer", row = 6, unit = 22, digs = true},
  {name = "Crossbowman", row = 7, unit = 23},
  {name = "Spearman", row = 8, unit = 24, digs = true},
  {name = "Pikeman", row = 9, unit = 25, digs = true},
  {name = "Maceman", row = 10, unit = 26, digs = true},
  {name = "Swordsman", row = 11, unit = 27},
  {name = "Knight", row = 12, unit = 28},
  {name = "Slave", row = 13, unit = 71, digs = true},
  {name = "Slinger", row = 14, unit = 72},
  {name = "Assassin", row = 15, unit = 73},
  {name = "ArabianArcher", row = 16, unit = 70},
  {name = "HorseArcher", row = 17, unit = 74},
  {name = "ArabianSwordsman", row = 18, unit = 75},
  {name = "FireThrower", row = 19, unit = 76},
}

local BY_UNIT, BY_ROW = {}, {}
local FIELDS = {
  AIVTroops_InitialRole = {default = -1, min = -1, max = 1},
  AIVTroops_Movement = {default = -1, min = -1, max = 2},
}
for _, troop in ipairs(TROOPS) do
  BY_UNIT[troop.unit], BY_ROW[troop.row] = troop, troop
  for _, kind in ipairs({"InitialRole", "Movement"}) do
    local maximum = (kind == "InitialRole" and not troop.digs) and 1 or 2
    FIELDS["AIVTroops_" .. kind .. "_" .. troop.name] = {default = -1, min = -1, max = maximum}
  end
end

local CHOICES = {
  InitialRole = {inherit = -1, native = 0, defend = 1, dig = 2},
  Movement = {inherit = -1, native = 0, hold = 1, patrol = 2},
}

local function new(config)
  config = config or {}
  local defaults = {}
  for key, field in pairs(FIELDS) do
    local suffix = key:sub(#"AIVTroops_" + 1)
    local kind = suffix:match("^[^_]+")
    local choice = (config.defaults or {})[suffix]
    local value = choice and CHOICES[kind][choice] or nil
    if choice ~= nil and (value == nil or value < field.min or value > field.max) then
      error("aiv-troop-spot-fix: invalid customization " .. suffix .. "=" .. tostring(choice))
    end
    defaults[key] = value or (suffix == kind and 0 or -1)
  end
  local values = {}
  for ai = 1, 16 do
    values[ai] = {}
  end
  local policy = {}
  function policy:set(ai, key, value)
    local field = FIELDS[key]
    if not values[ai] or not field or type(value) ~= "number" or value ~= math.floor(value)
        or value < field.min or value > field.max then
      return false, "invalid AIV troop setting: " .. tostring(ai) .. "/" .. tostring(key) .. "=" .. tostring(value)
    end
    values[ai][key] = value
    return true
  end
  function policy:reset(ai, key)
    if not values[ai] or not FIELDS[key] then return false end
    values[ai][key] = nil
    return true
  end
  function policy:raw(ai, key)
    if not values[ai] or not FIELDS[key] then return nil end
    return values[ai][key] or FIELDS[key].default
  end
  function policy:get(ai, kind, row)
    local troop = BY_ROW[row]
    if not values[ai] or not troop then return 0 end
    local prefix = "AIVTroops_" .. kind
    local key = prefix .. "_" .. troop.name
    -- AIC troop > AIC common > menu troop > menu common > native.
    if config.aic_overrides ~= false then
      for _, setting in ipairs({key, prefix}) do
        local value = values[ai][setting]
        if value ~= nil and value ~= -1 then return value end
      end
    end
    if defaults[key] ~= -1 then return defaults[key] end
    return math.max(0, defaults[prefix])
  end
  function policy:initialRole(ai, unit, canDig)
    local troop = BY_UNIT[unit]
    if not troop then return 0 end
    local role = self:get(ai, "InitialRole", troop.row)
    if role == 2 and (not troop.digs or not canDig) then return 1 end
    return role
  end
  function policy:ownRow(ai, unit)
    local troop = BY_UNIT[unit]
    if troop and (self:get(ai, "InitialRole", troop.row) ~= 0
        or self:get(ai, "Movement", troop.row) ~= 0
        or self:get(ai, "InitialRole", 13) ~= 0 or self:get(ai, "Movement", 13) ~= 0) then
      return troop.row
    end
  end
  return policy
end

local function groupCount(mode, slots, patrolGroups)
  slots = math.max(0, math.min(10, slots))
  if mode == 1 then return slots end
  -- Zero patrol groups means no cycling; retain one stationary defense group.
  return math.min(slots, math.max(1, patrolGroups))
end

local function slotIndex(mode, ordinal, slots, patrolGroups, rallyHits)
  if slots < 1 then return nil end
  if mode == 1 or patrolGroups < 1 then return ordinal % slots end
  local groups = groupCount(mode, slots, patrolGroups)
  return (rallyHits + ordinal * math.max(1, math.floor(slots / groups))) % slots
end

return {new = new, troops = TROOPS, fields = FIELDS, groupCount = groupCount, slotIndex = slotIndex}
