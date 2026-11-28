return {
  enable = function(self, config)
    if self.applied or not (config and config.reachable_delivery == true) then return end
    local delivery = require("delivery")
    local ok, native = pcall(delivery.resolve)
    if not ok then
      log(ERROR, "Granary and armory delivery is off: " .. tostring(native))
      return
    end
    delivery.install(native)
    self.applied = true
  end,
  disable = function()
    return false, "worker-delivery-fix: restart the game to change native options"
  end,
}
