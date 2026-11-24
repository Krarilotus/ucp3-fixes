-- Full Minimap
--
-- Scales the entire map to fit the interactive minimap (126x126 in-game, 128x128 in
-- landscaping) on every map size instead of showing a zoomed-in scrolling window.
--
-- Reuses MinimapViewState's pre-rendered full-map terrain+building cache (field17_0x44),
-- drawMinimap's live unit scanner (stealth, wildlife, disguised units, blinking lord,
-- Alt+R mode, all 4 map orientations), PencilRenderCore::drawBorderBox,
-- ViewportRenderState::setViewportBasedOnMapSize, and convertMinimapClickToTileXY's
-- orientation/tile-matrix lookup. Editor preview (param_10 == -1) and map/save
-- thumbnail rendering (param_10 == 1) remain untouched.

local SCROLL_AOB = "A1 ? ? ? ? 2B 41 28 56 99 F7 79 20 8B 35 ? ? ? ? 2B 71 2C 57 8B F8 0F AF 79 30 A1 ? ? ? ? 83 C0 FB 99 2B C2 D1 F8 2B F8 03 79 14 8B C6 99 C1 E7 05 89 3D ? ? ? ? F7 79 24 5F 8B F0 0F AF 71 30 A1 ? ? ? ? 99 2B C2 D1 F8 2B F0 03 71 10 B9 ? ? ? ? 03 F6 03 F6 03 F6 89 35 ? ? ? ? 5E E9 ? ? ? ?"
local CLICK_TILE_AOB = "83 79 3C 00 0F 84 B6 00 00 00 A1 ? ? ? ? 2B 41 28 53 0F AF 41 30 99 F7 79 20 8B 51 14 8B 5C 24 08 56 8B 35 ? ? ? ? 2B 71 2C 57 33 FF 8D 44 10 06 C1 E0 05 89 03 8B 41 30 0F AF C6 99 F7 79 24 8B 74 24 14 03 41 10 03 C0 03 C0 03 C0 89 06"
local MAPSIZE_AOB = "A1 ? ? ? ? 3B C1 89 7D BC 8D 7E 44 89 75 A8 89 4D F0 C7 45 F8 08 00 00 00 89 55 EC 89 7D AC 89 4D B8 89 4D E0 89 45 E4 75 07 C7"
local DRAW_SETUP_AOB = "89 4E 10 89 7E 14 03 45 08 89 45 F4 8B 45 20 2B C1 0F AF 45 28 99 F7 FB 03 45 0C 89 45 20 8B C1 99 2B C2 8B C8 A1 ? ? ? ? 89 45 B0 83 C0 01"
local DRAW_BLIT_AOB = "8B 3D ? ? ? ? 8B 45 08 03 C0 03 F8 8B 45 0C 8B 15 ? ? ? ? F7 E2 03 F8 8B 75 AC 8B 45 1C 2B 45 B8 03 C0 03 F0 8B 45 C8 2B 45 E0 BA 90 01 00 00 F7 E2 03 F0 8B 55 BC 8B 4D EC BB 00 00 00 00 66 8B 04 1E 66 89 04 1F 83 C3 02 49 75 F2 81 C6 90 01 00 00 03 3D ? ? ? ? 4A 75 DB"
local DRAW_UNIT_NORMAL_AOB = "9F E9 7E 00 00 00 83 E0 01 3B 45 24 7D 76 8B 5D 24 8B 55 E0 2B D8 83 EB 01 D1 EB 8D 34 02 83 C3 01 85 F6 7C 57 8B 45 10 0F AF 45 24 3B F0 7D 4C 8B C6 99 F7 7D FC"
local DRAW_UNIT_ALTR_AOB = "96 E9 7E 00 00 00 83 E0 01 3B 45 24 7D 7C 8B 5D 24 8B 55 E0 2B D8 83 EB 01 D1 EB 8D 34 02 83 C3 01 85 F6 7C 57 8B 45 10 0F AF 45 24 3B F0 7D 4C 8B C6 99 F7 7D FC"

