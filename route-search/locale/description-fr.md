# Recherche de chemin

Un composant partagé pour les modules qui modifient la façon dont les unités trouvent leur chemin. À lui seul, il ne change rien au jeu.

Smarter Pathing (raccourci pour les assassins) et Gatehouse Fixes (règles de passage par les portes) modifient la façon dont le jeu cherche un chemin lorsqu’une unité reçoit une nouvelle destination. Le module « Recherche de chemin » leur permet de fonctionner ensemble. Chacun y ajoute sa règle, et chaque règle tient compte de l’unité pour laquelle le jeu cherche un chemin. Seules les versions de ces deux modules qui déclarent « Recherche de chemin » comme dépendance l’utilisent et l’installent automatiquement.
