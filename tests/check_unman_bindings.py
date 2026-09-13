"""Focused preflight rejection checks for the exit-equipment interior patch."""
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
        return h, h.lua.eval('require("unman").prepare')()
    h, install = prepare(mapped)
    install()
    site, = [a for a, b in h.patches if b == b'\x90' * 7]
    entry = site - 0x8c
    tail_offset = mapped.index(bytes.fromhex('0f bf 93'), site-base+7)
    # Select the continuation by its complete instruction prefix, not an address.
    while mapped[tail_offset+7:tail_offset+16] != bytes.fromhex('83 c0 01 3b c2 89 44 24 34'):
        tail_offset = mapped.index(bytes.fromhex('0f bf 93'), tail_offset+1)
    def reject(memory):
        try: prepare(memory)
        except LuaError: return
        raise AssertionError('Invalid unman context accepted')
    for offset in (site-base, site-base+3, entry-base+0x3c, entry-base+0x54, tail_offset+18):
        changed = bytearray(mapped)
        changed[offset] ^= 0x01
        reject(changed)
    duplicate = bytearray(mapped)
    duplicate[tail_offset-128:tail_offset-87] = mapped[tail_offset:tail_offset+41]
    reject(duplicate)
    for offset in (site-base, entry-base+0x3c, tail_offset+18):
        h, install = prepare(mapped)
        h.memory[offset] ^= 1
        try: install()
        except LuaError:
            assert not h.patches and not h.allocations
        else: raise AssertionError('Changed prepared context accepted')
    print(f'{path}: unman occupied/layout/UID/continuation/ambiguity/preflight passed', flush=True)
