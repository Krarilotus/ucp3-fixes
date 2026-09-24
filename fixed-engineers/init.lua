return {
  enable = function(self, config)
    if self.applied or (config and config.crew_lifecycle == false) then return end
    local native = require("unit-handlers").resolve()
    local crew = require("crew").prepare(native)
    local unman = require("unman").prepare()
    -- Validate both native sites before installing either correction.
    crew()
    unman()
    self.applied = true
  end,
  disable = function()
    return false, "fixed-engineers: restart the game to change native options"
  end,
}
