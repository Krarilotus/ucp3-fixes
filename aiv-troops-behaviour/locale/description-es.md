# IA: Comportamiento de tropas AIV

Restaura las posiciones AIV ausentes de piqueros y ambos tipos de espadachines. Los ajustes opcionales controlan el papel inicial y el movimiento defensivo de los 15 tipos de tropa.

Por cada tropa, elige como máximo una opción de cada par. Defender: ir a las posiciones AIV; Cavar: asignar las tropas iniciales a cavar fosos. Mantener: permanecer en un puesto defensivo; Patrullar: recorrer los puestos según los ajustes de patrulla AIC de la IA. Pulsa de nuevo una casilla marcada para desmarcar el par y usar el comportamiento del juego.

Por IA: `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) y `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Sin sufijo de tropa, el ajuste es común para la IA; el papel común solo acepta `"defend"`. Las anulaciones AIC activadas tienen prioridad; los campos omitidos heredan.

Ejemplo: `AIVTroops_InitialRole_Slave: "dig"` asigna esclavos a cavar. Los nombres de tropas y los detalles están en la [referencia AIC](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour).

Los ajustes de tropas comienzan desactivados. Reinicia el juego y comienza una partida nueva tras los cambios.
