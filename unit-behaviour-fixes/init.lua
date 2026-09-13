return {
  enable = function(self, config)
    if self.applied or (config.crew_lifecycle == false and config.tunneler_response == false) then return end
    local native = require("unit-handlers").resolve()
    local crew = config.crew_lifecycle ~= false and require("crew").prepare(native)
    local unman = config.crew_lifecycle ~= false and require("unman").prepare()
    local tunneler = config.tunneler_response ~= false and require("tunneler").prepare(native)
    if crew then crew() end
    if unman then unman() end
    if tunneler then tunneler() end
    self.applied = true
  end,
  disable = function()
    return false, "unit-behaviour-fixes: restart the game to change native options"
  end,
}
