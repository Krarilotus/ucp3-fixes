return {
  enable = function(self, config)
    if config.crew_lifecycle == false or self.applied then return end
    local install = require("crew").prepare()
    install()
    self.applied = true
  end,
  disable = function()
    return false, "unit-behaviour-fixes: restart the game to change native options"
  end,
}
