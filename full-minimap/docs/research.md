# Minimap Research (Phase 1)

## Verified Target Executables

Read-only verification against both Stronghold Crusader 1.41 executables:

| Executable | Size (bytes) | SHA-256 (first 16 hex) | `.text` VA range | Notes |
|---|---:|---|---|---|
| `Stronghold Crusader.exe` | 8,376,320 | `3bb0a8c1e72331b3` | `0x00401000..0x0059D806` | Matches OpenSHC `SHC_3BB0A8C1` reference binary |
| `Stronghold_Crusader_Extreme.exe` | 7,962,624 | `55648e6b05d67d37` | `0x00401000..0x0059DC36` | `MinimapViewState` methods shifted by `+0x170`; 0 structural instruction differences across all 5 inspected methods |

OpenSHC references inspected (`C:\Projects\UCP\OpenSHC`, commit `126f25c9`):
- `src/OpenSHC/UI/MinimapViewState.hpp`
- `src/OpenSHC/UI/MinimapViewState.func.hpp`
- `src/OpenSHC/UI/MiniMap/MiniMapDefinedData.hpp`
- `src/precomp/addresses-SHC-3BB0A8C1.hpp`

All findings below were verified directly from disassembly of both executables (Capstone x86-32).

---

## 1. How the Minimap Is Drawn

### 1.1 Pre-Rendered Full-Map Buffers in `MinimapViewState`

`DAT_MinimapViewState` (`0x01A31610` in SHC) owns two 16-bit (RGB555 or RGB565 per `DAT_DirectDrawPixelFormat == 0x565`) off-screen pixel buffers with a fixed row stride of 200 pixels (`0x190` bytes):

- `this + 0x27144` (`field18_0x27144[80000]`): base terrain color buffer, filled incrementally by `renderMinimapTileColors` (`0x004B58D0` SHC / `0x004B5A40` Ext) via `setTileColorsDependingOnMapSize` (`0x004B6680`).
- `this + 0x00044` (`field17_0x44[80000]`): composite terrain + buildings/structures buffer, filled incrementally by `renderMinimapTileStripWithLuminescence` (`0x004B5330` SHC / `0x004B54A0` Ext) via `setMapPropertyDependingOnMapSize` (`0x004B6640`). For tiles without a structure, it copies the pixel from `field18_0x27144`.

Both wrapper functions branch solely on `SEC_MapSize <= 200` vs `SEC_MapSize > 200`:

- **`SEC_MapSize <= 200` (160, 200)**: `flags = 4` (`oneOrTwo = 2`), `widthFactor = 4`, `heightFactor = 2` → **2 px per X-unit, 1 px per Y-unit** (1 buffer pixel per isometric tile along each screen axis).
- **`SEC_MapSize > 200` (300, 400)**: `flags = 4` (`oneOrTwo = 2`), `widthFactor = 2`, `heightFactor = 1` → **1 px per X-unit, 0.5 px per Y-unit** (0.5 buffer pixels per isometric tile; odd rows skipped during buffer fill).

Crucially, **`field17_0x44` already holds the entire map pre-rendered as a centered square** for every map size (and is immediately rebuilt for all 100 strips whenever `SEC_MapOrientation` changes at `0x004B6782`, or incrementally 2 strips per frame when `this + 0x38 != 0`):

| `SEC_MapSize` | Isometric X range (`minX_base..maxX_base`) | Isometric Y range (`minY_base..maxY`) | Vanilla `(wF, hF, oneOrTwo)` | Active square in `field17_0x44` | `bufDim` | `bufOff` |
|---:|---|---|---|---:|---:|---:|
| 160 | `60..140` (`spanX = 80`) | `120..280` (`spanY = 160`) | `(4, 2, 2)` | `[20, 180) × [20, 180)` | 160 | 20 |
| 200 | `50..150` (`spanX = 100`) | `100..300` (`spanY = 200`) | `(4, 2, 2)` | `[0, 200) × [0, 200)` | 200 | 0 |
| 300 | `25..175` (`spanX = 150`) | `50..350` (`spanY = 300`) | `(2, 1, 2)` | `[25, 175) × [25, 175)` | 150 | 25 |
| 400 | `0..200` (`spanX = 200`) | `0..400` (`spanY = 400`) | `(2, 1, 2)` | `[0, 200) × [0, 200)` | 200 | 0 |

