local fields = require("behavior.policy").fields

return function(policy)
  local keys = {}
  for key in pairs(fields) do keys[#keys + 1] = key end
  table.sort(keys)
  for _, key in ipairs(keys) do
    modules.aicloader:setAdditionalAICValue(key,
      function(ai, value)
        if value == nil then return policy:raw(ai, key) end
        local ok, reason = policy:set(ai, key, value)
        if not ok then log(WARNING, reason) end
      end,
      function(ai) policy:reset(ai, key) end)
  end
end
