return {
  enable = function(self, config)
    if self.applied then return end
    local crewEnabled = not config or config.crew_lifecycle ~= false
    local stopEnabled = not config or config.siege_target_stop ~= false
    if not crewEnabled and not stopEnabled then return end
    local native = crewEnabled and require("unit-handlers").resolve()
    local crew = crewEnabled and require("crew").prepare(native)
    local unman = crewEnabled and require("unman").prepare()
    local targeting = stopEnabled and require("siege-targeting").prepare()
    -- Resolve and validate every enabled site before installing a patch.
    if targeting then targeting() end
    if crew then crew() end
    if unman then unman() end
    self.applied = true
  end,
  disable = function()
    return false, "fixed-engineers: restart the game to change native options"
  end,
}
