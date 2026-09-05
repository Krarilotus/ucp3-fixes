# AIV Troop Spot Fix

Restores loading of **pikemen, swordsmen and Arabian swordsmen** positions in
AIV rows **9, 11 and 18**. See [description.md](description.md) for the user-facing
scope and enable switch. Requires Crusader / Crusader Extreme 1.41 and UCP3.

## What changes

AIV section 2012 is a 24 × 10 matrix of local positions encoded as `y * 100 + x`.
The engine rotates/translates those local coordinates into game map tiles.
The loader processes rows 0–21 but explicitly skips rows 9, 11 and 18 after
resetting their counts. The module replaces only those three six-byte `je`
instructions with NOPs, preserving all comparisons and the count reset.

The author's original test on Crusader Extreme reported that the affected rows
loaded and troops moved to their spots. The review also confirmed the matching
instructions in both local 1.41 executables; see [validation](../docs/validation.md)
in the source repository for the evidence and remaining gameplay checks.

## What does not change

**Slaves (row 13) and all other rows are unchanged.** Row 13 is already loaded
without this patch. Troop assignment, movement, defensive behavior and patrol
rules are separate from the loader. For example, the existing engine can assign
certain ranged units to row 13 during the first AIV pause for non-Caliph AIs.
This module does not modify that rule. It is not a general fix for all units
that fail to reach a desired position, nor a claim of Definitive Edition parity.

## Patch locations

| Executable | Start of matched block | Removed jump offsets |
| --- | --- | --- |
| Crusader 1.41 | `0x4EF4B0` | `+15`, `+26`, `+37` |
| Crusader Extreme 1.41 | `0x4EF840` | `+15`, `+26`, `+37` |

Addresses are review references, not hardcoded patch destinations. An AOB scan
resolves the full block before any writes; a failed scan raises an initialization
error. Disable the option and restart to use the original behavior.
