return {
  enable = function(self, config)
    if self.applied or not (config and config.living_gatehouse_occupants == true) then return end
    local ok, install = pcall(require("capture").prepare)
    if not ok then
      log(ERROR, "The occupied gatehouse capture fix is off.")
      log(WARNING, tostring(install) .. "; gatehouse-capture-fix is left off")
      return
    end
    install()
    self.applied = true
  end,
  disable = function()
    return false, "gatehouse-capture-fix: restart the game to change native options"
  end,
}
