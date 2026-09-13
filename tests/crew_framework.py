"""Test adapter for the actual supplied UCP core/cache/byte compiler.

Only memory allocation, memory IO and scanner transport are simulated. Native
instruction execution is separate; this adapter is never packaged in a module.
"""
from pathlib import Path
import re
import struct
import zipfile

from lupa.lua54 import LuaRuntime


class CrewFramework:
    def __init__(self, mapped, base, framework_zip):
        self.memory = bytearray(mapped)
        self.base = base
        self.next_code = 0x5001800
        self.patches = []
        self.allocations = {}
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        lua = self.lua

        def read(address, length):
            offset = address - base
            assert 0 <= offset <= len(self.memory) - length
            return bytes(self.memory[offset:offset+length])

        def allocate(length):
            address = self.next_code
            self.next_code += length
            self.allocations[address] = length
            assert self.next_code < 0x5002000
            return address

        def write(address, values):
            raw = bytes(values.values())
            self.patches.append((address, raw))
            if base <= address < base + len(self.memory):
                self.memory[address-base:address-base+len(raw)] = raw

        def scan(pattern, first, last):
            regex = re.compile(b''.join(b'.' if x == '?' else re.escape(bytes([int(x, 16)]))
                                        for x in pattern.split()), re.S)
            start = max(0, first - base)
            stop = min(len(self.memory), last - base + 1)
            match = regex.search(self.memory, start, stop)
            return base + match.start() if match else None

        lua.globals().ucp = lua.table_from({'internal': lua.table_from({
            'readInteger': lambda a: struct.unpack('<i', read(a, 4))[0],
            'readByte': lambda a: read(a, 1)[0],
            'readBytes': lambda a, n: lua.table_from(read(a, n)),
            'writeCode': write,
            'allocateCode': allocate,
            'scanForAOB': scan,
        })})
        with zipfile.ZipFile(framework_zip) as archive:
            lua.globals().core = lua.execute(archive.read('core.lua').decode())
            lua.execute('package.preload.core = function() return core end; log=function() end')
            lua.globals().utils = lua.execute(archive.read('utils.lua').decode())
            lua.globals().data = lua.table_from({'cache': lua.execute(archive.read('data/cache.lua').decode())})
        self.module = lua.execute((Path(__file__).resolve().parents[1] /
                                   'unit-behaviour-fixes/crew.lua').read_text())

    def prepare(self):
        return self.module.prepare()
