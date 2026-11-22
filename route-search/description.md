# Route Search

A shared building block for modules that change how units find their way. On its own it
changes nothing in the game.

Smarter Pathing (assassin shortcut) and Gatehouse Fixes (gate route rules) both need the
game's route search for a unit. This module lets them work together: each adds its rule
here, and every rule sees the right unit. Other modules install it automatically when they
need it.