local DRAW_SETUP_ASM = [[
mov dword [STATE], 0
cmp dword [ebp + 0x2C], 0
jne ds_vanilla
test byte [ebp + 0x18], 2
jz ds_vanilla
cmp dword [ebp - 0x14], 0
jle ds_vanilla
cmp dword [ebp - 0x44], 0
jle ds_vanilla

mov eax, [MAP_SIZE]
test eax, eax
jnz ds_have_ms
mov eax, 400
ds_have_ms:
cmp eax, 4
jl ds_vanilla
cmp eax, 400
jg ds_vanilla

push ebx
push esi

mov ebx, eax
mov edx, eax
shr edx, 1
mov [ebp + 0x10], edx
mov [ebp + 0x14], ebx

cmp eax, 200
jle ds_small_buf
mov ecx, edx
jmp ds_store_buf
ds_small_buf:
mov ecx, ebx
ds_store_buf:
mov [STATE + 4], ecx
mov esi, 200
sub esi, ecx
sar esi, 1
mov [STATE + 8], esi
lea esi, [ecx + ecx]
mov [STATE + 12], esi
mov dword [STATE], 1

mov ecx, 400
sub ecx, eax
sar ecx, 1
mov edi, ecx
sar edi, 1

mov esi, [esp]
mov [esi + 0x10], ecx
mov [esi + 0x14], edi
mov [ebp + 0x1C], edi

push ecx
push edi
push ebx
push edx

mov eax, [VP_X]
cdq
and edx, 0x1F
add eax, edx
sar eax, 5
sub eax, [esp + 8]
mov esi, eax

imul eax, [ebp - 0x14]
cdq
idiv dword [esp]
add eax, [ebp + 0x08]
mov ecx, [ebp + 0x08]
cmp eax, ecx
jge ds_x1_lo
mov eax, ecx
ds_x1_lo:
add ecx, [ebp - 0x14]
dec ecx
cmp eax, ecx
jle ds_x1_hi
mov eax, ecx
ds_x1_hi:
mov ebx, eax

mov eax, esi
add eax, [ebp - 0x34]
inc eax
imul eax, [ebp - 0x14]
cdq
idiv dword [esp]
add eax, [ebp + 0x08]
dec eax
cmp eax, ebx
jge ds_x2_lo
mov eax, ebx
ds_x2_lo:
cmp eax, ecx
jle ds_x2_hi
mov eax, ecx
ds_x2_hi:
sub eax, ebx
mov [ebp - 0x0C], ebx
mov [ebp - 0x18], eax

mov eax, [VP_Y]
cdq
and edx, 7
add eax, edx
sar eax, 3
sub eax, [esp + 12]
mov esi, eax

imul eax, [ebp - 0x44]
cdq
idiv dword [esp + 4]
add eax, [ebp + 0x0C]
mov ecx, [ebp + 0x0C]
cmp eax, ecx
jge ds_y1_lo
mov eax, ecx
ds_y1_lo:
add ecx, [ebp - 0x44]
dec ecx
cmp eax, ecx
jle ds_y1_hi
mov eax, ecx
ds_y1_hi:
mov ebx, eax

mov eax, esi
add eax, [VP_H]
imul eax, [ebp - 0x44]
cdq
idiv dword [esp + 4]
add eax, [ebp + 0x0C]
dec eax
cmp eax, ebx
jge ds_y2_lo
mov eax, ebx
ds_y2_lo:
cmp eax, ecx
jle ds_y2_hi
mov eax, ecx
ds_y2_hi:
sub eax, ebx
mov [ebp + 0x20], ebx
mov [ebp - 0x40], eax
mov dword [ebp - 0x3C], 1

add esp, 8
pop edi
pop ecx
pop esi
pop ebx

ds_vanilla:
mov eax, ecx
cdq
sub eax, edx
jmp RESUME
]]

