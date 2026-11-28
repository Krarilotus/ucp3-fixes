return {
  enable = function(self, config)
    if self.applied or not (config and config.map_settings == true) then return end
    local ok, install = pcall(require("availability").prepare)
    if not ok then
      log(ERROR, "Map availability settings are off: " .. tostring(install))
      return
    end
    install()
    self.applied = true
  end,
  disable = function()
    return false, "scenario-settings-fix: restart the game to change native options"
  end,
}
