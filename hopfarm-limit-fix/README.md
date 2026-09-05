# Hop Farm Limit Fix

**Status: test version. Statically analysed and confirmed to patch at runtime;
the long-term gameplay effect is still being evaluated.**

## What it does

Makes AI hop farms count towards the same AIV farm limit as wheat, apple and
dairy farms. Without this, hop farms are not counted, so the AI builds more of
them than intended.

## The bug

When the AI wants to build a farm, it passes through a gate (`0x4CB470`) that
counts its existing farms and compares the count against the farm limit in its
AIV data (field `+0x74`). The counting routine it calls, `0x40AA20`, checks
building types `0x1E` (wheat), `0x20` (apple) and `0x21` (dairy) — but not
`0x1F` (hops).

A second, correct copy of the same count exists at `0x40CB20` (used elsewhere)
and checks all four farm types. The jump distances prove the omission: the
broken copy is missing exactly the 6 bytes of the `cmp cx, 0x1F` / `je`.

## Effect

Because hop farms are not counted, they slip through the gate as long as the
food-farm count is under the limit. They are not built "without limit", but
they are systematically not counted, so over long games — with farms being
destroyed and rebuilt — hop farms accumulate beyond their intended share and
their workers occupy population.

Measured, one map vs. the Abbot: without the fix the AI reached ~7 hop farms,
with the fix ~5. The direction is consistent with the bug; the magnitude at a
given point in time is modest and grows over long games. Whether this bug alone
explains the late-game "can no longer recruit" collapse is not yet proven and
needs a long A/B test.

## The fix

The three separate type comparisons (18 bytes at `0x40AA52`) are replaced by one
range check `0x1E <= type <= 0x21`:

```
sub ecx, 0x1E
cmp ecx, 3
ja  skip        ; same target as the original jne
nop (x10)
```

No code is relocated. The register is reloaded every loop iteration and unused
after the check. Located via an AOB scan that also checks the preceding zero-extension and
following flag-reset instruction. A failed scan raises an initialization error
before any writes on unsupported or conflicting executables.

## Scope and side effect

`0x40AA20` has exactly one caller (the farm gate), so the change is local to
farm-building and does not touch food or economy planning anywhere else.
Because hop farms now share the limit, AIs with a tight farm limit build
slightly fewer food farms in exchange. This is the correct semantics but it
shifts the balance of existing AIVs; check the farm-limit values (AIV field
`+0x74`) before relying on it in a tournament setting.

## Addresses (Extreme, ImageBase 0x400000)

| Address    | Meaning                                          |
|------------|--------------------------------------------------|
| `0x40AA20` | farm counter missing hops — the bug              |
| `0x40AA52` | patch site, 18 bytes                             |
| `0x40CB20` | correct farm counter, all four types (reference) |
| `0x4CB470` | AI farm-build gate, sole caller of 0x40AA20      |
| `0x4CB4B9` | limit compare `cmp ecx, [esi+0x74]`              |
| `0x4F1A64` | dispatch call into the farm gate                 |

## Configuration and review

The enable switch appears under **AI → Fixes**. It defaults to on when this module
is selected; existing configs without the option retain that behavior. Disable
it and restart to restore the original counting behavior. The fix respects the
existing AIV farm limit rather than introducing a separate configurable cap.

The review confirmed the comparison block at `0x40AA42` in Crusader and
`0x40AA52` in Crusader Extreme. The `movzx ecx, word ptr [edx]` before the patch
makes the 32-bit range check valid; ECX is dead after the check and flags are
reset by the following `test edi, edi`. See `docs/validation.md` in the source
repository for hashes and test coverage. No claim that this prevents late-game
recruitment collapse is made.
