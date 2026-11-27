"""Run Build Over Workers' AI wall path on licensed 1.41 executables (read-only).

The module's own init.lua runs under Lua 5.4 with `core` on a Unicorn address space that
holds the executable image; its FASM templates are assembled by UCP's fasm.dll (from the
framework's code.zip, called through 32-bit Windows PowerShell). For each executable:

- walls on: validateWallPlacementAtTile keeps a unit standing on a new AI wall tile and
  remembers the tile; with the tile queue full the game removes the unit; the end of
  placeDefensiveStructureTile moves the remembered unit next to the wall;
- walls off (buildings on): the AI wall code stays the game's and removes the unit.

Usage: python tests/check_build_over_workers.py --framework <ucp/code.zip> <exe>...
"""
import argparse
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zipfile

from lupa.lua54 import LuaRuntime, LuaError, lua_type
import pefile
from test_modules import unique_hit
from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EBX,
    UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EIP)

MODULE = Path(__file__).resolve().parents[1] / 'build-over-workers'
MASK, PAGE = 0xFFFFFFFF, 0x1000
HEAP, STACK_TOP, SENTINEL = 0x60000000, 0x70100000, 0x7FFFF000
REG = dict(eax=UC_X86_REG_EAX, ecx=UC_X86_REG_ECX, edx=UC_X86_REG_EDX, ebx=UC_X86_REG_EBX,
           esp=UC_X86_REG_ESP, ebp=UC_X86_REG_EBP, esi=UC_X86_REG_ESI, edi=UC_X86_REG_EDI)
# fasm_Assemble from UCP's fasm.dll with the buffer size core.allocateAssembly uses.
FASM_PS1 = r'''param([string]$asm, [string]$dll)
Add-Type -TypeDefinition @"
using System; using System.Runtime.InteropServices;
public static class Fasm {
  [DllImport(@"$dll", CallingConvention=CallingConvention.StdCall, CharSet=CharSet.Ansi)]
  public static extern int fasm_Assemble(string source, IntPtr memory, int size, short passes, IntPtr pipe);
}
"@
$mem = [Runtime.InteropServices.Marshal]::AllocHGlobal(64000)
[void][Fasm]::fasm_Assemble([IO.File]::ReadAllText($asm), $mem, 64000, 100, [IntPtr]::Zero)
if ([Runtime.InteropServices.Marshal]::ReadInt32($mem, 0) -ne 0) { exit 3 }
$len = [Runtime.InteropServices.Marshal]::ReadInt32($mem, 4)
$bytes = New-Object byte[] $len
[Runtime.InteropServices.Marshal]::Copy([Runtime.InteropServices.Marshal]::ReadIntPtr($mem, 8), $bytes, 0, $len)
[IO.File]::WriteAllBytes([IO.Path]::ChangeExtension($asm, "bin"), $bytes)
'''
AI_WALL_UNITS = '0F B7 84 77 E0 D7 23 00 66 85 C0 74 30 F7 84 B7 60 51 16 00 00 01 00 00'
POWERSHELL32 = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'


def regex(pattern):
    return re.compile(b''.join(b'.' if t == '?' else re.escape(bytes([int(t, 16)]))
                               for t in pattern.split()), re.S)


