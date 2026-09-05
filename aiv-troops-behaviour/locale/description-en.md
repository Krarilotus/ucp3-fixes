# AI: AIV Troop Behaviour

Restores missing AIV positions for pikemen and both swordsman types. Optional settings control starting roles and defender movement for all 15 troop types.

Choose whether troops defend or dig, and hold their position or patrol. Set common defaults or individual troop choices. Digging is only available to capable troops.

For individual AIs, use `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) and `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Leave off the troop suffix for a common AI setting; the common role accepts only `"defend"`. AIC overrides take priority when enabled; omitted fields inherit.

Example: `AIVTroops_InitialRole_Slave: "dig"` assigns slave diggers. See the [AIC field reference](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour) for troop names and details.

Troop settings start disabled. Restart and start a new match after changes.
