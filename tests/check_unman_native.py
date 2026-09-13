"""Compare the complete original exit-equipment command with the UID guard.

Licensed fixtures are supplied by the caller. All native callees run; controlled
unit records exercise valid, stale and invalid crew references, not gameplay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EIP
from crew_framework import CrewFramework

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--framework', type=Path, required=True)
parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
parser.add_argument('--report', type=Path)
args = parser.parse_args()
reports = []
for fixture in [f for p in args.fixtures for f in json.loads(p.read_text())]:
    path = Path(fixture.get('path', fixture.get('file')))
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
    pe = pefile.PE(data=raw)
    base, mapped = pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image()
    pattern = re.compile(re.escape(bytes.fromhex('83 EC 1C 8B 44 24 20 69 C0')) + b'.{4}' +
                         re.escape(bytes.fromhex('53 8B 5C 24 30 55 8D 2C 08 33 D2')), re.S)
    hits = list(pattern.finditer(mapped))
    assert len(hits) == 1
    entry = base + hits[0].start()
    extreme = b'crusaderExtreme.cfg' in mapped
    # Hash-pinned test setup only; production derives the root from the owner.
    record = (0x145ca28 if extreme else 0x1387f38) + 0x614
    tribes = 0x1f9afc0 if extreme else 0x1667f78
    capacity = 10000 if extreme else 2500
    h = CrewFramework(mapped, base, args.framework)
    install = h.lua.eval('require("unman").prepare')()
    assert not h.patches and not h.allocations
    install()
    installed = len(h.patches)
    install()
    assert len(h.patches) == installed and len(h.allocations) == 1

    def execute(crew_ids, stale=False, invalid_engine=False, patched=False, repeat=False):
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
        u.mem_write(base, mapped)
        u.mem_map(0x5000000, 0x20000)
        if patched:
            for address, payload in h.patches:
                u.mem_write(address, payload)
        def put(address, value, fmt='<I'):
            u.mem_write(address, struct.pack(fmt, value))
        engine = record + 50 * 0x490
        for offset, value, fmt in ((0x8c,2,'<H'), (0x8e,39,'<H'), (0x96,1,'<H'),
                (0x98,777,'<I'), (0xc4,80,'<H'), (0xc6,80,'<H'), (0xd4,32080,'<I'),
                (0x3b4,len(crew_ids),'<H'), (0x3c8,10000,'<I')):
            put(engine + offset, value, fmt)
        initial = {}
        for index, crew_id in enumerate(crew_ids):
            put(engine + 0x314 + index * 2, crew_id, '<h')
            put(engine + 0x31c + index * 4, 1000 + max(0, crew_id))
            if not 0 < crew_id < capacity:
                continue
            crew = record + crew_id * 0x490
            reused = stale and index == len(crew_ids) - 1
            for offset, value, fmt in ((0x8c,2,'<H'), (0x8e,55 if reused else 30,'<H'),
                    (0x96,1,'<H'), (0x98,7654321 if reused else 1000+crew_id,'<I'),
                    (0x2c0,5,'<H'), (0x32f,2,'<B'), (0x39e,50,'<H'), (0xa0,777,'<I'),
                    (0x3c8,2853,'<I'), (0x3cc,5000,'<I')):
                put(crew + offset, value, fmt)
            initial[crew_id] = bytes(u.mem_read(crew, 0x490))
        writes = []
        def on_write(uc, access, address, size, value, data):
            writes.append((address, size, value))
        u.hook_add(UC_HOOK_MEM_WRITE, on_write)
        stack, sentinel = 0x5010000, 0x5000000
        def call():
            for index, value in enumerate((sentinel, 1, 17, 50, 778 if invalid_engine else 777, 0)):
                put(stack + index * 4, value)
            u.reg_write(UC_X86_REG_ESP, stack)
            u.reg_write(UC_X86_REG_ECX, tribes)
            u.emu_start(entry, sentinel, count=100000)
            assert u.reg_read(UC_X86_REG_EIP) == sentinel
            assert u.reg_read(UC_X86_REG_ESP) == stack + 24
        call()
        snapshot = bytes(u.mem_read(record, capacity * 0x490))
        if repeat:
            call()
            assert bytes(u.mem_read(record, capacity * 0x490)) == snapshot
        for crew_id, before in initial.items():
            after = snapshot[crew_id*0x490:(crew_id+1)*0x490]
            assert before[0x98:0x9c] == after[0x98:0x9c]
            assert before[0x3c8:0x3d0] == after[0x3c8:0x3d0]
            if invalid_engine or (patched and stale and crew_id == crew_ids[-1]):
                assert before == after
                assert not any(record+crew_id*0x490 <= a < record+(crew_id+1)*0x490 for a,s,v in writes)
            else:
                assert struct.unpack_from('<H', after, 0x2c0)[0] == 109
        if not invalid_engine:
            assert struct.unpack_from('<H', snapshot, 50*0x490+0x3b4)[0] == 0
        return snapshot, writes

    for crew_ids in ((300,), (300,1300), (300,1300,1400,1500)):
        baseline, _ = execute(crew_ids)
        candidate, _ = execute(crew_ids, patched=True, repeat=True)
        assert baseline == candidate, 'Valid full-pool state changed'
    execute((300,1300), stale=True)  # Demonstrate original stale-slot mutation.
    execute((300,1300), stale=True, patched=True, repeat=True)
    for bad in (0, -1, capacity, 32767):
        _, writes = execute((300,bad), patched=True, repeat=True)
        assert not any(record+bad*0x490 <= a < record+(bad+1)*0x490 for a,s,v in writes)
    baseline, _ = execute((300,1300), invalid_engine=True)
    candidate, _ = execute((300,1300), invalid_engine=True, patched=True)
    assert baseline == candidate
    report = dict(path=str(path), sha256=fixture['sha256'], passed=True,
                  allocationBytes=sum(h.allocations.values()), originalPatchBytes=7,
                  cases=['partial/full crews', 'UID reuse', 'empty/negative/pool bounds',
                         'invalid engine UID', 'repeat command', 'complete valid unit-pool equality'])
    reports.append(report)
    print(json.dumps(report), flush=True)
if args.report:
    args.report.write_text(json.dumps(reports, indent=2) + '\n')