local DRAW_BLIT_ASM = [[
cmp dword [STATE], 0
jne db_scaled
mov edi, [SURFACE_PTR]
jmp RESUME_VANILLA

db_scaled:
sub esp, 16

mov eax, [STATE + 8]
imul eax, eax, 402
add eax, [ebp - 0x54]
mov [esp + 8], eax

mov eax, [STATE + 4]
shl eax, 16
xor edx, edx
div dword [ebp - 0x14]
mov [esp], eax

mov eax, [STATE + 4]
shl eax, 16
xor edx, edx
div dword [ebp - 0x44]
mov [esp + 4], eax

mov eax, [ebp + 0x0C]
mul dword [SURFACE_PITCH]
mov edi, [SURFACE_PTR]
add edi, eax
mov eax, [ebp + 0x08]
lea edi, [edi + eax * 2]

mov dword [esp + 12], 0
mov ebx, [ebp - 0x44]

db_row_loop:
mov eax, [esp + 12]
shr eax, 16
imul eax, eax, 400
add eax, [esp + 8]
mov esi, eax

push ebx
push edi
mov ebx, [esp + 8]
mov ecx, [ebp - 0x14]
xor eax, eax

db_col_loop:
mov edx, eax
shr edx, 16
mov dx, [esi + edx * 2]
mov [edi], dx
add edi, 2
add eax, ebx
dec ecx
jnz db_col_loop

pop edi
pop ebx
add edi, [SURFACE_PITCH]
mov eax, [esp + 4]
add [esp + 12], eax
dec ebx
jnz db_row_loop

add esp, 16
jmp SKIP_BLIT
]]

local DRAW_UNIT_ASM = [[
cmp dword [STATE], 0
jne du_scaled
and eax, 1
cmp eax, [ebp + 0x24]
jmp RESUME_VANILLA

du_scaled:
mov ebx, [ebp + 0x24]
and eax, 1
cmp eax, ebx
jge SKIP_PLOT
sub ebx, eax
dec ebx
shr ebx, 1
inc ebx
mov esi, [ebp - 0x20]
add esi, eax

mov eax, [ebp - 0x30]
imul eax, [ebp - 0x44]
cdq
idiv dword [STATE + 12]
add eax, [ebp + 0x0C]
mul dword [SURFACE_PITCH]
add eax, [SURFACE_PTR]
mov ecx, eax

du_loop:
test esi, esi
jl du_next
cmp esi, [STATE + 12]
jge du_next
mov eax, esi
imul eax, [ebp - 0x14]
cdq
idiv dword [STATE + 12]
add eax, [ebp + 0x08]
mov di, [ebp + 0x14]
mov [ecx + eax * 2], di
du_next:
add esi, 2
dec ebx
jnz du_loop
jmp SKIP_PLOT
]]

local SCROLL_CLICK_ASM = [[
cmp dword [ecx + 0x18], 0
jle sc_ret
cmp dword [ecx + 0x1C], 0
jle sc_ret

push ebx
push esi
push edi

mov esi, ecx
mov ebx, [MAP_SIZE]
test ebx, ebx
jnz sc_have_ms
mov ebx, 400
sc_have_ms:
mov edi, 400
sub edi, ebx
sar edi, 1

mov eax, [MOUSE_X]
sub eax, [esi + 0x28]
test eax, eax
jge sc_dx_lo
xor eax, eax
sc_dx_lo:
mov ecx, [esi + 0x18]
dec ecx
cmp eax, ecx
jle sc_dx_hi
mov eax, ecx
sc_dx_hi:
mov ecx, ebx
shr ecx, 1
imul eax, ecx
cdq
idiv dword [esi + 0x18]
mov ecx, edi
sar ecx, 1
add ecx, eax

mov eax, [VP_W]
add eax, -5
cdq
sub eax, edx
sar eax, 1
sub ecx, eax
shl ecx, 5
mov [VP_X], ecx

mov eax, [MOUSE_Y]
sub eax, [esi + 0x2C]
test eax, eax
jge sc_dy_lo
xor eax, eax
sc_dy_lo:
mov ecx, [esi + 0x1C]
dec ecx
cmp eax, ecx
jle sc_dy_hi
mov eax, ecx
sc_dy_hi:
imul eax, ebx
cdq
idiv dword [esi + 0x1C]
add edi, eax

mov eax, [VP_H]
cdq
sub eax, edx
sar eax, 1
sub edi, eax
shl edi, 3
mov [VP_Y], edi

pop edi
pop esi
pop ebx
mov ecx, VP_STATE
jmp SET_VP_FUNC

sc_ret:
ret
]]

