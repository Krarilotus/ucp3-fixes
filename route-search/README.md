# Route Search

**One owner for a unit's route search.** Modules that change how a unit's route is searched
add a *policy* here. They no longer each redirect the same game call. Installed alone,
route-search changes nothing in the game.

## Why it exists

`UnitsState::setDestinationForUnit` asks `PathFindingState::doPathfinding(owner, canClimb)`
for every unit route through a single call. Smarter Pathing's assassin shortcut and Gatehouse
Fixes' route rules both need that call:

- The shortcut runs two candidate searches (ground, then climbing) and keeps the better one.
- The gate rules change what one search sees (enemy gates shut, stairs rules), retry it and
  can split a trip into two legs.

When each module redirects the call itself, the result depends on load order. Either the gate
rules read the wrong unit, or the shortcut runs inside every gate retry. route-search
redirects the call once and runs the policies in a fixed, documented order.

## The game code it uses

| What | How it is found | Checked |
| --- | --- | --- |
| The call in `setDestinationForUnit` | `0F BF 8E AA 06 00 00 8B 44 24 14 50 51 B9 ? ? ? ? E8 ? ? ? ? 3B C3 89 1D ? ? ? ? 0F 8E`, call at +18 | exactly one match; the caller tests `eax` against `ebx` (0) right after it |
| `PathFindingState::doPathfinding` | its code from the first instruction to its first `ret 8` | exactly one match; reads the same row table and area map twice; the call above must go there |

SHC 1.41: call at `0x53D7B4` → search at `0x4A9B20`. Crusader Extreme 1.41: `0x53DBD4` →
`0x4A9C90`. These addresses are evidence, not bindings; the module finds both at runtime.
The call is the only direct call of the search in either executable.

If either pattern is missing or matches more than once, or the call already goes somewhere
else, route-search refuses: `addPolicy` raises an error that names the problem, and the game
code stays unchanged.

## Calling convention (contract version 1)

```lua
local routes = modules["route-search"]          -- routes.version == 1
local slots = routes:addPolicy({ id = "my-module.rule", order = 200 })
-- slots.next: address of a dword holding the next stage (a policy or the game's search)
-- slots.unit: address of a dword holding the unit whose route is being searched
local entry = core.allocateAssembly(myCode, { NEXT = slots.next, UNIT = slots.unit })
routes:enablePolicy("my-module.rule", entry)
```

A policy's `entry` is called exactly like the game's search:

- `thiscall`: `ecx` = PathFindingState, `[esp+4]` = owner (player), `[esp+8]` = canClimb.
- It returns with `ret 8`, the route length in `eax` (0 or less: no route).
- It preserves `ebx`, `esi`, `edi` and `ebp`; `eax`, `ecx`, `edx` and flags are free.
- It may call `dword [next]` any number of times, with the same convention, to run the rest
  of the chain. It may also skip it.
- It reads the unit from `dword [unit]` (`UnitsState + index * 0x490`, the value of `esi` in
  `setDestinationForUnit`). Never from `esi`: an outer policy may have changed it.

route-search writes `next` and the outermost entry; a policy never writes them. The
redirected call goes to a 35-byte stub:

```
push dword [unit]        ; keep an outer search's unit (nested searches)
mov  [unit], esi
push dword [esp+0Ch]     ; canClimb
push dword [esp+0Ch]     ; owner
call dword [first]       ; the outermost enabled policy
pop  dword [unit]
ret  8
```

## Order

A lower `order` runs outside a higher one. The game's search is always innermost. Two
policies with the same order are refused, because their nesting would depend on load order.
Orders are integers from 1 to 999.

| Band | Kind of policy | Policies |
| --- | --- | --- |
| 100–199 | compares candidate searches and returns one of them | Smarter Pathing assassin shortcut: 100 |
| 200–299 | changes what a single search sees | Gatehouse Fixes route rules: 200 |
| other | reserved; ask before using | |

**Candidate policies (100–199) and a failed candidate.** An inner policy may change the unit
when it answers "no route". Gatehouse Fixes, for example, stops the unit where it stands.
`setDestinationForUnit` writes the route fields again when the final answer is a route. It
does not rewrite the order's final destination (unit `+0xEC`/`+0xEE`) or unit `+0x2D2`. A
candidate policy that returns a route must therefore put those two fields back as they were
when it was entered, in case an earlier or later candidate failed.

## Lifecycle

- `addPolicy` and `enablePolicy` work only while modules are enabled: after route-search's
  own `enable()` (declare `route-search` as a dependency) and before the game starts. The
  framework's `afterInit` hook closes registration.
- The call is redirected when the first policy is enabled. Policies may be enabled in any
  load order; the chain is rebuilt on each `enablePolicy`.
- There is no live removal. To change policies, change the settings and restart the game.
- At `afterInit`, route-search checks that the call still goes to its stub. If a module loaded
  later redirected it again, an error in the log names the policies affected.

`routes:policies()` lists the enabled policies in order (`id`, `order`, `entry`, `next`). Through the
framework's proxy, iterate it with `ipairs`; `#` does not see its length.

## Compatibility

| Module | Relation |
| --- | --- |
| Smarter Pathing, `assassinsShortcut` | uses route-search (order 100) from the version that depends on it |
| Gatehouse Fixes, `pathing.enemy_gates_closed`, `walls.stairs_needed`, `walls.stairs_needed_ai` | uses route-search (order 200) from the version that depends on it |
| Released Smarter Pathing 1.0.3–1.0.4 / Gatehouse Fixes 1.0.4–1.0.7 | redirect the call themselves. Loaded before the first route policy, route-search refuses. Loaded after, the `afterInit` check logs an error and the game runs with the route policies bypassed. Update them. Their unreleased guard versions (before route-search) refuse the combination themselves. |
| Legacy ladder climb, Smarter Walls, Build over Workers, Smarter Buildings, Improved Tunnelers, Outpost Control, Improved Siege Engines | patch other places of `setDestinationForUnit` or call it; none patches this call or the search |

Not covered by contract 1: `setDestinationForUnit`'s other search, used when its last
argument is not 0 (`call 0x4A9DD0` on SHC), and searches other game functions run directly.

## Tests

`tests/test_route_search.py` runs the module's own `init.lua` under Lua 5.4. It runs the
stub it writes, with test policies, in unicorn from `setDestinationForUnit`'s own
instructions. `tests/check_route_search.py <exe>...` does the same on licensed 1.41
executables.
