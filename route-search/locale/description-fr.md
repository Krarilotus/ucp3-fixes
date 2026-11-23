# Recherche de chemin

Un composant partagé pour les modules qui modifient la façon dont les unités trouvent leur chemin. À lui seul, il ne change rien au jeu.

Smarter Pathing (raccourci d'escalade des assassins) et Gatehouse Fixes (règles de trajet des portes) modifient tous deux la recherche de chemin que le jeu lance lorsqu'une unité reçoit une nouvelle destination. La Recherche de chemin leur permet de fonctionner ensemble – chacun y ajoute sa règle, et chaque règle voit la bonne unité. Seules les versions de ces modules qui en dépendent l'utilisent et l'installent automatiquement.
