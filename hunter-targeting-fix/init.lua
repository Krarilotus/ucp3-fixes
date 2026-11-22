return {
  enable = function(self, config)
    -- Off unless configured on: the module keeps the game's behaviour by default.
    if self.applied or not (config and config.hunter_targeting == true) then return end
    local install = require("hunting").prepare()
    install()
    self.applied = true
  end,
  disable = function()
    return false, "hunter-targeting-fix: restart the game to change native options"
  end,
}
