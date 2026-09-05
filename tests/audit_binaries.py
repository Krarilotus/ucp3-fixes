"""Read-only optional check against legally installed game executables.

Usage: python tests/audit_binaries.py /path/to/executable [...]
Never modifies the executable or starts the game.
"""
import hashlib
import json
from pathlib import Path
import sys

import pefile
from test_modules import FIXTURES, ModuleHarness


def audit(path):
    raw = path.read_bytes()
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    memory = pe.get_memory_mapped_image()
    result = {'executable': path.name, 'sha256': hashlib.sha256(raw).hexdigest(), 'modules': {}}
    for name in FIXTURES:
        h = ModuleHarness(name, memory, base)
        h.enable({'enabled': True})
        pattern = bytes.fromhex(h.scans[0][0])
        first = memory.find(pattern)
        assert first >= 0 and memory.find(pattern, first + 1) == -1, (name, 'signature not unique')
        assert any(s.VirtualAddress <= first < s.VirtualAddress + s.Misc_VirtualSize and s.Characteristics & 0x20000000 for s in pe.sections), 'match outside executable section'
        result['modules'][name] = {
            'match': hex(base + first),
            'writes': [{'address': hex(a), 'length': len(b), 'bytes': b.hex(' ')} for a, b in h.writes],
        }
    assert path.read_bytes() == raw, 'audit must not change the game file'
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(json.dumps([audit(Path(p)) for p in sys.argv[1:]], indent=2))