local CLICK_TILE_ASM = [[
cmp dword [ecx + 0x18], 0
jle ct_invalid
cmp dword [ecx + 0x1C], 0
jle ct_invalid

push ebx
push esi
push edi

mov esi, ecx
mov ebx, [MAP_SIZE]
test ebx, ebx
jnz ct_have_ms
mov ebx, 400
ct_have_ms:
mov edi, 400
sub edi, ebx
sar edi, 1

mov eax, [MOUSE_X]
sub eax, [esi + 0x28]
test eax, eax
jge ct_dx_lo
xor eax, eax
ct_dx_lo:
mov ecx, [esi + 0x18]
dec ecx
cmp eax, ecx
jle ct_dx_hi
mov eax, ecx
ct_dx_hi:
mov ecx, ebx
shr ecx, 1
imul eax, ecx
cdq
idiv dword [esi + 0x18]
mov ecx, edi
sar ecx, 1
lea eax, [eax + ecx + 6]
shl eax, 5
mov ecx, [esp + 16]
mov [ecx], eax

mov eax, [MOUSE_Y]
sub eax, [esi + 0x2C]
test eax, eax
jge ct_dy_lo
xor eax, eax
ct_dy_lo:
mov ecx, [esi + 0x1C]
dec ecx
cmp eax, ecx
jle ct_dy_hi
mov eax, ecx
ct_dy_hi:
imul eax, ebx
cdq
idiv dword [esi + 0x1C]
add eax, edi
shl eax, 3

mov ebx, [esp + 16]
mov esi, [esp + 20]
mov [esi], eax
xor edi, edi
jmp RESUME_LOOKUP

ct_invalid:
jmp INVALID_RET
]]

local function readU32(address)
  return core.readInteger(address) & 0xFFFFFFFF
end

local function readRelTarget(nextInsn, relAddr)
  local rel = core.readInteger(relAddr)
  if rel >= 0x80000000 then
    rel = rel - 0x100000000
  end
  return (nextInsn + rel) & 0xFFFFFFFF
end

local function scanUnique(pattern, label)
  local ok, addr = pcall(core.AOBScan, pattern)
  if not ok or addr == nil or addr == 0 then
    log(WARNING, "full-minimap: " .. label .. " not found; nothing changed")
    return nil
  end
  local duplicate = core.scanForAOB(pattern, addr + 1)
  if duplicate and duplicate ~= 0 then
    log(WARNING, "full-minimap: " .. label .. " signature is ambiguous; nothing changed")
    return nil
  end
  return addr
end