class Game:
    """One executable image in Unicorn, with the module enabled on it."""

    def __init__(self, exe, work, config):
        pe = pefile.PE(str(exe), fast_load=True)
        self.raw = exe.read_bytes()
        self.base = pe.OPTIONAL_HEADER.ImageBase
        self.sections = [(self.base + s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)
                         for s in pe.sections]
        self.executable = [(self.base + s.VirtualAddress, s.SizeOfRawData)
                           for s in pe.sections if s.Characteristics & 0x20000000]
        self.work = work
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.hook_add(UC_HOOK_MEM_UNMAPPED, lambda uc, access, address, size, value, data:
                         self.map(address) or True)
        self.uc.hook_add(UC_HOOK_CODE, self.on_code)
        self.heap, self.detours, self.exposed, self.calls, self.logs = HEAP, {}, {}, [], []
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        g.INFO, g.WARNING, g.ERROR = 0, 1, 2
        g.log = lambda level, message: self.logs.append(str(message))
        core = lua.table()
        core.AOBScanUnique = lambda pattern: unique_hit(
            [va + match.start() for va, size in self.executable
             for match in regex(pattern).finditer(self.read(va, size))])
        core.readInteger = lambda a: struct.unpack('<i', self.read(a, 4))[0]
        core.readSmallInteger = lambda a: struct.unpack('<h', self.read(a, 2))[0]
        core.readByte = lambda a: struct.unpack('<b', self.read(a, 1))[0]
        core.writeByte = lambda a, v: self.write_data(a, bytes([int(v) & 0xFF]))
        core.writeInteger = lambda a, v: self.write_data(a, struct.pack('<I', int(v) & MASK))
        core.writeCode = lambda a, t: self.poke(int(a), self.flatten(t))
        core.allocate = lambda size, zero=None: self.allocate(int(size))
        core.allocateCode = lambda t: self.place(self.flatten(t))
        core.allocateAssembly = self.assemble
        core.detourCode = lambda fn, a, n: self.detours.__setitem__(int(a), fn)
        core.exposeCode = lambda a, n, cc: (lambda *args: self.call(int(a), [int(x) for x in args]))
        core.itob = lambda v: lua.table_from(list(struct.pack('<I', int(v) & MASK)))
        core.getRelativeAddress = lambda f, t, o=0: (int(t) - int(f) + int(o)) & MASK
        g.core = core
        g.package.path = str(MODULE).replace('\\', '/') + '/?.lua'
        module = lua.execute((MODULE / 'init.lua').read_text(encoding='utf-8'))
        module.enable(module, lua.table_from(config))

    # memory: the image's pages on first use, zero pages elsewhere
    def map(self, address):
        page = address & ~(PAGE - 1)
        self.uc.mem_map(page, PAGE)
        content = self.raw[:PAGE] if page == self.base else b''
        for va, offset, size in self.sections:
            if va <= page < va + size:
                content = self.raw[offset + page - va:offset + min(size, page - va + PAGE)]
        if content:
            self.uc.mem_write(page, bytes(content))

    def read(self, address, size):
        address = int(address) & MASK
        for page in range(address & ~(PAGE - 1), address + size, PAGE):
            try:
                self.uc.mem_read(page, 1)
            except UcError:
                self.map(page)
        return bytes(self.uc.mem_read(address, size))

    def poke(self, address, raw):
        self.read(address, len(raw))
        self.uc.mem_write(address, raw)

    def write_data(self, address, raw):
        if int(address) < HEAP:
            raise AssertionError('data write into the game image at %08X' % int(address))
        self.poke(int(address), raw)

    def file32(self, va):
        """A dword of the executable file, before any patch."""
        for start, offset, size in self.sections:
            if start <= va < start + size:
                return struct.unpack_from('<I', self.raw, offset + va - start)[0]
        raise AssertionError('%08X is not in the file' % va)

    def u16(self, a): return struct.unpack('<H', self.read(a, 2))[0]
    def u32(self, a): return struct.unpack('<I', self.read(a, 4))[0]
    def put8(self, a, v): self.poke(a, bytes([v & 0xFF]))
    def put16(self, a, v): self.poke(a, struct.pack('<H', v & 0xFFFF))
    def put32(self, a, v): self.poke(a, struct.pack('<I', v & MASK))

    def flatten(self, table):
        out = []

        def walk(t):
            for i in range(1, len(t) + 1):
                walk(t[i]) if lua_type(t[i]) == 'table' else out.append(int(t[i]) & 0xFF)
        walk(table)
        return bytes(out)

    def allocate(self, size):
        address = self.heap
        self.heap = (self.heap + size + 0x1F) & ~0xF
        self.poke(address, b'\0' * size)
        return address

    def place(self, code):
        address = self.allocate(len(code))
        self.poke(address, code)
        return address

    def assemble(self, script, values):
        address = self.allocate(0x400)
        source = 'use32\norg 0x%X\n' % address + ''.join(
            '%s = 0x%X\n' % (k, int(v) & MASK) for k, v in values.items()) + script
        handle, name = tempfile.mkstemp(suffix='.asm', dir=self.work)
        os.close(handle)
        asm = Path(name)
        asm.write_text(source, newline='\n')
        subprocess.run([str(POWERSHELL32), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(self.work / 'fasm.ps1'), '-asm', str(asm), '-dll', str(self.work / 'fasm.dll')],
                       check=True, capture_output=True)
        code = asm.with_suffix('.bin').read_bytes()
        assert len(code) <= 0x400
        self.poke(address, code)
        return address

    # code
    def scan(self, pattern, start=None, required=False, raw=False):
        """First match at or after `start` in the image: as loaded now, or in the file."""
        rx, start = regex(pattern), int(start) if start else 0
        for va, offset, size in self.sections:
            data = self.raw[offset:offset + size] if raw else self.read(va, size)
            found = rx.search(data, max(0, start - va))
            if found:
                return va + found.start()
        if required:
            raise LuaError('AOB could not be found: ' + pattern)
        return None

    def call(self, address, args):
        self.calls.append((address, args))
        handler = self.exposed.get(address)
        return handler(*args) if handler else 0

    def on_code(self, uc, address, size, _):
        fn = self.detours.get(address)
        if fn is not None:   # the detoured pad: run the Lua callback, then return
            fn(self.lua.table())
            esp = uc.reg_read(UC_X86_REG_ESP)
            uc.reg_write(UC_X86_REG_EIP, self.u32(esp))
            uc.reg_write(UC_X86_REG_ESP, esp + 4)

    def run(self, start, frame, **registers):
        """Run from `start` with `frame` on the stack (top first) until SENTINEL is reached."""
        esp = STACK_TOP - 4 * len(frame)
        for i, value in enumerate(frame):
            self.put32(esp + 4 * i, value)
        self.uc.reg_write(UC_X86_REG_ESP, esp)
        for name, value in registers.items():
            self.uc.reg_write(REG[name], value & MASK)
        self.uc.emu_start(start, SENTINEL, count=2_000_000)
        return {name: self.uc.reg_read(r) for name, r in REG.items()}


