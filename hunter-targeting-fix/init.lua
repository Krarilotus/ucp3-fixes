return {
  enable = function(self, config)
    if self.applied or not (config and config.hunter_targeting == true) then return end
    local ok, install = pcall(require("hunting").prepare)
    if not ok then
      log(ERROR, "The hunter targeting fix is off: " .. tostring(install))
      return
    end
    install()
    self.applied = true
  end,
  disable = function()
    return false, "hunter-targeting-fix: restart the game to change native options"
  end,
}
