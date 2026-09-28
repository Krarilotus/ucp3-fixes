return {
  enable = function(self, config)
    if self.applied or (config and config.living_gatehouse_occupants == false) then return end
    local install = require("capture").prepare()
    install()
    self.applied = true
  end,
  disable = function()
    return false, "gatehouse-capture-fix: restart the game to change native options"
  end,
}
