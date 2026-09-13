"""Hash-pinned original-instruction research; no runtime binding or callee stubs.

Compare native spawned/assigned melee units and the next enemy-notice consumer.
The controlled ready/idle inputs are not a running-game reproduction.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
from itertools import product
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EIP

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--framework', type=Path, required=True)
parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
parser.add_argument('--baseline', action='store_true')
parser.add_argument('--threat', action='store_true', help='Initialize native map geometry and test nearby-enemy pursuit at each stance/range')
parser.add_argument('--report', type=Path)
parser.add_argument('--compare', type=Path, help='Compare complete unit records with a prior baseline report')
args = parser.parse_args()
assert not (args.threat and args.compare), 'Use separate threat assertions, not the no-enemy record comparator'
from crew_framework import CrewFramework
fixtures = [f for manifest in args.fixtures for f in json.loads(manifest.read_text())]
reports = []
for fixture in fixtures:
    path = Path(fixture.get('path', fixture.get('file')))
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
    pe = pefile.PE(data=raw)
    base, mapped = pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image()
    patches = []
    if not args.baseline:
        h = CrewFramework(mapped, base, args.framework)
        install = h.lua.eval('require("tunneler").prepare')()
        assert not h.patches
        install()
        patches = h.patches
        assert len(h.allocations) == 2 and sum(h.allocations.values()) == 40
    def unique(pattern):
        expression = b''.join(b'.' if t == '?' else re.escape(bytes([int(t, 16)])) for t in pattern.split())
        hits = list(re.finditer(expression, mapped, re.S))
        assert len(hits) == 1, (path, pattern, len(hits))
        return base + hits[0].start()
    def integer(a): return struct.unpack_from('<I', mapped, a - base)[0]
    dispatch = unique('0F BF 91 A2 06 00 00 8B 04 95 ? ? ? ? FF D0 A1 ? ? ? ? 69 C0 90 04 00 00')
    table, current = integer(dispatch + 10), integer(dispatch + 17)
    extreme = 'Extreme' in path.name
    units = 0x145ca28 if extreme else 0x1387f38
    players = 0x11eea38 if extreme else 0x115bdf8
    tribes, stride = (0x1f9afc0, 0x688) if extreme else (0x1667f78, 0x334)
    spawn = unique('53 8B D9 B9 01 00 00 00 57 8B F9 8D 83 30 0B 00 00 66 83 38 00 74 1B 81 FF')
    assign = unique('56 57 8B 7C 24 0C 8B C7 69 C0 90 04 00 00 0F BF 90 ? ? ? ? 8B F2 69 F6 F4 39 00 00 83 BE ? ? ? ? 00 74 23')
    notice = unique('83 EC 5C 8B 54 24 60 53 55 56 57 8B FA 69 FF 90 04 00 00 8B F1')
    # This consumer tests Unit+0x3FC before reading its group's stance. Trace
    # which original instructions run, without replacing any callees.
    gate = notice + 0x52
    assert mapped[gate-base:gate-base+8] == bytes.fromhex('66 39 9C 37 10 0A 00 00')
    states = ((5, 5), (5, 6), (5, 4), (5, 7), (5, 9), (27, 1), (27, 3))
    cases = product(states, (0, 1, 2), (16, 80, 240)) if args.threat else ((state, 2, None) for state in states)
    for (kind, state), stance, distance in cases:
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
        u.mem_write(base, mapped)
        u.mem_map(0x5000000, 0x20000)
        for address, payload in patches: u.mem_write(address, payload)
        scratch = 0x70000000
        u.mem_map(scratch, 0x400000 if args.threat else 0x20000)
        def put(a, v): u.mem_write(a, struct.pack('<i', v))
        def half(a, v): u.mem_write(a, struct.pack('<h', v))
        def get(a): return struct.unpack('<i', u.mem_read(a, 4))[0]
        def short(a): return struct.unpack('<h', u.mem_read(a, 2))[0]
        def call(fn, this, *arguments):
            sp = scratch + (0x200000 if args.threat else 0x10000)
            put(sp, scratch)
            for i, value in enumerate(arguments): put(sp + 4 + i * 4, value)
            u.reg_write(UC_X86_REG_ESP, sp)
            u.reg_write(UC_X86_REG_ECX, this)
            u.emu_start(fn, scratch, count=10000000 if args.threat else 1000000)
            assert u.reg_read(UC_X86_REG_EIP) == scratch
            assert u.reg_read(UC_X86_REG_ESP) == sp + 4 + 4 * len(arguments)
            return u.reg_read(UC_X86_REG_EAX)
        coordinate = 1600 if args.threat else 640
        if args.threat:
            # These complete original initializers populate diamond-map geometry;
            # zero-filled lookup arrays are not a valid pursuit fixture.
            assert mapped[notice+0x586-base] == 0xb9
            assert mapped[notice+0x5a2-base:notice+0x5a6-base] == bytes.fromhex('0f bf 04 6d')
            tilemap = integer(notice + 0x587)
            viewport = integer(notice + 0x5a6) - 0x271c0
            call(unique('53 55 56 57 B8 02 00 00 00 33 F6 8D 99 00 32 00 00 8D 51 08 8D 7E FF'), tilemap)
            call(unique('55 8B EC 83 E4 F8 B8 18 C4 09 00 E8 ? ? ? ? 53 55 56 57 8B E9 33 C0 33 F6'), viewport)
            call(unique('53 55 56 8B E9 57 33 F6 8D 9D 28 87 18 00 8D BD C0 00 00 00 B1 30 33 D2'), viewport)
        unit = call(spawn, units, 1, 1, coordinate, coordinate, 8, kind)
        assert unit == 1
        record = units + 0x614 + unit * 0x490
        put(players + 0x39f4 + 0x2300, 9)
        call(assign, scratch + 0x1000, unit, 20)
        group = short(record + 0x2d8)
        group_record = tribes + group * stride
        half(group_record + stride - 0x54, stance)  # Native stance offset: 0x2E0 / 0x634.
        half(record + 0x8c, 2)
        half(record + 0x2a4, 1)
        half(record + 0x2c0, state)
        put(current, unit)
        call(integer(table + kind * 4), units)
        if args.threat:
            enemy = call(spawn, units, 1, 2, coordinate + distance, coordinate, 8, 24)
            enemy_record = units + 0x614 + enemy * 0x490
            half(enemy_record + 0x8c, 2)
            half(enemy_record + 0x2a4, 1)
            # Controlled input: both units occupy the same navigable area; the
            # native per-player enemy list admits this matching live enemy UID.
            half(tilemap + 0x363ed0 + get(record + 0xd4) * 2, 1)
            half(tilemap + 0x363ed0 + get(enemy_record + 0xd4) * 2, 1)
            put(players + 0x39f4 + 0x2088, 1)
            half(players + 0x39f4 + 0xd00, enemy)
            uid_pattern = unique('3B 04 95 ? ? ? ? 0F 85 22 02 00 00 8B 84 37 98 09 00 00')
            put(integer(uid_pattern + 3) + (10000 if extreme else 2500) * 4, get(enemy_record + 0x98))
        flag = short(record + 0x3fc)
        handler_record = bytes(u.mem_read(record, 0x490))
        trace = []
        def on_code(uc, address, size, data):
            if notice <= address < notice + 0xe0: trace.append(hex(address - notice))
        u.hook_add(UC_HOOK_CODE, on_code)
        call(notice, units, unit)
        read_stance = '0xad' in trace  # Original MOVSX tribe stance at notice+0xAD.
        row = dict(path=str(path), kind=kind, state=state, role=short(record+0x42a),
                   flag=flag, readGroupStance=read_stance, noticeEntry=hex(notice), trace=trace,
                   stance=stance, distance=distance, responseTarget=short(record+0x346), action=short(record+0x2c0),
                   handlerRecord=handler_record.hex(), noticeRecord=bytes(u.mem_read(record, 0x490)).hex())
        reports.append(row)
        expected = 1 if (not args.baseline and state in (5, 6)) or kind == 27 else 0
        assert flag == expected and read_stance == bool(expected), row
        if args.threat:
            pursues = bool(expected and distance <= (40 if stance == 1 else 200 if stance == 2 else 0))
            assert row['responseTarget'] == (enemy if pursues else 0), row
            assert not pursues or row['action'] == 101, row
            after = bytes.fromhex(row['noticeRecord'])
            for start, end in ((0x8c,0xa0), (0x2d8,0x2ec), (0x3c8,0x3d0), (0x42a,0x42c)):
                assert after[start:end] == handler_record[start:end], (row, start, end)
        print(json.dumps({k:v for k,v in row.items() if k not in ('trace', 'handlerRecord', 'noticeRecord')}), flush=True)
if args.compare:
    baseline = json.loads(args.compare.read_text())
    assert len(baseline) == len(reports)
    for original, patched in zip(baseline, reports):
        assert all(original[k] == patched[k] for k in ('path', 'kind', 'state', 'role'))
        for name in ('handlerRecord', 'noticeRecord'):
            a, b = bytes.fromhex(original[name]), bytes.fromhex(patched[name])
            changes = {i for i, (x, y) in enumerate(zip(a, b)) if x != y}
            allowed = {0x3fc, 0x3fd}
            if name == 'noticeRecord' and patched['kind'] == 5 and patched['state'] in (5, 6):
                # The original no-enemy branch now performs its normal eight-tick
                # retry delay. This is the native consumer's intended effect.
                assert struct.unpack_from('<h', b, 0x3ac)[0] == -8
                allowed |= {0x3ac, 0x3ad}
            assert changes <= allowed, (patched['path'], patched['kind'], patched['state'], name, changes)
    print(f'{len(reports)} paired records preserve identity/health and working controls; only eligibility and native no-enemy retry differ')
if args.report: args.report.write_text(json.dumps(reports, indent=2) + '\n')
