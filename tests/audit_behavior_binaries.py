"""Read-only signature, pointer and displaced-instruction audit for behavior hooks.

Usage: python tests/audit_behavior_binaries.py /path/to/executable [...]
This does not start or modify the game. It cannot validate gameplay or live hooks.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile
from test_modules import AIV, ModuleHarness
from test_behavior import enable_require


def audit(path):
    raw = path.read_bytes()
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    memory = pe.get_memory_mapped_image()
    h = ModuleHarness(AIV, memory, base)
    enable_require(h.lua)
    game_module = h.lua.execute('return (require("behavior.game"))')
    matches = {}
    def scan(pattern, *_):
        regex = b''.join(b'.' if x == '?' else re.escape(bytes([int(x, 16)])) for x in pattern.split())
        found = list(re.finditer(regex, memory, re.DOTALL))
        assert len(found) == 1, (pattern, 'matches', len(found))
        offset = found[0].start()
        assert any(s.VirtualAddress <= offset < s.VirtualAddress + s.Misc_VirtualSize
                   and s.Characteristics & 0x20000000 for s in pe.sections)
        return base + offset
    h.lua.globals().scan = scan
    h.lua.execute('core.AOBScan = function(pattern) return scan(pattern) end')
    pointers = []
    def read(address):
        offset = address - base
        assert 0 <= offset <= len(memory) - 4
        value = int.from_bytes(memory[offset:offset+4], 'little')
        assert value in (0x334, 0x688) or base <= value < base + pe.OPTIONAL_HEADER.SizeOfImage, (hex(address), hex(value))
        pointers.append({'instruction': hex(address), 'pointer': hex(value)})
        return value
    h.lua.globals().core.readInteger = read
    game = game_module.resolve()
    disassembler = Cs(CS_ARCH_X86, CS_MODE_32)
    sizes = {'initial': 7, 'mapper': 10, 'movement': 7, 'groupLimit': 9, 'patrolLimit': 8}
    for name, address in sorted(game.sites.items()):
        record = {'address': hex(address)}
        if name in sizes:
            size = sizes[name]
            instructions = list(disassembler.disasm(memory[address-base:address-base+size], address))
            assert sum(i.size for i in instructions) == size, (name, 'partial instruction')
            assert all(not i.mnemonic.startswith(('j', 'call', 'loop')) for i in instructions), (name, 'relative code relocation')
            record['displaced'] = [i.mnemonic + ' ' + i.op_str for i in instructions]
        matches[name] = record
    # The two selected initial-role destinations must still call native routines.
    initial = game.sites.initial - base
    for offset in (109, 119):
        assert memory[initial+offset:initial+offset+4] == bytes.fromhex('57 8B CB E8')
    assert path.read_bytes() == raw
    return dict(executable=path.name, sha256=hashlib.sha256(raw).hexdigest(), sites=matches, pointers=pointers)


if __name__ == '__main__':
    if len(sys.argv) < 2: raise SystemExit(__doc__)
    print(json.dumps([audit(Path(p)) for p in sys.argv[1:]], indent=2))
