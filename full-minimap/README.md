# Full Minimap (UCP3 Module)

UCP3 module (`full-minimap`) for Stronghold Crusader 1.41 and Stronghold Crusader Extreme 1.41 (framework `^3.0.8`).

Scales the entire map to fit the interactive minimap (`126x126` in-game and `128x128` in landscaping) on every map size (`160`, `200`, `300`, `400`), updating:
- terrain and building background blit from `MinimapViewState`'s pre-rendered full-map buffer;
- live unit dots in both normal and Alt+R modes (preserving stealth, wildlife, disguised units, blinking lord, and all 4 map rotations);
- the white visible-area viewport frame;
- click/drag camera scrolling and the move target of a minimap left-click with troops selected (as in vanilla, a right-click then pans the camera).

Editor preview and map/save thumbnail rendering are left untouched. See `docs/research.md` for binary analysis details.