def check(exe, work):
    results = []
    for walls in (True, False):
        g = Game(exe, work, {'walls': True} if walls else {'buildings': True})
        find = lambda pattern: g.scan(pattern, required=True, raw=True)
        place_test = find('69 ED 90 04 00 00 66 83 BD ? ? ? ? 3E 0F 85 ? ? ? ? 8B 54 24 28')
        set_pos = find('53 8B 5C 24 0C 81 FB 8F 01 00 00 55 8B E9 0F 87')
        ai_units = find(AI_WALL_UNITS)
        ai_end = find('C7 05 ? ? ? ? 01 00 00 00 E8 ? ? ? ? 5F 5D 5B C2 10 00') + 15
        tms = g.file32(find('F7 04 9D ? ? ? ? 00 01 00 00') + 3) - 0x165160
        units = g.file32(place_test + 9) - 0x8E
        rows, valid = g.file32(set_pos + 0xC1), g.file32(set_pos + 0x32)
        unit = lambda i: units + i * 0x490
        queue = HEAP + 8          # the module's first allocation: allies flag, then the queue
        tile = 110 * 400 + 110
        for y in range(400):
            g.put32(rows + y * 12, y * 400)
        for y in range(100, 121):  # open, walkable ground in one area around the tile
            for x in range(100, 121):
                t = y * 400 + x
                g.put8(valid + t, 1)
                g.put8(tms + 0x38B2F0 + t, 0xFF)
                g.put16(tms + 0x363ED0 + 2 * t, 1)
                g.put8(tms + 0x29FA30 + t, 9)
        # unit 8: an enemy spearman standing on the tile, on the ground
        g.put16(unit(8) + 0x8C, 1); g.put16(unit(8) + 0x8E, 24); g.put16(unit(8) + 0x96, 3)
        g.put16(unit(8) + 0xC4, 110); g.put16(unit(8) + 0xC6, 110); g.put32(unit(8) + 0xD4, tile)
        g.put16(unit(8) + 0xF6, 0)
        g.put16(tms + 0x23D7E0 + 2 * tile, 8)

        def validate():
            """validateWallPlacementAtTile from the unit test to its return."""
            g.put32(tms + 0x55491C, 1)
            return g.run(ai_units, [0xD1, 0x51, 0xBE, 0xBB, SENTINEL, 2, 110, 110, 0x1A],
                         edi=tms, esi=tile, ecx=0x2222, edx=0x3333)

        label = '%s, walls %s' % (exe.name, 'on' if walls else 'off')
        assert not g.logs, g.logs
        if not walls:
            assert regex(AI_WALL_UNITS).fullmatch(g.read(ai_units, 24)), 'AI wall code patched with walls off'
            validate()
            assert g.u16(unit(8) + 0x8C) == 3, 'the game no longer removes the unit'
            results.append(label + ': AI wall code unchanged; the game removes the unit')
            continue
        assert g.read(ai_units, 1) == b'\xE9', 'AI wall code not redirected'
        g.put32(queue, 0)
        registers = validate()
        assert (g.u16(unit(8) + 0x8C), g.u32(queue), g.u32(queue + 4)) == (1, 1, tile), 'unit not kept'
        assert g.u32(tms + 0x55491C) == 0, 'the tile no longer passes as valid'
        assert [registers[r] for r in ('esp', 'ebx', 'ebp', 'esi', 'edi')] == \
            [STACK_TOP, 0xBB, 0xBE, 0x51, 0xD1], 'registers or stack not restored'
        g.put32(queue, 1024)
        validate()
        assert g.u16(unit(8) + 0x8C) == 3, 'full queue: the game should remove the unit'
        g.put16(unit(8) + 0x8C, 1)
        g.exposed[set_pos] = lambda this, u, x, y, h: (
            g.put16(unit(u) + 0xC4, x), g.put16(unit(u) + 0xC6, y), 0)[2]
        g.put32(queue, 1); g.put32(queue + 4, tile)
        g.put32(tms + 0x165160 + 4 * tile, 0x100)   # the tile is now a wall
        registers = g.run(ai_end, [0xD1, 0xBE, 0xBB, SENTINEL, 0, 0, 0, 0], eax=0x1111, esi=0x5151)
        moved = [args for address, args in g.calls if address == set_pos]
        assert moved == [[units - 0x614, 8, 110, 109, 9]], moved
        assert [registers[r] for r in ('eax', 'esi', 'ebx', 'ebp', 'edi', 'esp')] == \
            [0x1111, 0x5151, 0xBB, 0xBE, 0xD1, STACK_TOP], 'registers or stack not restored'
        assert g.u32(queue) == 0 and not [m for m in g.logs if 'failed' in m], g.logs
        results.append(label + ': unit kept and remembered, full queue left to the game, '
                       'unit moved next to the wall')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--framework', type=Path, required=True, help="UCP 3.0.7's ucp/code.zip")
    parser.add_argument('exes', type=Path, nargs='+')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        with zipfile.ZipFile(args.framework) as archive:
            (work / 'fasm.dll').write_bytes(archive.read('vendor/fasm/fasm.dll'))
        (work / 'fasm.ps1').write_text(FASM_PS1, encoding='utf-8')
        for exe in args.exes:
            for line in check(exe, work):
                print(line)


if __name__ == '__main__':
    main()
