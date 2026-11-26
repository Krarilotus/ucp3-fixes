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
  for _, key in ipairs(keys) do
    loader:registerAdditionalAICValue(owner, key, function(ai, value)
      assert(value == nil, "AIV Troop Behaviour setters require an atomic loader update")
      return policy:raw(ai, key)
    end, function(ai) policy:reset(ai, key) end)
  end
  loader:registerAICUpdateProvider(owner, {
    -- Takes part in every reset, so its fields reset in the same transaction.
    handles = function(_, spec, resetting)
      if resetting then return true end
      for key in pairs(spec) do
        if fields[key] then return true end
      end
      return false
    end,
    prepare = function(ai, spec, _, resetting)
      local previous = {}
      for _, key in ipairs(keys) do previous[key] = policy:raw(ai, key) end
      return {
        commit = function()
          if resetting then return restore(ai, {}) end
          for _, key in ipairs(keys) do
            if spec[key] ~= nil then
              local ok, reason = policy:set(ai, key, spec[key])
              if not ok then log(WARNING, reason) end
            end
          end
        end,
        rollback = function() restore(ai, previous) end,
      }
    end,
  })
end
