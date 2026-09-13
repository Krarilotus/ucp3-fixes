"""Execute original siege behavior handlers with controlled death-frame inputs.

User-supplied hash-pinned binaries only. With --baseline the original bug is
asserted; otherwise the actual module runs through supplied UCP core/cache code.
No substitute native callee bodies or claims of gameplay acceptance.
"""
import hashlib
import argparse
import json
from pathlib import Path
import re
import struct

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EBX, UC_X86_REG_EBP

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--framework', type=Path, required=True)
parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
parser.add_argument('--baseline', action='store_true')
parser.add_argument('--crew-mode', choices=('full', 'partial', 'reused-slot', 'already-attributed'), default='full')
parser.add_argument('--reset-death-action', action='store_true')
parser.add_argument('--report', type=Path)
args = parser.parse_args()
from crew_framework import CrewFramework
fixtures = [dict(path=f.get('path', f.get('file')), sha256=f['sha256'])
            for manifest in args.fixtures for f in json.loads(manifest.read_text())]
reports = []
for fixture in fixtures:
    raw = Path(fixture['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    mapped = pe.get_memory_mapped_image()
    source_patches = []
    if not args.baseline:
        harness = CrewFramework(mapped, base, args.framework)
        install = harness.prepare()
        install()
        source_patches = harness.patches
    pattern = re.compile(bytes.fromhex('0F BF 91 A2 06 00 00 8B 04 95') + b'.{4}'
                         + bytes.fromhex('FF D0 A1') + b'.{4}', re.S)
    hits = list(pattern.finditer(mapped))
    assert len(hits) == 1
    block = hits[0].group()
    table, current = struct.unpack_from('<I', block, 10)[0], struct.unpack_from('<I', block, 17)[0]
    advance_pattern = re.compile(b'\xa1.{4}' + bytes.fromhex('69 C0 90 04 00 00 01 9C 30 54 06 00 00 8B 0D')
                                 + b'.{4}' + bytes.fromhex('8D 84 30 54 06 00 00'), re.S)
    advance_hits = list(advance_pattern.finditer(mapped))
    assert len(advance_hits) == 1
    advance_entry = base + advance_hits[0].start()
    dispatch_end = base + hits[0].end()
    fire_prefix = bytes.fromhex('8B 44 24 04 53 33 DB 3B C3 7F 06 33 C0 5B C2 0C 00 69 C0 90 04 00 00 66 39 9C 08 B4 08 00 00')
    fire_hits = list(re.finditer(re.escape(fire_prefix), mapped))
    assert len(fire_hits) == 1
    fire_entry = base + fire_hits[0].start()
    # These identities/roots remain private reconstruction evidence.
    units = 0x145ca28 if 'Extreme' in fixture['path'] else 0x1387f38
    record = units + 0x614
    cases = []
    for kind in (39, 40, 41, 58, 59, 60, 61, 77):
        handler = struct.unpack_from('<I', mapped, table - base + kind * 4)[0]
        for cycle, complete_dispatch, advance_due, fire_health in (
                (0, False, False, None), (1, False, False, None),
                (0, True, False, None), (0, True, True, None),
                (0, False, False, 1), (0, False, False, 5000)):
            u = Uc(UC_ARCH_X86, UC_MODE_32)
            u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 0xfff) & ~0xfff)
            u.mem_write(base, mapped)
            u.mem_map(0x5000000, 0x2000)
            for address, payload in source_patches:
                u.mem_write(address, payload)
            def put(a, v, fmt='<I'):
                u.mem_write(a, struct.pack(fmt, v))
            def get(a, fmt='<I'):
                return struct.unpack(fmt, u.mem_read(a, struct.calcsize(fmt)))[0]
            engine_id = 50
            engine = record + engine_id * 0x490
            u.mem_write(engine, bytes(0x490))
            put(current, engine_id)
            put(engine + 0x8c, 2, '<H')
            put(engine + 0x8e, kind, '<H')
            put(engine + 0x96, 1, '<H')
            put(engine + 0x98, 777)
            put(engine + 0x2a0, 1, '<H')
            put(engine + 0x2b0, cycle)
            put(engine + 0x44, 0 if advance_due else 100)
            put(engine + 0x2c0, 111, '<H')
            if args.reset_death_action and complete_dispatch:
                put(engine + 0x2c0, 0, '<H')
            put(engine + 0x3b4, 1 if args.crew_mode == 'partial' else 2, '<H')
            put(engine + 0x3f0, int(args.crew_mode == 'already-attributed'), '<H')
            put(engine + 0x3cc, 10000)
            put(engine + 0x400, 2, '<H')
            if fire_health is not None:
                put(engine + 0x2a0, 0, '<H')
                put(engine + 0x2c0, 0, '<H')
                put(engine + 0x3c8, fire_health)
            for slot, crew_id in enumerate((300, 1300)):
                crew = record + crew_id * 0x490
                u.mem_write(crew, bytes(0x490))
                put(engine + 0x314 + slot * 2, crew_id, '<H')
                put(engine + 0x31c + slot * 4, 1000 + crew_id)
                put(crew + 0x8c, 2, '<H')
                put(crew + 0x8e, 30, '<H')
                put(crew + 0x96, 1, '<H')
                put(crew + 0x98, 1000 + crew_id)
                put(crew + 0x2c0, 5, '<H')
                put(crew + 0x32f, 2, '<B')
                put(crew + 0x3c8, 2853)
                put(crew + 0x3cc, 5000)
            if args.crew_mode == 'reused-slot':
                put(record + 1300 * 0x490 + 0x98, 7654321)
                put(record + 1300 * 0x490 + 0x8e, 55, '<H')
            crew_state_writes = []
            crew_states = {record + i * 0x490 + 0x8c for i in (300, 1300)}
            def record_crew_write(uc, access, address, size, value, data):
                if address in crew_states:
                    crew_state_writes.append((address, size, value))
            u.hook_add(UC_HOOK_MEM_WRITE, record_crew_write)
            stack, sentinel = 0x5000800, 0x5001000
            put(stack, sentinel)
            u.reg_write(UC_X86_REG_ESP, stack)
            u.reg_write(UC_X86_REG_ECX, engine - 0x614)
            if fire_health is not None:
                put(stack + 4, engine_id)
                put(stack + 8, 2)
                put(stack + 12, 0)
                u.reg_write(UC_X86_REG_ECX, units)
                u.emu_start(fire_entry, sentinel, count=10000)
                assert u.reg_read(UC_X86_REG_ESP) == stack + 16
                if not args.baseline and fire_health == 1:
                    assert get(engine + 0x8c, '<H') == 2
                    assert get(engine + 0x2a0, '<H') == 1
                    assert get(engine + 0x2c0, '<H') == 114
                    u.reg_write(UC_X86_REG_ESP, stack)
                    u.reg_write(UC_X86_REG_ESI, units)
                    u.reg_write(UC_X86_REG_EBX, 1)
                    u.reg_write(UC_X86_REG_EBP, 0)
                    u.emu_start(advance_entry, dispatch_end, count=10000)
            elif complete_dispatch:
                u.reg_write(UC_X86_REG_ESI, units)
                u.reg_write(UC_X86_REG_EBX, 1)
                u.reg_write(UC_X86_REG_EBP, 0)
                u.emu_start(advance_entry, dispatch_end, count=10000)
                assert u.reg_read(UC_X86_REG_ESP) == stack
            else:
                u.emu_start(handler, sentinel, count=10000)
                assert u.reg_read(UC_X86_REG_ESP) == stack + 4
            states = [get(record + i * 0x490 + 0x8c, '<H') for i in (300, 1300)]
            expected_removed = fire_health is None and cycle == 0 and (not args.baseline or not (complete_dispatch and advance_due))
            expected_removed |= not args.baseline and fire_health == 1
            if args.reset_death_action and complete_dispatch:
                expected_removed = True
            if args.crew_mode == 'already-attributed':
                expected_removed = False
            expected_states = [3, 3] if expected_removed else [2, 2]
            if args.crew_mode in ('partial', 'reused-slot'):
                expected_states[1] = 2
            assert states == expected_states, (kind, cycle, complete_dispatch, advance_due, states)
            first_writes = len(crew_state_writes)
            if complete_dispatch or (not args.baseline and fire_health == 1):
                # A second real update must not run casualty/crew cleanup again.
                u.reg_write(UC_X86_REG_ESP, stack)
                u.reg_write(UC_X86_REG_ESI, units)
                u.reg_write(UC_X86_REG_EBX, 1)
                u.reg_write(UC_X86_REG_EBP, 0)
                u.emu_start(advance_entry, dispatch_end, count=10000)
                assert len(crew_state_writes) == first_writes
            for crew_id in (300, 1300):
                crew = record + crew_id * 0x490
                expected_uid = 7654321 if args.crew_mode == 'reused-slot' and crew_id == 1300 else 1000 + crew_id
                assert get(crew + 0x98) == expected_uid
                assert get(crew + 0x3c8) == 2853
            cases.append(dict(type=kind, handler=hex(handler), initialAnimationCycle=cycle,
                              completeNativeDispatch=complete_dispatch, animationAdvanceDue=advance_due,
                              fireInitialHealth=fire_health,
                              engineLogicalState=get(engine + 0x8c, '<H'),
                              engineDying=get(engine + 0x2a0, '<H'),
                              engineRequestedType=get(engine + 0x2ca, '<H'),
                              crewLogicalStates=states,
                              crewStateWrites=len(crew_state_writes),
                              resultingAnimationCycle=get(engine + 0x2b0)))
    reports.append(dict(path=fixture['path'], sha256=fixture['sha256'], cases=cases))
report = dict(baseline=args.baseline, crewMode=args.crew_mode, genericDeathReset=args.reset_death_action, fixtures=reports,
              limitation='Actual framework-emitted correction and original native dispatch/handlers; synthetic state, no callee stubs. This does not replace gameplay acceptance.')
if args.report:
    args.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(fixtures=len(reports), cases=sum(len(r['cases']) for r in reports),
                      baseline=args.baseline, crewMode=args.crew_mode, genericDeathReset=args.reset_death_action)))
