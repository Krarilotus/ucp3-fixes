"""Exercise the idle correction using supplied UCP and licensed PE fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from lupa.lua54 import LuaError
from crew_framework import CrewFramework

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--framework', type=Path, required=True)
parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
args = parser.parse_args()
for fixture in [f for p in args.fixtures for f in json.loads(p.read_text())]:
    path = Path(fixture.get('path', fixture.get('file')))
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
    pe = pefile.PE(data=raw)
    mapped, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    def prepare(memory):
        h = CrewFramework(memory, base, args.framework)
        return h, h.lua.eval('require("tunneler").prepare')()
    h, install = prepare(mapped)
    assert not h.patches and not h.allocations
    install()
    count = len(h.patches)
    install()
    assert len(h.patches) == count
    assert len(h.allocations) == 2 and sum(h.allocations.values()) == 40
    sites = [a for a, b in h.patches if b == b'\x90'*6]
    assert len(sites) == 2
    changed = {i for i, (a, b) in enumerate(zip(mapped, h.memory)) if a != b}
    assert changed <= {a-base+i for a in sites for i in range(6)}
    def rejected(memory):
        h = CrewFramework(memory, base, args.framework)
        try: h.lua.eval('require("tunneler").prepare')()
        except LuaError:
            assert not h.patches and not h.allocations
            return
        raise AssertionError('Invalid binding accepted')
    for site in sites:
        memory = bytearray(mapped)
        memory[site-base] = 0xe9
        rejected(memory)
        memory = bytearray(mapped)
        struct.pack_into('<I', memory, site-base+2,
                         struct.unpack_from('<I', memory, site-base+2)[0]+4)
        rejected(memory)
    memory = bytearray(mapped)
    start = sites[0]-base-14
    memory[start-64:start-64+45] = memory[start:start+45]
    rejected(memory)
    h, install = prepare(mapped)
    h.memory[sites[-1]-base] = 0xe9
    try: install()
    except LuaError: assert not h.patches and not h.allocations
    else: raise AssertionError('Changed prepared idle site accepted')
    # All OFF must work even on an unsupported image, without discovery.
    h = CrewFramework(b'unsupported', base, args.framework)
    init = h.lua.execute((Path(__file__).resolve().parents[1] / 'unit-behaviour-fixes/init.lua').read_text())
    init.enable(init, h.lua.table_from(dict(crew_lifecycle=False, tunneler_response=False)))
    assert not h.patches and not h.allocations
    # Both ON prepare first and share dispatch ownership; each OFF path installs
    # only the selected existing correction.
    for crew, idle, allocations in ((True, True, 11), (True, False, 9), (False, True, 2)):
        h = CrewFramework(mapped, base, args.framework)
        init = h.lua.execute((Path(__file__).resolve().parents[1] / 'unit-behaviour-fixes/init.lua').read_text())
        init.enable(init, h.lua.table_from(dict(crew_lifecycle=crew, tunneler_response=idle)))
        assert len(h.allocations) == allocations
    print(f'{path}: idle binding, occupied/layout/ambiguity/preflight, ON/OFF and crew composition passed')
