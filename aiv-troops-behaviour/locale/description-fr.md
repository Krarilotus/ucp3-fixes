# IA : Comportement des troupes AIV

Rétablit les positions AIV manquantes des piquiers et des deux types d’épéistes. Des réglages facultatifs contrôlent le rôle initial et les déplacements défensifs des 15 types de troupes.

Choisissez la défense ou le creusement, le maintien en position ou la patrouille. Utilisez des réglages communs ou propres à chaque troupe. Seules les troupes capables de creuser ont cette option.

Par IA : `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) et `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Sans suffixe de troupe, le réglage est commun à l’IA ; le rôle commun accepte seulement `"defend"`. Les remplacements AIC activés sont prioritaires ; les champs omis héritent.

Exemple : `AIVTroops_InitialRole_Slave: "dig"` affecte les esclaves au creusement. Consultez la [référence AIC](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour) pour les noms de troupes et les détails.

Les réglages des troupes sont désactivés au départ. Redémarrez le jeu et commencez une nouvelle partie après modification.
