return {
  enable = function(self, config)
    if self.applied or not (config and config.map_settings == true) then return end
    local install = require("availability").prepare()
    install()
    self.applied = true
  end,
  disable = function()
    return false, "scenario-settings-fix: restart the game to change native options"
  end,
}
