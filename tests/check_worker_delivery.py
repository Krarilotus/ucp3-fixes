"""Read-only native binding/ABI probe for user-supplied SHC/Extreme executables.

Usage: python tests/check_worker_delivery.py <game.exe> [more-game.exe ...]
No game files are stored in the module package or source repository.
"""
import argparse
import hashlib
from pathlib import Path
import re

from lupa.lua54 import LuaRuntime, LuaError
import pefile


MODULE = Path(__file__).resolve().parents[1] / 'worker-delivery-fix'


class Probe:
    def __init__(self, path):
        self.path = Path(path)
        raw = Path(path).read_bytes()
        pe = pefile.PE(data=raw)
        self.data = pe.get_memory_mapped_image()
        self.base = pe.OPTIONAL_HEADER.ImageBase
        self.extra = {}
        self.detours = []
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        core = self.lua.table()
        core.AOBScan = self.aob
        core.scanForAOB = self.scan
        core.readInteger = lambda a: self.read(a, 4)
        core.readSmallInteger = lambda a: self.read(a, 2)
        core.readByte = lambda a: self.read(a, 1)
        core.readBytes = lambda a, n: self.lua.table_from([self.read(a+i, 1) for i in range(n)])
        core.detourCode = lambda cb, a, n: self.detours.append((a, n, cb))
        self.lua.globals().core = core
        self.lua.globals().package.path = str(MODULE).replace('\\', '/') + '/?.lua'
        self.delivery = self.lua.execute('return (require("delivery"))')
        self.digest = hashlib.sha256(raw).hexdigest()

    def read(self, address, size):
        out = []
        for i in range(size):
            at = address + i
            if at in self.extra: out.append(self.extra[at])
            elif 0 <= at - self.base < len(self.data): out.append(self.data[at - self.base])
            else: raise AssertionError(f'Invalid read at {at:#x}')
        return int.from_bytes(bytes(out), 'little')

    def write(self, address, value, size):
        for i, byte in enumerate(value.to_bytes(size, 'little')):
            self.extra[address + i] = byte

    def scan(self, pattern, start=None, stop=None):
        rx = b''.join(b'.' if token == '?' else re.escape(bytes([int(token, 16)]))
                      for token in pattern.split())
        first = max(0, (start or self.base) - self.base)
        last = len(self.data) if stop is None else min(len(self.data), stop - self.base)
        found = re.search(rx, self.data[first:last], re.DOTALL)
        return self.base + first + found.start() if found else None

    def aob(self, pattern, start=None, stop=None):
        found = self.scan(pattern, start, stop)
        if found is None: raise RuntimeError('AOB not found: ' + pattern)
        return found

    def check(self):
        native = self.delivery.resolve()
        self.delivery.install(native)
        assert len(self.detours) == 1
        site, size, callback = self.detours[0]
        assert size == 5 and bytes(self.read(site+i, 1) for i in range(5)) == b'\x6a\x00\x50\x51\x55'
        building_flags = self.read(site - 7, 4)  # decoded native type-table operand
        assert [self.read(building_flags + kind*4, 4) for kind in (10, 11, 19)] == [1, 0, 0]
        s = native.sites
        assert s.accessible < site < s.custom
        # The original call stack has 12 local bytes and four saved registers.
        stack = self.base + 0x3000000
        buildings = self.base + 0x2800000
        building_id, unit_id = 7, 3
        building = buildings + building_id * 0x32c
        unit = native.units + unit_id * 0x490
        self.write(stack + 16, buildings, 4)
        self.write(stack + 28, s.producers + 0x100, 4)
        self.write(stack + 32, building_id, 4)
        self.write(buildings + 8, 100, 4)
        self.write(building + 0xea, 1, 2)
        self.write(building + 0xe6, 19, 2)
        self.write(native.currentSlot, unit_id, 4)
        self.write(native.maxUnitsAddress, 2500, 4)
        self.write(unit + 0x98, 1234, 4)
        self.write(unit + 0x96, 1, 2)
        self.write(unit + 0xc4, 10, 2)
        self.write(unit + 0xc6, 20, 2)
        self.write(native.rowOffsets + 20*12, 20*400, 4)
        self.write(native.areas + (20*400+10)*2, 9, 2)

        def call():
            return callback(self.lua.table_from({'ESP': stack, 'ESI': building,
                                                  'ECX': 3, 'EAX': 5, 'EBX': 0, 'EDI': 88}))

        cases = []
        assert call().ECX == 9
        cases.append('producer granary uses worker area')
        for kind, caller in ((19, s.storage + 0x109), (11, s.armory + 0x50)):
            self.write(building + 0xe6, kind, 2)
            self.write(stack + 28, caller, 4)
            assert call().ECX == 9
        cases.append('granary and armory selector calls use worker area')
        self.write(stack + 28, s.heatmap + 27, 4)
        assert call().ECX == 5
        self.write(building + 0xe6, 19, 2)
        assert call().ECX == 5
        self.write(building + 0xe6, 10, 2)
        assert call().ECX == 3
        self.write(building + 0xe6, 19, 2)
        assert callback(self.lua.table_from({'ESP': stack, 'ESI': building,
            'ECX': 3, 'EAX': 0, 'EBX': 0})).ECX == 3
        assert callback(self.lua.table_from({'ESP': stack, 'ESI': building,
            'ECX': 3, 'EAX': 5, 'EBX': 1})).ECX == 3
        cases.append('AI caller uses valid store area, not stockpile or invalid entry')
        self.write(stack + 28, s.afterProducers + 2, 4)
        assert call().ECX == 3
        cases.append('unrelated caller retains keep area')
        self.write(stack + 28, s.producers + 0x100, 4)
        self.write(building + 0xe6, 10, 2)
        assert call().ECX == 3
        cases.append('stockpile retains original special case')
        self.write(building + 0xe6, 19, 2)
        self.write(unit + 0x96, 2, 2)
        assert call().ECX == 3
        cases.append('different owner retains keep area')
        self.write(unit + 0x96, 1, 2)
        self.write(native.areas + (20*400+10)*2, 0, 2)
        assert call().ECX == 3
        cases.append('unlabelled region retains original check')
        self.write(native.areas + (20*400+10)*2, 9, 2)
        blocked_entry = self.lua.table_from({'ESP': stack, 'ESI': building, 'ECX': 3,
                                             'EAX': 5, 'EBX': 1, 'EDI': 88})
        assert callback(blocked_entry).ECX == 3
        cases.append('invalid entry remains with native fallback')
        self.data = bytearray(self.data)
        offset = site - self.base
        self.data[offset] = 0x90
        try:
            self.delivery.resolve()
        except (LuaError, RuntimeError):
            cases.append('missing route binding rejected')
        else: raise AssertionError('Missing route binding accepted')
        self.data[offset] = 0x6a
        target = offset + 0x1000
        saved = self.data[target:target+32]
        self.data[target:target+32] = self.data[offset:offset+32]
        try:
            self.delivery.resolve()
        except (LuaError, RuntimeError):
            cases.append('ambiguous route binding rejected')
        else: raise AssertionError('Ambiguous route binding accepted')
        self.data[target:target+32] = saved

        heat_offset = s.heatmap - self.base
        self.data[heat_offset] = 0x90
        try:
            self.delivery.resolve()
        except (LuaError, RuntimeError):
            cases.append('changed AI caller context rejected')
        else: raise AssertionError('Changed AI caller context accepted')
        self.data[heat_offset] = 0x0f

        self.data[offset] = 0x90
        try:
            self.delivery.install(native)
        except (LuaError, RuntimeError):
            assert len(self.detours) == 1
            cases.append('occupied after preflight rejected')
        else: raise AssertionError('Occupied route binding accepted')
        return {'file': str(self.path), 'sha256': self.digest, 'hook': hex(site), 'cases': cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executables', nargs='+', type=Path)
    for filename in parser.parse_args().executables:
        print(Probe(filename).check())
