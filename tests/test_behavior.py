"""Policy, AIC integration, register ABI and initial-assignment trampoline checks."""
from pathlib import Path
import re
import struct
import unittest
import yaml

from lupa.lua54 import lua_type
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EFLAGS, UC_X86_REG_ESP, UC_X86_REG_ESI, UC_X86_REG_EBX, UC_X86_REG_EBP

from test_modules import ROOT, BASE, AIV, FIXTURES, ModuleHarness, LuaError


def enable_require(lua):
    lua.globals().package.path = (ROOT / AIV).as_posix() + '/?.lua;' + (ROOT / AIV).as_posix() + '/?/init.lua'


class BehaviorHarness(ModuleHarness):
    def __init__(self):
        super().__init__(AIV, FIXTURES[AIV] + bytes(0x100000 - len(FIXTURES[AIV])))
        enable_require(self.lua)
        self.patterns = self.lua.execute('return (require("behavior.game"))').patterns
        self.sites = {}
        for index, (name, pattern) in enumerate(sorted(self.patterns.items())):
            address = BASE + 0x1000 + index * 0x100
            self.sites[name] = address
            self.put(address, bytes(0xCC if x == '?' else int(x, 16) for x in pattern.split()))
        self.pointers = {
            'unitType': 0x120000, 'unitOwner': 0x120008, 'aiType': 0x140000,
            'unitLimit': 0x1F0000, 'slotCounts': 0x140D8C, 'rowToTribe': 0x110000,
            'tribeIDs': 0x140E0C, 'tribeOwner': 0x170004,
        }
        for site, offset, pointer in (
            ('mapper', 13, 'unitType'), ('mapper', 24, 'unitOwner'),
            ('playerType', 11, 'aiType'), ('unitLimit', 11, 'unitLimit'),
            ('slotCounts', 3, 'slotCounts'), ('groupLimit', 5, 'rowToTribe'),
            ('tribeIDs', 11, 'tribeIDs'), ('movement', 17, 'tribeOwner'),
        ):
            self.i32(self.sites[site] + offset, self.pointers[pointer])
        self.i32(self.sites['movement'] + 11, 0x334)
        self.i32(self.pointers['unitLimit'], 100)
        self.i32(self.pointers['aiType'] + 0x39F4, 2)  # raw player type Rat=2 -> AIC 1
        self.i32(self.pointers['aiType'] + 2 * 0x39F4, 17)  # Abbot -> AIC 16
        self.i32(self.pointers['aiType'] + 3 * 0x39F4, 1)  # Human -> no AIC
        for row in range(20): self.i32(self.pointers['rowToTribe'] + row * 4, row * 10)
        self.callbacks, self.hooks, self.native_calls, self.aic = {}, {}, [], {}
        self.next_code = 0x1E0000
        self.lua.globals().core.readInteger = lambda a: int.from_bytes(self.get(a, 4), 'little', signed=True)
        self.lua.globals().core.readSmallInteger = lambda a: int.from_bytes(self.get(a, 2), 'little', signed=True)
        self.lua.globals().core.allocateCode = self.allocate
        self.lua.globals().core.detourCode = lambda cb, a, n: self.callbacks.update({a: (cb, n)})
        self.lua.globals().core.hookCode = self.hook
        self.lua.globals().core.insertCode = self.insert
        self.lua.globals().register_aic = lambda key, setter, reset: self.aic.update({key: (setter, reset)})
        self.lua.execute('''
          modules = {aicloader = {setAdditionalAICValue = function(self, key, setter, reset)
            register_aic(key, setter, reset)
          end}}
          WARNING = 1
          core.relTo = function(dst, offset)
            return function(address)
              local value = (dst - address + offset) & 0xFFFFFFFF
              return {value & 255, (value >> 8) & 255, (value >> 16) & 255, (value >> 24) & 255}
            end
          end
        ''')

    def get(self, address, size):
        offset = address - self.base
        assert 0 <= offset <= len(self.memory) - size
        return self.memory[offset:offset + size]

    def put(self, address, data):
        offset = address - self.base
        assert 0 <= offset <= len(self.memory) - len(data)
        self.memory[offset:offset + len(data)] = data

    def i32(self, address, value): self.put(address, struct.pack('<I', value))
    def i16(self, address, value): self.put(address, struct.pack('<H', value))

    def scan(self, pattern, extra_arguments):
        self.scans.append((pattern, extra_arguments))
        regex = b''.join(b'.' if x == '?' else re.escape(bytes([int(x, 16)])) for x in pattern.split())
        result = re.search(regex, self.memory, re.DOTALL)
        return self.base + result.start() if result else None

    def compile(self, code, address):
        result = bytearray()
        def add(item):
            if lua_type(item) == 'function': add(item(address + len(result)))
            elif lua_type(item) == 'table':
                for value in item.values(): add(value)
            else: result.append(int(item))
        add(code)
        return bytes(result)

    def allocate(self, code):
        address = self.next_code
        self.next_code += 256
        self.put(address, self.compile(code, address))
        return address

    def insert(self, site, size, code, return_to, original):
        self.assert_original = original
        address = self.next_code
        data = self.compile(code, address) + bytes(self.get(site, size))
        data += b'\xE9' + struct.pack('<i', (return_to or site + size) - (address + len(data) + 5))
        self.put(address, data)
        self.inserted = (address, data)
        self.next_code += 256
        return address

    def hook(self, cb, address, argc, convention, size):
        self.hooks[address] = (cb, argc, convention, size)
        def original(*args):
            self.native_calls.append((address, args))
            return 12345
        return original

    def install(self, **config):
        self.enable({'behavior': self.lua.table_from({'enabled': True, **config}, recursive=True)})
    def set_aic(self, ai, key, value): self.aic[key][0](ai, value)
    def callback(self, site, **registers):
        return self.callbacks[self.sites[site]][0](self.lua.table_from(registers))


