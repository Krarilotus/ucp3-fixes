local fields = require("behavior.policy").fields
local owner = "aiv-troops-behaviour"

-- The policy stores the per-AI values; AIC Loader applies them through this provider.
return function(policy)
  local loader = modules.aicloader
  local keys = {}
  for key in pairs(fields) do keys[#keys + 1] = key end
  table.sort(keys)
  local function restore(ai, values)
    for _, key in ipairs(keys) do
      if values[key] == nil then policy:reset(ai, key) else policy:set(ai, key, values[key]) end
    end
  end
  local active, registered = true, {}
  local function unregister()
    active = false
    for index = #registered, 1, -1 do
      loader:unregisterAdditionalAICValue(owner, registered[index])
    end
  end
  local ok, reason = pcall(function()
    for _, key in ipairs(keys) do
      loader:registerAdditionalAICValue(owner, key, function(ai, value)
        assert(value == nil, "AIV Troop Behaviour setters require an atomic loader update")
        return policy:raw(ai, key)
      end, function(ai) policy:reset(ai, key) end)
      registered[#registered + 1] = key
    end
    loader:registerAICUpdateProvider(owner, {
      -- Takes part in every reset, so its fields reset in the same transaction.
      handles = function(_, spec, resetting)
        if not active then return false end
        if resetting then return true end
        for key in pairs(spec) do
          if fields[key] then return true end
        end
        return false
      end,
      -- Rejected fields keep their previous values; valid fields still apply.
      prepare = function(ai, spec, _, resetting)
        local previous, accepted = {}, {}
        for _, key in ipairs(keys) do
          previous[key] = policy:raw(ai, key)
          if not resetting and spec[key] ~= nil then
            local ok, reason = policy:accepts(ai, key, spec[key])
            if ok then
              accepted[key] = spec[key]
            else
              log(type(spec[key]) == "string" and WARNING or ERROR, reason)
            end
          end
        end
        return {
          commit = function()
            if resetting then return restore(ai, {}) end
            for key, value in pairs(accepted) do policy:set(ai, key, value) end
          end,
          rollback = function() restore(ai, previous) end,
        }
      end,
    })
  end)
  if not ok then
    unregister()
    error(reason, 0)
  end
  return unregister
end
