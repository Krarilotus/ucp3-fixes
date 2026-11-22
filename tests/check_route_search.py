"""Check route-search on licensed Stronghold Crusader 1.41 executables (read-only).

Usage: python tests/check_route_search.py <game.exe> [more-game.exe ...]

Maps each executable's image, runs route-search's own init.lua against it, enables two test
policies (a candidate comparer at order 100 outside a recorder at order 200) and runs the
game's own setDestinationForUnit instructions around the redirected call in unicorn, with the
game's search replaced by a recorder. Never modifies the executable or starts the game.
"""
import hashlib
from pathlib import Path
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

from route_search_harness import (Space, RouteSearch, Emulator, d, pattern_regex,
                                  recording_policy, comparing_policy)

SITE_START = 18      # the call's offset in route-search's site pattern


def check(path):
    raw = Path(path).read_bytes()
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    image = pe.get_memory_mapped_image()
    space = Space(image, base, size=(len(image) + 0x500000 + 0xFFFF) & ~0xFFFF)
    rs = RouteSearch(space)
    rs.enable()
    log, count = space.allocate(64), space.allocate(4)
    outer_next, unit = rs.add('test.comparer', 100)
    inner_next, _ = rs.add('test.recorder', 200)
    inner = space.allocate(64)
    space.write(inner, recording_policy(unit, inner_next, log, count))
    outer = space.allocate(64)
    space.write(outer, comparing_policy(outer_next))
    rs.enable_policy('test.recorder', inner)
    rs.enable_policy('test.comparer', outer)
    rs.fire_after_init()
    assert not [m for level, m in rs.logs if level != 'INFO'], rs.logs

    (call, patch), = rs.code_writes
    site = call - SITE_START
    original = image[call - base:call - base + 5]
    search = call + 5 + struct.unpack('<i', original[1:])[0]
    head = call + 5 + struct.unpack('<i', patch[1:])[0]
    assert original[0] == 0xE8 and patch[0] == 0xE8
    callers = [base + m.start() for m in pattern_regex('E8').finditer(image)
               if base + m.start() + 5 + struct.unpack('<i', image[m.start() + 1:m.start() + 5])[0] == search]
    assert callers == [call], ('direct callers of the search', [hex(c) for c in callers])
    text = [ins.mnemonic for ins in Cs(CS_ARCH_X86, CS_MODE_32).disasm(space.read(head, 35), head)]
    assert text == ['push', 'mov', 'push', 'push', 'call', 'pop', 'ret'], text

    unit_record = space.allocate(0x900)
    space.put16(unit_record + 0x6AA, 4)                  # owner
    space.put32(unit, 0x13572468)                        # an outer search's unit
    emulator = Emulator(space, search, unit, [25, 17])
    regs = {'esi': unit_record, 'ebx': 0, 'edi': 0x1111, 'ebp': 0x2222, 'eax': 0, 'ecx': 0, 'edx': 0}
    out, sp = emulator.run(site, call + 5, regs, stack=[0, 0, 0, 0, 0, 1, 0])
    state = struct.unpack('<I', image[site + 14 - base:site + 18 - base])[0]
    assert out['eax'] == 42 and out['esp'] == sp
    assert (out['ebx'], out['esi'], out['edi'], out['ebp']) == (0, unit_record, 0x1111, 0x2222)
    assert emulator.calls == [dict(ecx=state, owner=4, climb=1, unit=unit_record)] * 2, emulator.calls
    assert (emulator.u32(count), emulator.u32(log), emulator.u32(log + 4)) == (2, unit_record, unit_record)
    assert emulator.u32(unit) == 0x13572468
    return ('%s sha256 %s: call 0x%X -> search 0x%X (only caller), PathFindingState 0x%X; stub 35 bytes; '
            'order 100 outside 200; two game searches, each for the right unit; registers, '
            'stack and [unit] restored' % (Path(path).name, hashlib.sha256(raw).hexdigest()[:16],
                                           call, search, state))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for executable in sys.argv[1:]:
        print(check(executable))
