-- Shared original unit-handler ownership for this module's bounded corrections.
local pattern = "0F BF 91 A2 06 00 00 8B 04 95 ? ? ? ? FF D0 A1 ? ? ? ? 69 C0 90 04 00 00"
local function resolve()
  local dispatch = core.AOBScan(pattern)
  local tableAddress = core.readInteger(dispatch + 10)
  local entries = {}
  for kind = 0, 79 do entries[kind] = core.readInteger(tableAddress + kind * 4) end
  return {
    entries = entries,
    find = function(kind, signature, size)
      local first, last = entries[kind], nil
      for _, entry in pairs(entries) do
        if entry > first and (not last or entry < last) then last = entry end
      end
      local address = core.AOBScan(signature)
      assert(last and address >= first and address + size < last,
        "fixed-engineers: patch is outside its native unit handler")
      return address
    end,
  }
end
return {resolve = resolve}
