# IA : Comportement des troupes AIV

Rétablit les positions AIV manquantes des piquiers et des deux types d’épéistes. Des réglages facultatifs contrôlent le rôle initial et les déplacements défensifs des 15 types de troupes.

Pour chaque troupe, choisir au plus une option par paire. Défendre : rejoindre les positions AIV ; Creuser : affecter les troupes initiales au creusement des douves. Rester : garder un poste défensif ; Patrouille : circuler entre les postes selon les réglages de patrouille AIC de l’IA. Réinitialiser rétablit le comportement du jeu.

Par IA : `AIVTroops_InitialRole_<Troop>` (`"defend"` / `"dig"`) et `AIVTroops_Movement_<Troop>` (`"hold"` / `"patrol"`). Sans suffixe de troupe, le réglage est commun à l’IA ; le rôle commun accepte seulement `"defend"`. Les remplacements AIC activés sont prioritaires ; les champs omis héritent.

Exemple : `AIVTroops_InitialRole_Slave: "dig"` affecte les esclaves au creusement. Consultez la [référence AIC](https://github.com/UnofficialCrusaderPatch/UCP-Wiki/blob/docs/extension-aic-fields/docs/Stronghold-Crusader-Wiki/AI-Lords/AI-Character-Parameters.md#aiv-troop-behaviour) pour les noms de troupes et les détails.

Les réglages des troupes sont désactivés au départ. Redémarrez le jeu et commencez une nouvelle partie après modification.
