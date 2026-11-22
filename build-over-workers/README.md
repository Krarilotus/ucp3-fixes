# Build Over Workers

Place buildings or walls where your own (and, optionally, your allies') workers are
standing; soldiers and enemy units still block. Anyone standing where a new building or
wall goes up, yours or the AI's, is moved to the nearest free tile next to it and walks
on, instead of being removed or left stuck inside. What the module does, in plain
English, is in `locale/description-en.md`.

Author: **Monsterfish**. Relicensed by the author under GPL-3.0 for inclusion in this
repository; consent relayed by Krarilotus on 2026-11-22. Merged from the reviewed
`Krarilotus/Build-over-Workers@b6caee5` (Monsterfisch/Build-over-Workers#1, "building
and wall switches really turn the behaviour off, including AI walls"). See `CREDITS.md`.

- Package version: **1.1.0** (Monsterfish's last release: 1.0.3)
- Targets: Stronghold Crusader 1.41 and Stronghold Crusader Extreme 1.41
- Requires UCP framework 3.0.7 and frontend 1.0.2 or a compatible later version
- Writes no save data: no Map Extensions section, no files. Moved units keep their
  native position, height and destination, which the game saves as usual.

## Settings

| Option URL | Category | Default |
| --- | --- | --- |
| `build-over-workers.buildings` | Bugfixes | off |
| `build-over-workers.walls` | Bugfixes | off |
| `build-over-workers.keepOnWalls` (under walls) | Bugfixes | on |
| `build-over-workers.allies` | Balance Changes | off |

Placement over workers is off by default (`buildings`, `walls`, `allies`), so selecting the
module alone keeps the game's placement rules. `keepOnWalls` stays on: it is the 1.0.2
protection that keeps people standing on a wall or stairs in place when the wall is
repaired, and it does nothing while `walls` is off. The **UCP3 Recommended** setup turns
everything on, which is the 1.0.3 behaviour.
With both `buildings` and `walls` off the module scans and patches nothing. The option
URLs are unchanged from 1.0.3, so saved profiles keep their values.

## Release notes

- **1.1.0:** Merged into ucp3-fixes under GPL-3.0. Placement over workers is off by
  default (`keepOnWalls` stays on); the UCP3 Recommended setup turns it on. Signatures
  that match more than once are refused before any change. Players who added the module on its own will
  see it switched off after updating; switch the parts on again in Customizations or
  select UCP3 Recommended. Settings you saved explicitly stay as they are. Includes
  Monsterfisch/Build-over-Workers#1 (the switches really turn the behaviour off,
  including AI walls) and its translation update.

## Emulator bench

`bench/test_bow.py` runs the module's own Lua unchanged against the real executable
images, assembles its code with UCP's own `fasm.dll` and executes it on a small x86
interpreter: building and wall placement tests, remembered tiles, AI walls and moving
the units afterwards, on both executables, with every switch on, with allies off, with
each part alone and unconfigured. It is a local tool, not part of the portable suite in
`tests/` (which CI runs), because it needs:

- Python with `lupa`, `capstone` and `pefile` (see `tests/requirements.txt`);
- `SHC_GAME_DIR`: a folder with `Stronghold Crusader.exe` and
  `Stronghold_Crusader_Extreme.exe` 1.41 (read only);
- `UCP_FASM_DLL`: `fasm.dll` from a UCP install (`vendor/fasm/fasm.dll` inside
  `ucp/code.zip`), loaded by 32-bit Windows PowerShell through `fasm32_margin.ps1`;
- optionally `BOW_FASM_CACHE` for the assembled-code cache (default `bench/fasm_cache`).

```sh
python build-over-workers/bench/test_bow.py
```

It prints `N checks, 0 failed` when green. Addresses are found by the bench
independently of the module. `tests/test_build_over_workers.py` covers the package
contract and the off path without a game.

Not carried over from the source repository: `tools/publish.py` (this repository builds
packages with `tools/build_modules.py`) and the bench's `host.py`/`x86emu.py` copies,
which only provided the FASM helpers now in `bench/harness.py`.
