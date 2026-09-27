"""Compare original fire damage with the actual framework-emitted crew patch.

All 80 unit type values are classification controls. Native callees are not
stubbed. This tests instruction behavior, not actual fire gameplay or casualties.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EBX,
    UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
from crew_framework import CrewFramework

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--framework', type=Path, required=True)
parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
args = parser.parse_args()
fixtures = [f for manifest in args.fixtures for f in json.loads(manifest.read_text())]
siege = {39, 40, 41, 58, 59, 60, 61, 77}
reports = []
for fixture in fixtures:
    path = Path(fixture.get('path', fixture.get('file')))
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
    pe = pefile.PE(data=raw)
    base, mapped = pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image()
    prefix = bytes.fromhex('8B 44 24 04 53 33 DB 3B C3 7F 06 33 C0 5B C2 0C 00 69 C0 90 04 00 00')
    hits = list(re.finditer(re.escape(prefix), mapped))
    assert len(hits) == 1
    entry = base + hits[0].start()
    harness = CrewFramework(mapped, base, args.framework)
    harness.prepare()()
    # Reference roots are confined to this hash-pinned test, not runtime bindings.
    units = 0x145ca28 if 'Extreme' in path.name else 0x1387f38
    record = units + 0x614 + 50 * 0x490

    def execute(kind, health, responsible, half, corrected):
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 0xfff) & ~0xfff)
        u.mem_write(base, mapped)
        u.mem_map(0x5000000, 0x2000)
        if corrected:
            for address, payload in harness.patches:
                u.mem_write(address, payload)
        def put(address, value, fmt='<I'):
            u.mem_write(address, struct.pack(fmt, value))
        u.mem_write(record, bytes(0x490))
        for offset, value in ((0x8c, 2), (0x8e, kind), (0x96, 1), (0x3b4, 2)):
            put(record+offset, value, '<H')
        put(record+0x98, 987654)
        put(record+0x3c8, health)
        put(record+0x3cc, 5000)
        stack, sentinel = 0x5000800, 0x5001000
        for offset, value in ((0, sentinel), (4, 50), (8, responsible), (12, half)):
            put(stack+offset, value)
        u.reg_write(UC_X86_REG_ESP, stack)
        u.reg_write(UC_X86_REG_ECX, units)
        writes = []
        def on_write(uc, access, address, size, value, user):
            writes.append((address, size, value))
        u.hook_add(UC_HOOK_MEM_WRITE, on_write)
        u.emu_start(entry, sentinel, count=10000)
        assert u.reg_read(UC_X86_REG_ESP) == stack+16
        regs = [u.reg_read(r) for r in (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP)]
        return bytes(u.mem_read(record, 0x490)), writes, regs

    cases = [(kind, health, 2, 0) for kind in range(80) for health in (1, 5000)]
    cases += [(kind, health, responsible, 1) for kind in sorted(siege | {5, 22, 30, 55})
              for health in (1, 5000) for responsible in (0, 1, 8)]
    for kind, health, responsible, half in cases:
        original, writes, regs = execute(kind, health, responsible, half, False)
        corrected, new_writes, new_regs = execute(kind, health, responsible, half, True)
        if kind not in siege or health == 5000:
            assert corrected == original and writes == new_writes and regs == new_regs, (kind, health, responsible, half)
        else:
            assert struct.unpack_from('<H', original, 0x8c)[0] == 4
            assert struct.unpack_from('<H', corrected, 0x8c)[0] == 2
            assert struct.unpack_from('<H', corrected, 0x2a0)[0] == 1
            assert struct.unpack_from('<H', corrected, 0x2c0)[0] == 114
            for offset, size in ((0x8e, 2), (0x96, 2), (0x98, 4), (0x3c8, 8), (0x400, 2)):
                assert original[offset:offset+size] == corrected[offset:offset+size]
            assert new_regs[0] == regs[0]
    reports.append({'path': str(path), 'cases': len(cases)})
    print(json.dumps(reports[-1]), flush=True)
print(json.dumps({'fixtures': len(reports), 'comparisons': sum(r['cases'] for r in reports)}))