In general, for any `mapSize` (defaulting `0` to `400`):
- `spanX = mapSize / 2`, `spanY = mapSize`
- `minX_base = (400 - mapSize) / 4`, `minY_base = (400 - mapSize) / 2`
- `bufDim = (mapSize <= 200) ? mapSize : (mapSize / 2)`
- `bufOff = (200 - bufDim) / 2`

### 1.2 Minimap Area Sizes & Callers of `drawMinimap`

`MinimapViewState::drawMinimap(xPos, yPos, width, height, flags, xOffset, yOffset, widthFactor, heightFactor, param_10)` (`0x004B66C0` SHC / `0x004B6830` Ext) has exactly four callers:

| Caller | SHC VA | Ext VA | Area (`W × H`) | Screen Origin | `flags` | `param_10` | Purpose |
|---|---|---|---|---|---|---:|---|
| `renderMinimapMain` | `0x004B7300` | `0x004B7470` | `126 × 126` (`0x7E`) | `[0xF2B3A0]+0x23B`, `[0xF2B3A4]+0x1D1` | `7` (`1\|2\|4`) | `0` | In-game HUD minimap |
| `renderMinimapLandscaping` | `0x004B7460` | `0x004B75D0` | `128 × 128` (`0x80`) | `[0xF2B3A0]+0x298`, `[0xF2B3A4]+0x1D0` | `7` (`1\|2\|4`) | `0` | Map editor landscaping minimap |
| `renderMinimapEditor` | `0x004B7530` | `0x004B76A0` | `100/150/160/200` | Menu-centered | `5` (`1\|4`) | `-1` | Map editor menu preview (already fits whole map) |
| `renderMiniMapForSaving` | `0x004B7600` | `0x004B7770` | `100/150/160/200` | Offset in `loadedMiniMap[200][200]` | `5` (`1\|4`) | `1` | Saved map/savegame thumbnail (must stay untouched) |

Only the two live interactive minimaps (`renderMinimapMain` and `renderMinimapLandscaping`) pass `param_10 == 0` and `(flags & 2) != 0`.

### 1.3 Where and Why the Minimap Scrolls

Inside `drawMinimap`:
1. `0x004B6844..0x004B6864` stores `width`, `height`, `widthFactor`, `heightFactor`, `x`, `y`, `oneOrTwo` into `MinimapViewState` fields `+0x18..+0x30`.
2. `0x004B6899..0x004B68BF` converts the pixel box into tile-space window spans:
   - `width_in_X = (width / widthFactor) * oneOrTwo` (`62` for 160/200 maps; `126` for 300/400 maps on `126×126`)
   - `height_in_Y = (height / heightFactor) * oneOrTwo` (`126` for 160/200 maps; `252` for 300/400 maps on `126×126`)
3. `0x004B68D1..0x004B68E2` compares `mapSize / 2` against `width_in_X`. Because `80 >= 62`, `100 >= 62`, `150 >= 126`, and `200 >= 126`, **every standard map size** takes the scrolling branch at `0x004B6970`:
   - Centers `[startX_tile, startY_tile]` around the viewport center `(xOffset, yOffset)` and clamps to `[minX, maxX - width_in_X]` and `[minY, maxY - height_in_Y]`.
   - Stores `this->startY` (`+0x10`) and `this->startX` (`+0x14`) at `0x004B6A27`.
4. `0x004B6B1D..0x004B6B7A` performs a 1:1 pixel copy (`width × height` ushorts) from `field17_0x44` starting at `(startX_buf, startY_buf)` onto `PTR_SurfacePointer3`.
5. `0x004B6B98..0x004B71FE` draws live units over the blitted background by walking the isometric screen-to-tile matrix (`0x021FD1B0`/`0x021FD1B8`, rotated by `SEC_MapOrientation`) over `[startX_tile - 2 .. startX_tile + width_in_X - 1]` × `[startY_tile .. startY_tile + height_in_Y - 1]`. It has two loops:
   - Normal player-color mode (`[altRToggleMinimapHideWildlife] == 0`, `0x004B6BA5..0x004B6EE9`), including wildlife, disguised units, assassin stealth, and blinking lord (`this + 0x40`).
   - Alt+R ally/enemy mode (`[altRToggleMinimapHideWildlife] != 0`, `0x004B6EEE..0x004B71FE`), hiding wildlife and coloring allies/enemies.
   Both loops converge on identical `oneOrTwo == 2` pixel-plot blocks (`0x004B6E36..0x004B6EB3` and `0x004B7146..0x004B71C3`) that divide `(x_raw, y_raw)` by `oneOrTwo` (`2`) and plot `word [ebp+0x14]` directly onto `PTR_SurfacePointer3`.

