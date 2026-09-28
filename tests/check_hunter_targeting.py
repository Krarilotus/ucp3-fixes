"""Check hunter patch bindings on licensed 1.41 executables.

Usage: python tests/check_hunter_targeting.py --framework <3.0.7/core.lua> <game.exe> [more-game.exe ...]
"""
import argparse
from pathlib import Path
import re

import pefile
from lupa.lua54 import LuaRuntime
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EDI,
                               UC_X86_REG_EFLAGS, UC_X86_REG_ESI, UC_X86_REG_ESP)


MODULE = Path(__file__).resolve().parents[1] / 'hunter-targeting-fix'
CAVE = 0x3000000


def check(path, framework):
    pe = pefile.PE(str(path))
    image, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    lua = LuaRuntime(unpack_returned_tuples=True)
    core = lua.execute(framework.read_text(encoding='utf-8'))
    lua.globals().utils = lua.table_from({'itob': core.itob})
    writes = {}
    byte_patches = []
    code_patches = []
    next_cave = [CAVE]

    def read(address, count):
        return bytes(writes.get(at, image[at-base] if 0 <= at-base < len(image) else 0)
                     for at in range(address, address + count))

    def scan(pattern, start=None, stop=None):
        regex = b''.join(
            b'.' if token == '?' else re.escape(bytes([int(token, 16)]))
            for token in pattern.split())
        low = max(base, start or base) - base
        high = min(base + len(image), stop or base + len(image)) - base
        match = re.search(regex, image[low:high], re.DOTALL)
        return base + low + match.start() if match else None

    def aob(pattern):
        address = scan(pattern)
        if address is None: raise AssertionError('hunter signature absent')
        return address

    def write_code(address, code):
        compiled = core.compile(code, address)
        for offset, byte in enumerate(compiled.values()):
            writes[address + offset] = byte

    def write_byte(address, byte):
        byte_patches.append(address)
        writes[address] = byte

    native_insert = core.insertCode

    def insert(address, size, code):
        code_patches.append((address, size))
        return native_insert(address, size, code)

    def allocate(count):
        address = next_cave[0]
        next_cave[0] += 0x1000
        return address

    core.AOBScan = aob
    core.scanForAOB = scan
    core.readByte = lambda address: read(address, 1)[0]
    core.readInteger = lambda address: int.from_bytes(read(address, 4), 'little')
    core.readBytes = lambda address, count: lua.table_from(read(address, count))
    core.writeCodeByte = write_byte
    core.writeCode = write_code
    core.allocateCode = allocate
    core.insertCode = insert
    lua.globals().core = core
    lua.globals().package.path = MODULE.as_posix() + '/?.lua'
    install = lua.execute('return require("hunting").prepare()')
    install()
    assert len(byte_patches) == 4 and len(code_patches) == 2
    selector, pass_limit, second_limit, movement = sorted(byte_patches)
    assert [image[address-base] for address in byte_patches] == [20, 20, 20, 5]
    assert [writes[address] for address in byte_patches] == [0, 0, 0, 1]
    assert selector < pass_limit < second_limit < movement
    sight, failed = (patch[0] for patch in code_patches)
    assert sight < pass_limit and movement < failed
    assert [size for _, size in code_patches] == [5, 6]
    assert read(sight, 1) == b'\xe9' and read(failed, 1) == b'\xe9'

    def run(site, cave, stops, eax=0, edi=0, zero=False, pass_number=0, path_done=0):
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        for page in {(site & ~0xfff), *(address & ~0xfff for address in stops)}:
            uc.mem_map(page, 0x1000)
            uc.mem_write(page, read(page, 0x1000))
        uc.mem_map(cave, 0x1000)
        uc.mem_write(cave, read(cave, 0x1000))
        uc.mem_map(0x3200000, 0x1000)
        stack = 0x3200800
        uc.mem_write(stack + 0x24, pass_number.to_bytes(4, 'little'))
        uc.reg_write(UC_X86_REG_ESP, stack)
        uc.reg_write(UC_X86_REG_EAX, eax)
        uc.reg_write(UC_X86_REG_EDI, edi)
        uc.reg_write(UC_X86_REG_ESI, 1)
        uc.reg_write(UC_X86_REG_EFLAGS, 0x246 if zero else 0x202)
        if site == failed and edi > 3 and zero:
            call = re.search(b'\xe8(.{4})', read(cave, 0x100), re.DOTALL)
            assert call is not None
            target = cave + call.start() + 5 + int.from_bytes(call.group(1), 'little', signed=True)
            target_page = target & ~0xfff
            uc.mem_map(target_page, 0x1000)
            uc.mem_write(target, b'\xb8' + path_done.to_bytes(4, 'little') + b'\xc2\x04\x00')
        reached = []

        def stop(_, address, size, __):
            if address in stops:
                reached.append(address)
                uc.emu_stop()

        uc.hook_add(UC_HOOK_CODE, stop)
        uc.emu_start(site, 0, count=40)
        assert len(reached) == 1
        return reached[0]

    skip = sight + 7 + image[sight-base+6]
    assert run(sight, CAVE, (sight+7, skip), eax=0x1b0) == skip
    assert run(sight, CAVE, (sight+7, skip), eax=0x1b0, pass_number=1) == sight+7
    assert run(sight, CAVE, (sight+7, skip), eax=100) == sight+7
    fallback = failed + 6 + int.from_bytes(image[failed-base+2:failed-base+6], 'little', signed=True)
    step = failed - 0xb1  # Reference-only check: the native walking return block.
    assert run(failed, CAVE+0x1000, (failed+6, fallback, step)) == failed+6
    assert run(failed, CAVE+0x1000, (failed+6, fallback, step), edi=2, zero=True) == fallback
    assert run(failed, CAVE+0x1000, (failed+6, fallback, step), edi=10, zero=True, path_done=1) == fallback
    assert run(failed, CAVE+0x1000, (failed+6, fallback, step), edi=10, zero=True) == step
    install()
    assert len(byte_patches) == 4 and len(code_patches) == 2
    return f'{path.name}: six bindings; sight and movement branches exercised'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--framework', type=Path, required=True)
    parser.add_argument('executables', type=Path, nargs='+')
    args = parser.parse_args()
    for executable in args.executables:
        print(check(executable, args.framework))
