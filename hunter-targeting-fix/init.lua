return {
  enable = function(self, config)
    if self.applied or (config and config.hunter_targeting == false) then return end
    local install = require("hunting").prepare()
    install()
    self.applied = true
  end,
  disable = function()
    return false, "hunter-targeting-fix: restart the game to change native options"
  end,
}
