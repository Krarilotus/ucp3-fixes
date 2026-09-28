"""Probe the native gatehouse patch on licensed SHC/Extreme executables.

Usage: python tests/check_gatehouse_capture.py <game.exe> [more-game.exe ...]
"""
import argparse
from pathlib import Path
import re

import pefile
from lupa.lua54 import LuaRuntime
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_ESP


MODULE = Path(__file__).resolve().parents[1] / 'gatehouse-capture-fix'
FRAMEWORK = Path(r'C:\Projects\UCP\UnofficialCrusaderPatch3\content\ucp\code\core.lua')
CAVE = 0x3000000


def check(path):
    pe = pefile.PE(str(path))
    base, image = pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image()
    lua = LuaRuntime(unpack_returned_tuples=True)
    core = lua.execute(FRAMEWORK.read_text(encoding='utf-8'))
    lua.globals().core = core
    lua.globals().utils = lua.table_from({'itob': core.itob})
    lua.globals().package.path = MODULE.as_posix() + '/?.lua'
    changes = {}

    def read(address, count):
        return bytes(changes.get(a, image[a-base] if 0 <= a-base < len(image) else 0)
                     for a in range(address, address + count))

    def scan(pattern, start=None, stop=None):
        regex = b''.join(b'.' if token == '?' else re.escape(bytes([int(token, 16)]))
                         for token in pattern.split())
        low = max(base, start or base) - base
        high = min(base + len(image), stop or base + len(image)) - base
        found = re.search(regex, image[low:high], re.DOTALL)
        return base + low + found.start() if found else None

    def aob(pattern):
        address = scan(pattern)
        if address is None: raise AssertionError('gatehouse signature absent')
        return address

    def write_code(address, code):
        compiled = core.compile(code, address)
        for offset, byte in enumerate(compiled.values()): changes[address + offset] = byte

    core.AOBScan = aob
    core.scanForAOB = scan
    core.readInteger = lambda address: int.from_bytes(read(address, 4), 'little')
    core.readByte = lambda address: read(address, 1)[0]
    core.readBytes = lambda address, count: lua.table_from(read(address, count))
    core.allocateCode = lambda count: CAVE
    core.writeCode = write_code

    install = lua.execute('return require("capture").prepare()')
    install()
    site = next(address for address in changes if base <= address < base + len(image))
    # Only the native gatehouse occupancy comparison is patched.
    assert read(site, 1) == b'\xe9'
    original = image[site-base:site-base+10]
    assert original[:3] == b'\x66\x83\xbe' and original[8] == 0x74
    selectable = int.from_bytes(original[3:7], 'little')
    skip = site + 10 + original[9]

    for dying, selectable_flag, expected in ((0, 1, site + 10),
                                             (1, 1, skip), (0, 0, skip)):
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        code_page = site & ~0xfff
        uc.mem_map(code_page, 0x1000)
        uc.mem_write(code_page, read(code_page, 0x1000))
        uc.mem_map(CAVE, 0x1000)
        uc.mem_write(CAVE, read(CAVE, 0x1000))
        data_page = selectable & ~0xfff
        uc.mem_map(data_page, 0x1000)
        uc.mem_write(selectable - 4, dying.to_bytes(2, 'little'))
        uc.mem_write(selectable, selectable_flag.to_bytes(2, 'little'))
        uc.mem_map(0x3200000, 0x1000)
        uc.reg_write(UC_X86_REG_ESI, 0)
        uc.reg_write(UC_X86_REG_ESP, 0x3200ff0)
        reached = []

        def stop(_, address, size, __):
            if address in (site + 10, skip):
                reached.append(address)
                uc.emu_stop()

        uc.hook_add(UC_HOOK_CODE, stop)
        uc.emu_start(site, skip + 1, count=12)
        assert reached == [expected], (path, dying, selectable_flag, reached)
    return f'{path.name}: one binding; live occupants count, dying and unselectable occupants do not'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executables', type=Path, nargs='+')
    for executable in parser.parse_args().executables:
        print(check(executable))
