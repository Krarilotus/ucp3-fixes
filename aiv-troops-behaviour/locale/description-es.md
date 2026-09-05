# IA: Comportamiento de tropas AIV

Restaura las posiciones AIV ausentes de piqueros y ambos tipos de espadachines. Los ajustes opcionales controlan el papel inicial y el movimiento defensivo de los 15 tipos de tropa.

Elige defender o cavar, mantener la posición o patrullar. Usa ajustes comunes o por tipo de tropa. Solo las tropas capaces de cavar tienen esa opción.

Por IA: `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) y `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Sin sufijo de tropa, el ajuste es común para la IA; el papel común solo acepta `"defend"`. Las anulaciones AIC activadas tienen prioridad; los campos omitidos heredan.

Ejemplo: `AIVTroops_InitialRole_Slave: "dig"` asigna esclavos a cavar. Los nombres de tropas y los detalles están en la [referencia AIC](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour).

Los ajustes de tropas comienzan desactivados. Reinicia el juego y comienza una partida nueva tras los cambios.
