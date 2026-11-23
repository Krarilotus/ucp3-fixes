# Route Search

A shared building block for modules that change how units find their way. On its own it
changes nothing in the game.

Smarter Pathing (assassin shortcut) and Gatehouse Fixes (gate route rules) both change the
route search the game runs when a unit gets a new destination. Route Search lets them work
together: each adds its rule here, and every rule sees the right unit. Only versions of those
modules that depend on Route Search use it; they install it automatically.
