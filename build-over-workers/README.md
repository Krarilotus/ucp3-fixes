# Build Over Workers

Place buildings or walls where your own (and, optionally, your allies') workers are
standing; soldiers and enemy units still block. Anyone standing where a new building or
wall goes up, yours or the AI's, is moved to the nearest free tile next to it and walks
on, instead of being removed or left stuck inside.

Author: **Monsterfish**. Licensed under GPL-3.0 (`LICENSE`); see `CREDITS.md`.

- Targets Stronghold Crusader 1.41 and Stronghold Crusader Extreme 1.41
- Requires UCP framework 3.0.8 and frontend 1.0.2 or a compatible later version
- Writes no save data. Moved units keep their native position, height and destination,
  which the game saves as usual.

## Settings

| Option URL | Category | Default |
| --- | --- | --- |
| `build-over-workers.buildings` | Bugfixes | off |
| `build-over-workers.walls` | Bugfixes | off |
| `build-over-workers.keepOnWalls` (under walls) | Bugfixes | on |
| `build-over-workers.allies` | Balance Changes | off |

Placement over workers is off by default, so selecting the module alone keeps the game's
placement rules. `keepOnWalls` keeps people standing on a wall or stairs in place when the
wall is repaired; it does nothing while `walls` is off. With both `buildings` and `walls`
off the module scans and patches nothing.

`python tests/check_build_over_workers.py --framework <ucp/code.zip> <exe>...` runs the
module's AI wall path, with walls on and off, on licensed 1.41 executables.

## Release notes

- **1.1.1:** Building and wall placement over workers turn off separately, with an error,
  when their game code is not found.
- **1.1.0:** Placement over workers is off by default; after updating, switch it on in
  Customizations unless you saved it on. The switches also cover AI walls. A signature
  that matches more than once is refused before any change.
