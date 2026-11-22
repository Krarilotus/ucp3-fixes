return {
  enable = function(self, config)
    -- Off unless configured on: the module keeps the game's behaviour by default.
    if self.applied or not (config and config.living_gatehouse_occupants == true) then return end
    local install = require("capture").prepare()
    install()
    self.applied = true
  end,
  disable = function()
    return false, "gatehouse-capture-fix: restart the game to change native options"
  end,
}
