return {
  enable = function(self, config)
    if self.applied then return end
    local crewEnabled = config ~= nil and config.crew_lifecycle == true
    local stopEnabled = config ~= nil and config.siege_target_stop == true
    if not crewEnabled and not stopEnabled then return end
    local crew, unman, targeting
    if crewEnabled then
      local ok, installCrew, installUnman = pcall(function()
        local native = require("unit-handlers").resolve()
        return require("crew").prepare(native), require("unman").prepare()
      end)
      if ok then
        crew, unman = installCrew, installUnman
      else
        log(ERROR, "Siege crew cleanup is off: " .. tostring(installCrew))
      end
    end
    if stopEnabled then
      local ok, install = pcall(require("siege-targeting").prepare)
      if ok then
        targeting = install
      else
        log(ERROR, "Stop siege engines when targeting is off: " .. tostring(install))
      end
    end
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