class BehaviorTests(unittest.TestCase):
    def setUp(self): self.h = BehaviorHarness()

    def test_all_sites_preflight_before_any_writes(self):
        self.h.put(self.h.sites['initial'], b'\x90')
        with self.assertRaisesRegex(LuaError, 'cannot resolve behavior hook initial'):
            self.h.install()
        self.assertFalse(self.h.writes or self.h.callbacks or self.h.hooks or self.h.aic)

    def test_registration_getter_validation_and_per_ai_reset(self):
        h = self.h
        h.install()
        self.assertEqual(len(h.aic), 32)
        key = 'AIVTroops_InitialRole_Slave'
        self.assertIsNone(h.aic[key][0](1, None))
        h.set_aic(1, key, 'dig')
        self.assertEqual(h.aic[key][0](1, None), 'dig')
        self.assertIsNone(h.aic[key][0](16, None))
        for invalid in (-1, 0, 1, 2, 3, -2, 0.5, True, '2', 'native', 'inherit', 'Dig', 'hold', float('nan')):
            h.set_aic(1, key, invalid)
            self.assertEqual(h.aic[key][0](1, None), 'dig')
        h.aic[key][1](1)
        self.assertIsNone(h.aic[key][0](1, None))
        for key in ('AIVTroops_InitialRole_Swordsman', 'AIVTroops_InitialRole'):
            h.set_aic(1, key, 'dig')
            self.assertIsNone(h.aic[key][0](1, None))

    def test_each_named_field_reaches_expected_role_or_movement(self):
        h = self.h
        h.install()
        policy = h.lua.execute('return require("behavior.policy").new()')
        troops = h.lua.execute('return require("behavior.policy").troops')
        for key, (handler, reset) in h.aic.items():
            role = key.startswith('AIVTroops_InitialRole')
            troop = next((t for t in troops.values() if key.endswith('_' + t.name)), None)
            allowed = {'defend': 1} if role else {'hold': 1, 'patrol': 2}
            if role and troop and troop.digs:
                allowed['dig'] = 2
            for value, expected in allowed.items():
                with self.subTest(key=key, value=value):
                    handler(16, value)
                    self.assertEqual(handler(16, None), value)
                    self.assertIsNone(handler(1, None))
                    self.assertTrue(policy.set(policy, 16, key, value))
                    self.assertEqual(policy.get(policy, 16, 'InitialRole' if role else 'Movement', troop.row if troop else 13), expected)
                    policy.reset(policy, 16, key)
                    reset(16)
                    self.assertIsNone(handler(16, None))

    def test_ai_numbering_matches_aicloader_not_raw_player_data(self):
        game = self.h.lua.execute('return require("behavior.game").resolve()')
        self.assertEqual([game.ai(i) for i in (0, 1, 2, 3, 9)], [0, 1, 16, 0, 0])
        this = 0x1D0000
        self.h.i32(this + 16 * 0x2A4 + 0x114, 4)
        self.assertEqual(game.patrolGroups(this, 16), 4)

    def test_initial_digger_is_capability_checked_and_ai_specific(self):
        h = self.h
        h.install()
        h.set_aic(1, 'AIVTroops_InitialRole', 'defend')
        h.set_aic(1, 'AIVTroops_InitialRole_Slave', 'dig')
        gate = h.callbacks[0x1E0000][0]
        unit = 0x120000
        h.i16(unit, 71)
        h.i16(unit + 0x2E0, 1)
        def role(ai): return gate(h.lua.table_from({'EBP': ai, 'ESI': unit, 'EAX': 99})).EAX
        self.assertEqual(role(1), 2)
        self.assertEqual(role(16), 0)
        h.i16(unit + 0x2E0, 0)
        self.assertEqual(role(1), 1)
        h.i16(unit, 27)  # swordsman stays a defender, even with a modified runtime flag
        h.i16(unit + 0x2E0, 1)
        self.assertEqual(role(1), 1)

    def test_exact_native_digging_whitelist(self):
        policy_module = self.h.lua.execute('return (require("behavior.policy"))')
        actual = {t.unit for t in policy_module.troops.values() if t.digs}
        self.assertEqual(actual, {22, 24, 25, 26, 30, 71})

    def test_position_fix_preserves_conditional_pikeman_digging(self):
        # Execute the original assignment instructions, including the fallback
        # from our trampoline. Loading row 9 must not force its diggers to defend.
        for mode in ('base', 'unconfigured', 'hold', 'defend', 'dig'):
            h = BehaviorHarness()
            original = bytes(h.get(h.sites['initial'], 126))
            if mode == 'base':
                h.enable()
                self.assertEqual(bytes(h.get(h.sites['initial'], 126)), original)
                start = h.sites['initial']
            else:
                defaults = {'Movement_Pikeman': 'hold'} if mode == 'hold' else {}
                h.install(defaults=defaults)
                if mode in ('defend', 'dig'):
                    h.set_aic(1, 'AIVTroops_InitialRole_Pikeman', mode)
                start = h.inserted[0]
            for ai in (1, 16):
                for digging_max in (0, 20):
                    for can_dig in (0, 1):
                        with self.subTest(mode=mode, ai=ai, digging_max=digging_max, can_dig=can_dig):
                            unit, aic = 0x120000, 0x170000
                            h.i16(unit, 25)
                            h.i16(unit + 0x2E0, can_dig)
                            h.i32(aic + ai * 0x2A4 + 0x15C, digging_max)
                            if mode != 'base':
                                role = h.callbacks[0x1E0000][0](h.lua.table_from({'EBP': ai, 'ESI': unit})).EAX
                                h.put(0x1E0000, b'\xB8' + struct.pack('<I', role) + b'\xC3')
                            cpu = Uc(UC_ARCH_X86, UC_MODE_32)
                            cpu.mem_map(BASE, 0x100000)
                            cpu.mem_write(BASE, bytes(h.memory))
                            for register, value in ((UC_X86_REG_ESI, unit), (UC_X86_REG_EBX, aic),
                                                    (UC_X86_REG_EBP, ai), (UC_X86_REG_ESP, 0x1C0000)):
                                cpu.reg_write(register, value)
                            targets = {h.sites['initial'] + 109: 'dig', h.sites['initial'] + 119: 'defend'}
                            reached = []
                            def stop_at_assignment(cpu, address, size, _):
                                if address in targets:
                                    reached.append(targets[address])
                                    cpu.emu_stop()
                            cpu.hook_add(UC_HOOK_CODE, stop_at_assignment)
                            cpu.emu_start(start, h.sites['initial'] + 126, count=70)
                            expected = 'dig' if digging_max and can_dig else 'defend'
                            if ai == 1 and mode in ('defend', 'dig'):
                                expected = 'dig' if mode == 'dig' and can_dig else 'defend'
                            self.assertEqual(reached, [expected])

    def test_menu_defaults_aic_precedence_reset_and_opt_out(self):
        for overrides in (True, False):
            p = self.h.lua.execute('return (require("behavior.policy"))').new(
                self.h.lua.table_from({'aic_overrides': overrides, 'defaults': {
                    'InitialRole': 'defend', 'InitialRole_Slave': 'dig',
                    'Movement': 'hold', 'Movement_Spearman': 'patrol',
                }}, recursive=True))
            self.assertEqual(p.get(p, 1, 'Movement', 8), 2)
            self.assertEqual(p.get(p, 16, 'InitialRole', 13), 2)
            p.set(p, 1, 'AIVTroops_Movement', 'hold')
            self.assertEqual(p.get(p, 1, 'Movement', 8), 1 if overrides else 2)
            p.set(p, 1, 'AIVTroops_Movement_Spearman', 'hold')
            self.assertEqual(p.get(p, 1, 'Movement', 8), 1 if overrides else 2)
            self.assertEqual(p.get(p, 16, 'Movement', 8), 2)
            p.reset(p, 1, 'AIVTroops_Movement_Spearman')
            p.reset(p, 1, 'AIVTroops_Movement')
            self.assertEqual(p.get(p, 1, 'Movement', 8), 2)
            self.assertIsNone(p.raw(p, 1, 'AIVTroops_Movement_Spearman'))

    def test_menu_only_configuration_reaches_hooks_without_any_aic_file(self):
        h = self.h
        h.install(aic_overrides=False, defaults={'InitialRole': 'defend', 'Movement_Slave': 'hold'})
        h.set_aic(1, 'AIVTroops_InitialRole_Slave', 'dig')
        h.i16(0x120000, 71)
        h.i16(0x120000 + 0x2E0, 1)
        gate = h.callbacks[0x1E0000][0]
        for ai in (1, 16):
            self.assertEqual(gate(h.lua.table_from({'EBP': ai, 'ESI': 0x120000})).EAX, 1)

    def test_invalid_menu_value_fails_before_writes_or_hooks(self):
        for defaults in ({'InitialRole_Swordsman': 'dig'}, {'Movement': 'typo'}):
            with self.assertRaisesRegex(LuaError, 'invalid customization'):
                self.h.install(defaults=defaults)
            self.assertFalse(self.h.writes or self.h.hooks or self.h.callbacks)

    def test_menu_choices_cover_runtime_fields_and_only_capable_diggers(self):
        options = yaml.safe_load((ROOT / AIV / 'options.yml').read_text(encoding='utf-8'))
        def choices(nodes):
            for node in nodes:
                if node['display'] == 'Choice': yield node
                yield from choices(node.get('children', []))
        menus = list(choices(options['options']))
        policy = self.h.lua.execute('return (require("behavior.policy"))')
        self.assertEqual({'AIVTroops_' + n['url'].split('.')[-1] for n in menus},
                         set(policy.fields.keys()) - {'AIVTroops_InitialRole', 'AIVTroops_Movement'})
        self.assertEqual(len(menus), 30)
        self.assertTrue(all(n['contents']['value'] == 'native' and 'inheritFrom' not in n for n in menus))
        for menu in menus:
            suffix = menu['url'].split('.')[-1]
            for choice in menu['contents']['choices']:
                config = self.h.lua.table_from({'defaults': {suffix: choice['name']}}, recursive=True)
                policy.new(config)  # Every exposed value is accepted by the real policy.
        diggers = {n['url'].split('.')[-1] for n in menus if any(c['name'] == 'dig' for c in n['contents']['choices'])}
        self.assertEqual(diggers, {'InitialRole_' + t.name for t in policy.troops.values() if t.digs})

    def test_global_fallback_and_per_troop_override(self):
        p = self.h.lua.execute('return require("behavior.policy").new()')
        p.set(p, 1, 'AIVTroops_Movement', 'hold')
        p.set(p, 1, 'AIVTroops_Movement_Spearman', 'patrol')
        self.assertEqual(p.get(p, 1, 'Movement', 8), 2)
        self.assertEqual(p.get(p, 1, 'Movement', 11), 1)
        self.assertEqual(p.get(p, 16, 'Movement', 8), 0)
        p.reset(p, 1, 'AIVTroops_Movement_Spearman')
        self.assertEqual(p.get(p, 1, 'Movement', 8), 1)

    def test_held_patrol_rows_have_capacity_even_with_zero_patrol_groups(self):
        h = self.h
        h.install()
        h.set_aic(1, 'AIVTroops_Movement_Spearman', 'hold')
        h.i32(h.pointers['slotCounts'] + 0x39F4 + 8 * 4, 5)
        r = h.callback('groupLimit', EBP=1, EAX=8, EBX=0, EDX=0)
        self.assertEqual(r.EBX, 5)
        h.i32(0x110100, 8)
        r = h.callback('patrolLimit', EBP=1, EBX=0x110100, ECX=5, EAX=0)
        self.assertEqual(r.EAX, 5)

    def test_slot_distribution_uses_patrol_groups_and_existing_rally_counter(self):
        p = self.h.lua.execute('return (require("behavior.policy"))')
        self.assertEqual([p.slotIndex(2, i, 5, 2, 0) for i in range(2)], [0, 2])
        self.assertEqual([p.slotIndex(2, i, 5, 2, 4) for i in range(2)], [4, 1])
        self.assertEqual(p.slotIndex(1, 2, 5, 2, 99), 2)
        self.assertEqual(p.slotIndex(2, 0, 5, 0, 99), 0)
        self.assertIsNone(p.slotIndex(2, 0, 0, 2, 99))
        self.assertEqual(p.groupCount(2, 5, 50), 5)

    def test_slot_mapping_prevents_ranged_troops_sharing_configured_slave_row(self):
        h = self.h
        h.install()
        h.set_aic(1, 'AIVTroops_Movement_Slave', 'hold')
        h.i16(h.pointers['unitType'] + 0x490, 22)
        h.i16(h.pointers['unitOwner'] + 0x490, 1)
        mapper, argc, convention, size = h.hooks[h.sites['mapper']]
        self.assertEqual((argc, convention, size), (3, 1, 10))
        self.assertEqual(mapper(0x1D0000, 1, 1), 6)
        h.i16(h.pointers['unitOwner'] + 0x490, 2)
        self.assertEqual(mapper(0x1D0000, 1, 1), 12345)  # Abbot remains native

    def test_movement_wrapper_preserves_native_arguments_and_validates_uid(self):
        h = self.h
        h.install()
        h.set_aic(1, 'AIVTroops_Movement_Swordsman', 'patrol')
        tribe, row, ordinal, this = 1, 11, 1, 0x1D0000
        h.i32(h.pointers['tribeOwner'] + 0x334, 1)
        h.i32(h.pointers['tribeOwner'] + 0x334 + 8, 42)
        h.i16(h.pointers['tribeIDs'] + 0x39F4 + (row * 10 + ordinal) * 2, tribe)
        uid_addr = h.pointers['tribeIDs'] + 0x190 + 0x39F4 + (row * 10 + ordinal) * 4
        h.i32(uid_addr, 42)
        h.i32(h.pointers['slotCounts'] + 0x39F4 + row * 4, 5)
        h.i32(h.pointers['tribeIDs'] - 0x5B8 + 0x39F4, 4)
        h.i32(this + 0x2A4 + 0x114, 2)
        move, argc, convention, size = h.hooks[h.sites['movement']]
        self.assertEqual((argc, convention, size), (4, 1, 7))
        move(this, tribe, row, 0)
        self.assertEqual(h.native_calls[-1][1], (this, tribe, row, 1))
        h.i32(uid_addr, 43)  # stale ID: do not reinterpret the caller's slot
        move(this, tribe, row, 3)
        self.assertEqual(h.native_calls[-1][1], (this, tribe, row, 3))

    def test_extreme_tribe_stride_is_decoded_from_executable(self):
        h = self.h
        h.i32(h.sites['movement'] + 11, 0x688)
        h.install(defaults={'Movement': 'hold'})
        h.i32(h.pointers['tribeOwner'] + 0x688, 1)
        h.i32(h.pointers['tribeOwner'] + 0x688 + 8, 42)
        h.i16(h.pointers['tribeIDs'] + 0x39F4 + 111 * 2, 1)
        h.i32(h.pointers['tribeIDs'] + 0x190 + 0x39F4 + 111 * 4, 42)
        h.i32(h.pointers['slotCounts'] + 0x39F4 + 11 * 4, 3)
        h.hooks[h.sites['movement']][0](0x1D0000, 1, 11, 0)
        self.assertEqual(h.native_calls[-1][1], (0x1D0000, 1, 11, 1))

    def test_initial_trampoline_routes_and_preserves_stack_and_registers(self):
        h = self.h
        h.install()
        address, code = h.inserted
        self.assertEqual(h.assert_original, 'after')
        gate = 0x1E0000
        for role, expected in ((0, h.sites['initial'] + 7), (1, h.sites['initial'] + 119), (2, h.sites['initial'] + 109)):
            with self.subTest(role=role):
                cpu = Uc(UC_ARCH_X86, UC_MODE_32)
                cpu.mem_map(BASE, 0x100000)
                cpu.mem_write(address, code)
                cpu.mem_write(gate, b'\xB8' + struct.pack('<I', role) + b'\xC3')
                cpu.mem_write(0x120000, b'\x47\x00')
                cpu.reg_write(UC_X86_REG_ESI, 0x120000)
                cpu.reg_write(UC_X86_REG_ESP, 0x1C0000)
                cpu.reg_write(UC_X86_REG_EAX, 0x12345678)
                cpu.reg_write(UC_X86_REG_EFLAGS, 0x246)
                cpu.emu_start(address, expected, count=40)
                self.assertEqual(cpu.reg_read(UC_X86_REG_ESP), 0x1C0000)
                self.assertEqual(cpu.reg_read(UC_X86_REG_EAX), 71 if role == 0 else 0x12345678)
                if role: self.assertEqual(cpu.reg_read(UC_X86_REG_EFLAGS), 0x246)


if __name__ == '__main__': unittest.main()
