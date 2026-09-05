# Review evidence and release checks

Reviewed submission: `20ead193dd71b6d0b30a4c8a3c6c8569a1ace402`.
Review date: 2026-09-05. The proposed fixes are version 0.1.1.

## Compatibility and structure

The 3.0.7 extension-store branch was checked at
`f0ca949eb6cdace6ff6a56c8ab7b968616d5ebaa`. Its recipe pins framework commit
`77c6accf14a55fb95434fe6ffd96516e005568b5`.

- Both definitions correctly use `type: module`; these patches need `core`.
- The declared framework and frontend dependency ranges admit 3.0.7 and the
  frontend versions accepted by this store recipe.
- `ucp2-legacy` uses a central dispatcher with separate `init` (resolve) and
  `enable` (write) phases because it contains many fixes. These independent,
  single-fix modules do not need that dispatcher: each resolves its full patch
  before writing. They now use the same `UCP2Switch` / AI / Fixes presentation.
- Module selection already makes the fixes independently optional. The new
  boolean options additionally allow configuration plugins to disable them.
  Defaults preserve the behavior of existing module selections. Per-AI caps and
  per-row controls would change the scope and are not necessary for these fixes.
- Keeping the modules self-contained is preferable to a shared runtime helper
  dependency for two short entry points. AIV offsets are now a named list.
- Runtime disable explicitly returns failure with a restart message, consistent
  with the legacy module's unsupported runtime-disable contract.

The original `target == nil` branches were unreachable on failed scans:
`core.AOBScan` throws. The entry points now use that contract, provide a
module-specific error, and resolve before writing. They use the framework's
default cached scan path, and repeated enable calls do not apply patches twice.

## Binary inspection

Read-only inspection of these installed executables found exactly one match for
each module, inside an executable PE section. No executable was modified.

| Executable | SHA-256 | Hop comparison | AIV block |
| --- | --- | --- | --- |
| Stronghold Crusader.exe | `3bb0a8c1e72331b3a30a5aa93ed94beca0081b476b04c1960e26d5b45387ac5a` | `0x40AA42` | `0x4EF4B0` |
| Stronghold_Crusader_Extreme.exe | `55648e6b05d67d37a5773fe699bbb17a2d6ad4de1bb9dbded9a21caef82bd7fb` | `0x40AA52` | `0x4EF840` |

The hop signature now includes the preceding `movzx ecx, word ptr [edx]` and
following `test edi, edi`. These establish why the 32-bit subtract/range-check
replacement is valid despite the original comparisons using CX. The replacement
occupies exactly 18 bytes and its unsigned branch retains the original skip
destination. ECX is reloaded before the next relevant comparison.

The AIV patch writes exactly 18 bytes in total: three six-byte conditional jumps
at offsets 15, 26 and 37. No neighboring comparisons or count resets change.

## Troop coverage: slaves are not fixed

The row mapping agrees with OpenSHC's `src/OpenSHC/AI/AIVUnitType.hpp` and the
installed Crusader unit-type table at `0xB425E8`:

| AIV row | Troop | Effect of this module |
| --- | --- | --- |
| 9 | Pikeman | Previously skipped row is loaded |
| 11 | Swordsman | Previously skipped row is loaded |
| 18 | Arabian swordsman | Previously skipped row is loaded |
| 13 | Slave | No change; row already loads |
| All other rows | Other troops / AIV markers | No change |

Disassembly and local Ghidra decompilation of Crusader's `applyAIV` at
`0x4EF0D0` show that only 9, 11 and 18 are excluded from the row-decoding loop.
Coordinates are divided by **100**, not 400, before orientation and map
translation. The source documentation previously confused these coordinate spaces.

The downstream routines are distinct: `assignUnitToATribe` at `0x4D2660`,
`getUnitTypeIndexForUnitID` at `0x4CC390`, and movement/defense routines at
`0x4D4130`, `0x4D4220` and `0x4D4340`. In particular, `getUnitTypeIndexForUnitID`
can assign certain ranged units to row 13 during the first AIV pause for
non-Caliph AIs with row-13 positions. Those behaviors remain unchanged.
This establishes the narrow patch scope; it does not diagnose every reported
case of a slave or another unit failing to move. Reproducing those cases requires
the relevant map, AIV, AIC, starting troops and AI state.

## Automated checks

```sh
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
python tests/audit_binaries.py "/path/to/Stronghold Crusader.exe" "/path/to/Stronghold_Crusader_Extreme.exe"
```

The portable suite runs the actual Lua modules with an in-memory core adapter,
then executes their x86 output in Unicorn. It covers:

- Disabled options, existing empty configs and repeated enables.
- Missing/conflicting signatures causing an error before any writes.
- Refusal to patch a hop counter missing the required zero-extension.
- Unsupported runtime disable preserving the patch and reporting restart.
- The full 65,536-value building-type domain: exactly wheat, hops, apple and
  dairy are accepted; the skip target is correct.
- Original versus patched AIV checks for all rows 0–21: only 9, 11 and 18 change;
  row 13 remains identical.
- Definition, option URL, locale-key and package-input consistency, including
  English description fallback equality.

The optional PE audit invokes the Lua patches against memory-mapped copies of
the supplied binaries, checks signature uniqueness and executable sections,
reports write addresses, and verifies the source files remain unchanged.

These are isolated instruction and integration checks, not a new live gameplay
test or a signed store build. The author's prior Extreme gameplay observations
remain author-reported evidence.

## Before a stable store release

Both modules are reasonable **opt-in candidates** after the changes are accepted,
with the limited AIV scope made visible. Release validation still needs:

1. Launch both game variants through UCP 3.0.7 with the modules individually,
   together, and with `ucp2-legacy` and `aivloader`; verify enabled/disabled config
   behavior and signing through the normal store pipeline.
2. Compare hop farm counts, food production and recruitment on fixed map/AIV/AIC
   setups, including low farm caps, several AIs and long destruction/rebuild runs.
   A fixed counting omission does not establish a cure for recruitment collapse.
3. Check affected AIV troop positions with all keep orientations, several starting
   troop sets, enclosed/open keeps and defensive/patrol settings on both variants.
   Include row 13 as an unchanged control, plus save/load and multiplayer checks
   if these packages will be offered for those uses.
4. Build/sign each module from the accepted immutable commit. The 3.0.7 recipe
   needs string `contents.source.location` values and matching module versions.
   Add `de` to the store's language list if German store descriptions should be
   offered. Installed English/German descriptions and English fallback are
   already packaged by these modules.

No store recipe or store release is changed by this PR.