---

## 2. How Clicks on the Minimap Turn Into a Map Position

Two `MinimapViewState` methods handle minimap clicks; no other code outside `MinimapViewState` reads its scale/offset fields (`+0x10..+0x30`).

### 2.1 Camera Scroll (`scrollViewportToMinimapClick`, `0x004B5110` SHC / `0x004B5280` Ext)
- `0x004B5110..0x004B5133`: guard. With troops selected (`0x01FE7D20 == 0x3D` or `0x01FE7BEC == 1`), it scrolls only while the right button is held (`MouseState.rightClickState`, `0x00F2C9F8`). A left click then falls through to `MenuItemActionHandler_InGameMenu_UnitSelectionAndControlsUnk` (`0x004348D0`), which orders the troops to the tile from `convertMinimapClickToTileXY`; that handler ignores a right click over the minimap.
- `0x004B5134..0x004B519F`:
  ```c
  int tx = ((DAT_MouseXScreenSpace - this->x) / this->widthFactor) * this->oneOrTwo + this->startX;
  SEC_ViewportX = (tx - (DAT_ViewportWidth - 5) / 2) << 5;
  int ty = ((DAT_MouseYScreenSpace - this->y) / this->heightFactor) * this->oneOrTwo + this->startY;
  SEC_ViewportY = (ty - DAT_ViewportHeight / 2) << 3;
  DAT_ViewportRenderState->setViewportBasedOnMapSize();
  ```

### 2.2 Unit Command Click-to-Tile (`convertMinimapClickToTileXY`, `0x004B51A0` SHC / `0x004B5310` Ext)
- `0x004B51A0..0x004B51A9`: checks hover flag `this + 0x3C`; if 0, writes `(-1, -1)` and returns (`0x004B5260`).
- `0x004B51AA..0x004B51F0`:
  ```c
  int tx = ((DAT_MouseXScreenSpace - this->x) * this->oneOrTwo) / this->widthFactor + this->startX + 6;
  *outX = tx << 5;
  int ty = ((DAT_MouseYScreenSpace - this->y) * this->oneOrTwo) / this->heightFactor + this->startY;
  *outY = ty << 3;
  ```
- `0x004B51F1..0x004B525D`: applies `SEC_MapOrientation` (`0 / 6 / 4 / 2`), looks up the tile index in the screen-to-tile matrix (`0x021FD1C0`), and converts to logical `(tileX, tileY)` via `DAT_TileTranslationMatrix_YComponent` and `DAT_TileTranslationMatrix_X`.

---

## 3. How the Visible-Area Frame Is Drawn

- `drawMinimap` computes the viewport rectangle in minimap screen pixels:
  - `[ebp - 0x0C]` (`boxLeft`), `[ebp + 0x20]` (`boxTop`), `[ebp - 0x18]` (`boxWidth`), `[ebp - 0x40]` (`boxHeight`), and enable flag `[ebp - 0x3C]`.
- At `0x004B71FF..0x004B7295`, if `(flags & 2) != 0 && [ebp - 0x3C] != 0`, it clips the rectangle against `[xPos, xPos + width - 1]` and `[yPos, yPos + height]`, then calls:
  `PencilRenderCore::drawBorderBox(left, top, right, bottom, -1)` (`0x004711B0` SHC).
- Inspection of `drawBorderBox`'s line helpers (`0x00468DE0` horizontal, `0x00468E40` vertical) confirms both `right` and `bottom` are **inclusive** (`cmp eax, ebx; jg done`), so valid coordinates lie in `[xPos, xPos + W - 1]` × `[yPos, yPos + H - 1]`.

---

## 4. Compatibility & Reuse Inventory

