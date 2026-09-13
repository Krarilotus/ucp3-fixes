"""Run the original tribe command and native path cleanup on licensed PE fixtures.

No callee stubs or live-process writes. This is instruction/ABI evidence, not
desktop, multiplayer or save/replay acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from lupa.lua54 import LuaError
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EIP
from crew_framework import CrewFramework

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--framework', type=Path, required=True)
parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
parser.add_argument('--report', type=Path)
args = parser.parse_args()
reports = []
for fixture in [f for manifest in args.fixtures for f in json.loads(manifest.read_text())]:
    path = Path(fixture.get('path', fixture.get('file')))
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == fixture['sha256']
    pe = pefile.PE(data=raw)
    mapped, base = pe.get_memory_mapped_image(), pe.OPTIONAL_HEADER.ImageBase
    h = CrewFramework(mapped, base, args.framework)
    prepare = h.lua.eval('require("siege-targeting").prepare')
    install = prepare()
    assert not h.patches and not h.allocations
    install()
    assert list(h.allocations.values()) == [27]
    patch_count = len(h.patches)
    install()
    assert len(h.patches) == patch_count
    site = h.patches[0][0]
    # Reference-only addresses: the fixture hash above pins their provenance.
    # Production uses the verified AOB/context/decoded-call bindings instead.
    extreme = 'extreme' in path.name.lower()
    command = 0x5280a0 if extreme else 0x527c80
    units = 0x145ca28 if extreme else 0x1387f38
    tribes, stride = (0x1f9afc0, 0x688) if extreme else (0x1667f78, 0x334)
    stop = 0x52f490 if extreme else 0x52f070
    assert mapped[command-base:command-base+3] == b'\x83\xec\x1c'
    assert struct.unpack_from('<I', mapped, command-base+9)[0] == stride
    assert struct.unpack_from('<I', mapped, site-base+2)[0] == units+0x614+0x3c5
    root = units+0x614
    cases = []
    for kind in (22, 39, 40, 41, 61, 77):
        for order in (4, 5, 31):
            for invalid_uid in (False, True) if order == 4 else (False,):
                pair = []
                for enabled in (False, True):
                    u = Uc(UC_ARCH_X86, UC_MODE_32)
                    u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
                    u.mem_write(base, mapped)
                    u.mem_map(0x5000000, 0x20000)
                    if enabled:
                        for address, payload in h.patches: u.mem_write(address, payload)
                    def put(address, value, size=4):
                        u.mem_write(address, value.to_bytes(size, 'little'))
                    a, b, group = root+0x490, root+2*0x490, tribes+stride
                    put(group+0x40, 2, 2); put(group+0x5c, 1, 2); put(group+0x60, 2, 2)
                    for record, owner, unit_kind, uid, x in ((a,1,kind,100,40),(b,2,22,200,44)):
                        for off,value,size in ((0x8c,2,2),(0x8e,unit_kind,2),(0x96,owner,2),
                                (0x98,uid,4),(0xb6,x*8,2),(0xb8,320,2),(0xc4,x,2),(0xc6,40,2),
                                (0x2c0,101,2),(0x362,20,2),(0x3b4,2,2),(0x3c8,100,4)):
                            put(record+off,value,size)
                    for off,value in ((0xfa,7),(0xfc,22),(0x2d2,4),(0x294,3)):
                        put(a+off,value,2)
                    put(a+0x39c,3,2)
                    sp, end = 0x5010000, 0x501f000
                    params = [1,order,2,201 if invalid_uid else 200,0] if order==4 else [1,order,44,40,0]
                    put(sp,end)
                    for i,value in enumerate(params): put(sp+4+i*4,value)
                    u.reg_write(UC_X86_REG_ESP,sp); u.reg_write(UC_X86_REG_ECX,tribes)
                    calls = []
                    u.hook_add(UC_HOOK_CODE,lambda uc,ip,size,data:calls.append(ip),begin=stop,end=stop)
                    u.emu_start(command,end,count=1000000)
                    assert u.reg_read(UC_X86_REG_EIP)==end
                    assert u.reg_read(UC_X86_REG_ESP)==sp+24, 'thiscall RET20 ABI'
                    record = bytes(u.mem_read(a,0x490))
                    cleared = all(record[o:o+2]==b'\0\0' for o in (0xfa,0xfc,0x2d2,0x294))
                    affected = order==4 and kind in (39,40) and not invalid_uid
                    assert cleared == (not invalid_uid and (not affected or enabled))
                    assert len(calls)==int(cleared), 'native cleanup exactly once'
                    pair.append(record)
                changed={i for i,(x,y) in enumerate(zip(*pair)) if x!=y}
                allowed={0xfa,0xfb,0xfc,0xfd,0x2d2,0x2d3,0x294,0x295}
                assert changed<=allowed
                assert bool(changed)==(order==4 and kind in (39,40) and not invalid_uid)
                cases.append(dict(kind=kind,order=order,invalid_uid=invalid_uid,changed=sorted(changed)))
    # Reject absent/occupied context, duplicates and a changed layout without writes.
    def rejected(memory, mutate_after=False):
        check=CrewFramework(memory,base,args.framework)
        try:
            apply=check.lua.eval('require("siege-targeting").prepare')()
            if mutate_after: check.memory[site-base]=0xe9
            apply()
        except LuaError:
            assert not check.patches and not check.allocations
            return
        raise AssertionError('Invalid command binding accepted')
    changed=bytearray(mapped); changed[site-base]=0xe9; rejected(changed)
    changed=bytearray(mapped); changed[site-base+2]^=4; rejected(changed)
    changed=bytearray(mapped); changed[site-base-80:site-base-18]=mapped[site-base:site-base+62]; rejected(changed)
    changed=bytearray(mapped); changed[stop-base+14]=0x90; rejected(changed)
    rejected(mapped,True)
    # All OFF is a true no-op, even without any supported executable context.
    check=CrewFramework(b'unsupported',base,args.framework)
    init=check.lua.execute((Path(__file__).resolve().parents[1]/'unit-behaviour-fixes/init.lua').read_text())
    config=check.lua.table_from(dict(crew_lifecycle=False,tunneler_response=False,siege_target_stop=False))
    init.enable(init,config)
    assert not check.patches and not check.allocations
    reports.append(dict(path=str(path),sha256=fixture['sha256'],code_bytes=27,cases=cases))
    print(f'{path.name}: {len(cases)} paired commands, ABI/cleanup/record preservation and binding rejection passed',flush=True)
if args.report: args.report.write_text(json.dumps(reports,indent=2)+'\n')