local function writeJump(site, target, patchSize)
  local code = { 0xE9, core.itob(core.getRelativeAddress(site, target, -5)) }
  for i = 6, patchSize do
    code[#code + 1] = 0x90
  end
  core.writeCode(site, code)
end

local M = {}

function M:enable(config)
  if type(config) == "table" and config.enabled == false then
    return
  end

  local scrollAddr = scanUnique(SCROLL_AOB, "scrollViewportToMinimapClick")
  local clickTileAddr = scanUnique(CLICK_TILE_AOB, "convertMinimapClickToTileXY")
  local mapSizeAddr = scanUnique(MAPSIZE_AOB, "drawMinimap mapSize read")
  local drawSetupAddr = scanUnique(DRAW_SETUP_AOB, "drawMinimap setup")
  local drawBlitAddr = scanUnique(DRAW_BLIT_AOB, "drawMinimap blit")
  local drawUnitNormalAddr = scanUnique(DRAW_UNIT_NORMAL_AOB, "drawMinimap normal unit plot")
  local drawUnitAltRAddr = scanUnique(DRAW_UNIT_ALTR_AOB, "drawMinimap Alt+R unit plot")

  if not (scrollAddr and clickTileAddr and mapSizeAddr and drawSetupAddr
      and drawBlitAddr and drawUnitNormalAddr and drawUnitAltRAddr) then
    return
  end

  local mouseX = readU32(scrollAddr + 0x01)
  local mouseY = readU32(scrollAddr + 0x0F)
  local vpW = readU32(scrollAddr + 0x1E)
  local vpX = readU32(scrollAddr + 0x37)
  local vpH = readU32(scrollAddr + 0x46)
  local vpState = readU32(scrollAddr + 0x55)
  local vpY = readU32(scrollAddr + 0x61)
  local setVpFunc = readRelTarget(scrollAddr + 0x6B, scrollAddr + 0x67)

  local clickMouseX = readU32(clickTileAddr + 0x0B)
  local clickMouseY = readU32(clickTileAddr + 0x25)
  if clickMouseX ~= mouseX or clickMouseY ~= mouseY then
    log(WARNING, "full-minimap: mouse global mismatch between click handlers; nothing changed")
    return
  end

  local mapSize = readU32(mapSizeAddr + 0x01)
  local surfacePtr = readU32(drawBlitAddr + 0x02)
  local surfacePitch = readU32(drawBlitAddr + 0x12)
  if readU32(drawBlitAddr + 0x57) ~= surfacePitch then
    log(WARNING, "full-minimap: surface pitch mismatch in drawMinimap blit; nothing changed")
    return
  end

  local setupSite = drawSetupAddr + 0x1E
  local setupResume = drawSetupAddr + 0x23
  local blitSite = drawBlitAddr
  local blitResumeVanilla = drawBlitAddr + 0x06
  local blitSkip = drawBlitAddr + 0x5E
  local unitNormalSite = drawUnitNormalAddr + 0x06
  local unitNormalResume = drawUnitNormalAddr + 0x0C
  local unitNormalSkip = drawUnitNormalAddr + 0x84
  local unitAltRSite = drawUnitAltRAddr + 0x06
  local unitAltRResume = drawUnitAltRAddr + 0x0C
  local unitAltRSkip = drawUnitAltRAddr + 0x84
  local clickTileSite = clickTileAddr + 0x0A
  local clickTileResume = clickTileAddr + 0x51
  local clickTileInvalid = readRelTarget(clickTileAddr + 0x0A, clickTileAddr + 0x06)

  local state = core.allocate(16, true)

  local setupStub = core.allocateAssembly(DRAW_SETUP_ASM, {
    STATE = state,
    MAP_SIZE = mapSize,
    VP_X = vpX,
    VP_Y = vpY,
    VP_H = vpH,
    RESUME = setupResume,
  })

  local blitStub = core.allocateAssembly(DRAW_BLIT_ASM, {
    STATE = state,
    SURFACE_PTR = surfacePtr,
    SURFACE_PITCH = surfacePitch,
    RESUME_VANILLA = blitResumeVanilla,
    SKIP_BLIT = blitSkip,
  })

  local unitNormalStub = core.allocateAssembly(DRAW_UNIT_ASM, {
    STATE = state,
    SURFACE_PTR = surfacePtr,
    SURFACE_PITCH = surfacePitch,
    RESUME_VANILLA = unitNormalResume,
    SKIP_PLOT = unitNormalSkip,
  })

  local unitAltRStub = core.allocateAssembly(DRAW_UNIT_ASM, {
    STATE = state,
    SURFACE_PTR = surfacePtr,
    SURFACE_PITCH = surfacePitch,
    RESUME_VANILLA = unitAltRResume,
    SKIP_PLOT = unitAltRSkip,
  })

  local scrollStub = core.allocateAssembly(SCROLL_CLICK_ASM, {
    MAP_SIZE = mapSize,
    MOUSE_X = mouseX,
    MOUSE_Y = mouseY,
    VP_W = vpW,
    VP_H = vpH,
    VP_X = vpX,
    VP_Y = vpY,
    VP_STATE = vpState,
    SET_VP_FUNC = setVpFunc,
  })

  local clickTileStub = core.allocateAssembly(CLICK_TILE_ASM, {
    MAP_SIZE = mapSize,
    MOUSE_X = mouseX,
    MOUSE_Y = mouseY,
    RESUME_LOOKUP = clickTileResume,
    INVALID_RET = clickTileInvalid,
  })

  writeJump(setupSite, setupStub, 5)
  writeJump(blitSite, blitStub, 6)
  writeJump(unitNormalSite, unitNormalStub, 6)
  writeJump(unitAltRSite, unitAltRStub, 6)
  writeJump(scrollAddr, scrollStub, 5)
  writeJump(clickTileSite, clickTileStub, 5)

  log(INFO, "full-minimap: enabled full-map scaling for minimap display, viewport frame, and clicks")
end

function M:disable() end

return M
