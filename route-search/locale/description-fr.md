# Recherche de chemin

Un composant partagé pour les modules qui modifient la façon dont les unités trouvent leur chemin. À lui seul, il ne change rien au jeu.

Smarter Pathing (raccourci d'escalade des assassins) et Gatehouse Fixes (règles de trajet des portes) ont tous deux besoin de la recherche de chemin du jeu pour une unité. Ce module leur permet de fonctionner ensemble : chacun y ajoute sa règle, et chaque règle voit la bonne unité. Les autres modules l'installent automatiquement lorsqu'ils en ont besoin.