### Framework & Subsystem Reuse
| Capability | Existing Owner / Symbol | Reuse Decision |
|---|---|---|
| AOB discovery | UCP3 framework `core.AOBScan` (each pattern checked unique offline in both executables) | Used directly |
| Code allocation, assembly, patching | UCP3 framework `core.allocate`, `core.allocateAssembly`, `core.writeCode`, `core.itob`, `core.getRelativeAddress` | Used directly |
| Pre-rendered terrain+building map cache | `MinimapViewState::renderMinimapTileColors` & `renderMinimapTileStripWithLuminescence` (`field17_0x44`) | Reused untouched — already renders the full map for all sizes and rotations |
| Live unit scan, stealth, wildlife, Alt+R, lord blink | `MinimapViewState::drawMinimap` unit loops | Reused untouched — only the two `oneOrTwo == 2` pixel-plot blocks are scaled |
| Surface lock & viewport frame rendering | `PencilRenderCore::setupPencilSurface` & `drawBorderBox` | Reused untouched |
| Viewport bounds clamping | `ViewportRenderState::setViewportBasedOnMapSize` | Reused untouched |
| Orientation & logical tile lookup for clicks | `MinimapViewState::convertMinimapClickToTileXY` tail (`0x004B51F1`) | Reused untouched |

### Module Overlap Check
Searched UCP3 framework (`Krarilotus--UnofficialCrusaderPatch3`), `Community-Paket-UCP3`, `Krarilotus--UnofficialCrusaderPatch`, and `_rq/repos/*`:
- `MapEditorImprovements` only calls `MinimapViewState::triggerMinimapRedraw` (`0x004B5300`) and reads the build-menu minimap item rect (`126×126`). Neither is modified.
- No other released or local module patches `drawMinimap`, `scrollViewportToMinimapClick`, or `convertMinimapClickToTileXY`.

---

## 5. Phase 2 Feasibility Decision: Proceed

Because `field17_0x44` already holds the complete map pre-rendered as a centered `bufDim × bufDim` square (`160`, `200`, `150`, or `200`) and `drawMinimap`'s own unit scanner already supports full-map bounds (used verbatim by `renderMiniMapForSaving`), **no renderer rewrite is needed**.

A minimal, clean 6-site hook set (all within `MinimapViewState`, all runtime-resolved via shared AOBs verified uniquely on both Crusader and Extreme) implements full-map scaling for every map size and both interactive minimaps (`126×126` in-game, `128×128` landscaping) while leaving editor/save previews untouched:

1. **`drawMinimap` setup hook (`0x004B6A45` SHC / `0x004B6BB5` Ext)**: When `param_10 == 0 && (flags & 2) != 0`, sets full-map tile bounds (`startX = minX_base`, `startY = minY_base`, `width_in_X = spanX`, `height_in_Y = spanY`), records `(active=1, bufDim, bufOff, twoBufDim)`, and computes the scaled, clamped visible-area frame into `[ebp-0x0C]/[ebp+0x20]/[ebp-0x18]/[ebp-0x40]` so vanilla's `drawBorderBox` draws it. Otherwise sets `active=0` and runs vanilla untouched.
2. **`drawMinimap` blit hook (`0x004B6B1D` SHC / `0x004B6C8D` Ext)**: When `active == 1`, nearest-neighbor scales `field17_0x44[bufOff..bufOff+bufDim)` into `W × H` on `PTR_SurfacePointer3` using 16.16 fixed-point DDA.
3. **`drawMinimap` unit-plot hooks (`0x004B6E36` / `0x004B7146` SHC; `0x004B6FA6` / `0x004B72B6` Ext)**: When `active == 1`, plots each detected unit pixel at `(xPos + (esi * W) / twoBufDim, yPos + (y_raw * H) / twoBufDim)` for both normal and Alt+R loops.
4. **`scrollViewportToMinimapClick` hook (`0x004B5134` SHC / `0x004B52A4` Ext)**: Maps clamped `(dx, dy)` via `(dx * spanX) / this->width + minX_base` and `(dy * spanY) / this->height + minY_base`, writes `SEC_ViewportX/Y`, and tail-jumps to `setViewportBasedOnMapSize`.
5. **`convertMinimapClickToTileXY` hook (`0x004B51AA` SHC / `0x004B5310+0xA` Ext)**: Maps clamped `(dx, dy)` identically (`+ 6` column offset preserved), stores `*outX`/`*outY`, and resumes vanilla's orientation/tile-matrix lookup at `+0x51`.
