"""Validate crew bindings against user-supplied, hash-pinned executable fixtures.

Example: python tests/check_crew_bindings.py --framework code.zip --fixtures matrix.json
Manifest entries require path (or file) and sha256. No game files are distributed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import pefile
from lupa.lua54 import LuaError

from crew_framework import CrewFramework


def run(fixtures, framework):
    results = []
    for fixture in fixtures:
        path = Path(fixture.get('path', fixture.get('file')))
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
        pe = pefile.PE(data=raw)
        mapped, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
        h = CrewFramework(mapped, base, framework)
        install = h.prepare()
        assert not h.patches
        install()
        count = len(h.patches)
        install()
        assert len(h.patches) == count
        assert len(h.allocations) == 9 and sum(h.allocations.values()) == 217
        sites = [a for a, payload in h.patches if base <= a < base + len(mapped) and payload == b'\x90'*6]
        assert len(sites) == 8
        fire_site = next(a for a, payload in h.patches if base <= a < base + len(mapped) and payload == b'\x90'*10)
        changed = {i for i, (a, b) in enumerate(zip(mapped, h.memory)) if a != b}
        expected = {a-base+offset for a in sites for offset in range(6)} | {a-base+7 for a in sites}
        expected |= set(range(fire_site-base, fire_site-base+10))
        assert changed <= expected
        cases = ['prepare-without-writes', 'all-eight-owned-guards', 'idempotence', 'bounded-production-diff']

        def rejected(memory, label):
            candidate = CrewFramework(memory, base, framework)
            try:
                candidate.prepare()
            except LuaError:
                assert not candidate.patches and not candidate.allocations
                cases.append(label)
                return
            raise AssertionError('Binding accepted ' + label)

        memory = bytearray(mapped)
        memory[sites[-1]-base] = 0xe9
        rejected(memory, 'occupied-last-guard')
        memory = bytearray(mapped)
        struct.pack_into('<I', memory, sites[-1]-base+2,
                         struct.unpack_from('<I', memory, sites[-1]-base+2)[0] + 4)
        rejected(memory, 'inconsistent-layout-operand')

        # Insert a second matching guard inside its real native handler. Its
        # original loop is retained at the later address, so first-match-only
        # resolution would patch an unintended location in this modified image.
        memory = bytearray(mapped)
        memory[sites[0]-base-64:sites[0]-base-39] = memory[sites[0]-base:sites[0]-base+25]
        rejected(memory, 'duplicate-within-handler')

        memory = bytearray(mapped)
        pattern = bytes.fromhex('0F BF 91 A2 06 00 00 8B 04 95')
        dispatch = mapped.index(pattern)
        memory[dispatch+64:dispatch+91] = memory[dispatch:dispatch+27]
        rejected(memory, 'duplicate-dispatch')

        memory = bytearray(mapped)
        memory[fire_site-base] = 0xe9
        rejected(memory, 'occupied-fatal-fire-selector')

        # AIC owns an entry observer; our interior fire gate must remain resolvable.
        memory = bytearray(mapped)
        fire_entry = mapped.index(bytes.fromhex('8B 44 24 04 53 33 DB 3B C3 7F 06 33 C0 5B C2 0C 00 69 C0 90 04 00 00'))
        memory[fire_entry:fire_entry+5] = bytes.fromhex('E9 00 00 00 00')
        observed = CrewFramework(memory, base, framework)
        observed.prepare()
        assert not observed.patches
        cases.append('independent-of-fire-entry-observer')

        pending = CrewFramework(mapped, base, framework)
        install = pending.prepare()
        pending.memory[sites[-1]-base] = 0xe9
        try:
            install()
        except LuaError:
            assert not pending.patches and not pending.allocations
            cases.append('occupied-after-prepare')
        else:
            raise AssertionError('Changed prepared site accepted')
        results.append({'path': str(path), 'sha256': fixture['sha256'], 'cases': cases,
                        'codeBytes': sum(h.allocations.values()), 'patchedBytes': 66})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--framework', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
    args = parser.parse_args()
    fixtures = [f for manifest in args.fixtures for f in json.loads(manifest.read_text())]
    result = run(fixtures, args.framework)
    print(json.dumps({'fixtures': len(result), 'cases': sum(len(r['cases']) for r in result),
                      'results': result}, indent=2))
