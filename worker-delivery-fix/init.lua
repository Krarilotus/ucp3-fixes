return {
  enable = function(self, config)
    if self.applied or (config and config.reachable_delivery == false) then return end
    local delivery = require("delivery")
    local native = delivery.resolve() -- Validate every binding before patching.
    delivery.install(native)
    self.applied = true
  end,
  disable = function()
    return false, "worker-delivery-fix: restart the game to change native options"
  end,
}
