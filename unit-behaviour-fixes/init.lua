return {
  enable = function(self, config)
    if self.applied or (config.crew_lifecycle == false and config.tunneler_response == false
        and config.siege_target_stop == false) then return end
    local native = (config.crew_lifecycle ~= false or config.tunneler_response ~= false)
      and require("unit-handlers").resolve()
    local crew = config.crew_lifecycle ~= false and require("crew").prepare(native)
    local tunneler = config.tunneler_response ~= false and require("tunneler").prepare(native)
    local targeting = config.siege_target_stop ~= false and require("siege-targeting").prepare()
    if targeting then targeting() end
    if crew then crew() end
    if tunneler then tunneler() end
    self.applied = true
  end,
  disable = function()
    return false, "unit-behaviour-fixes: restart the game to change native options"
  end,
}
