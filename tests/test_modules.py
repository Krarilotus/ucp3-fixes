"""Exercise the Lua entry points and their actual x86 output without a game."""
from pathlib import Path
import re
import unittest

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from lupa.lua54 import LuaRuntime, LuaError
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x100000
HOP = 'hopfarm-limit-fix'
AIV = 'aiv-troops-behaviour'
FIXTURES = {
    HOP: bytes.fromhex('0F B7 0A 66 83 F9 1E 74 0C 66 83 F9 20 74 06 66 83 F9 21 75 11 85 FF'),
    AIV: bytes.fromhex('83 7C 24 1C 09 8B 44 24 38 C7 00 00 00 00 00 0F 84 32 03 00 00 83 7C 24 1C 0B 0F 84 27 03 00 00 83 7C 24 1C 12 0F 84 1C 03 00 00'),
}


class ModuleHarness:
    def __init__(self, name, memory, base=BASE):
        self.name, self.memory, self.base = name, bytearray(memory), base
        self.scans, self.writes = [], []
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().scan = self.scan
        self.lua.globals().write = self.write
        # Match core.AOBScan's throwing contract, not the original module's nil assumption.
        self.lua.execute('''
          core = {
            AOBScan = function(pattern, ...)
              local address = scan(pattern, select('#', ...))
              if address == nil then error('AOB not found: ' .. pattern) end
              return address
            end,
            writeCode = write,
          }
          INFO = 0
          log = function(...) end
        ''')
        self.module = self.lua.execute((ROOT / name / 'init.lua').read_text(encoding='utf-8'))

    def scan(self, pattern, extra_arguments):
        self.scans.append((pattern, extra_arguments))
        offset = self.memory.find(bytes.fromhex(pattern))
        return None if offset < 0 else self.base + offset

    def write(self, address, code):
        data = bytes(code.values())
        offset = address - self.base
        if not 0 <= offset <= len(self.memory) - len(data):
            raise AssertionError('out-of-bounds patch')
        self.memory[offset:offset + len(data)] = data
        self.writes.append((address, data))

    def enable(self, config=None):
        self.module.enable(self.module, self.lua.table_from(config or {}))


class ModuleTests(unittest.TestCase):
    def test_disabled_means_no_scan_or_write(self):
        for name in FIXTURES:
            with self.subTest(module=name):
                h = ModuleHarness(name, b'unsupported executable')
                h.enable({'enabled': False})
                self.assertEqual((h.scans, h.writes), ([], []))

    def test_missing_pattern_fails_before_writing(self):
        for name in FIXTURES:
            with self.subTest(module=name):
                h = ModuleHarness(name, b'unsupported executable')
                with self.assertRaisesRegex(LuaError, name + ': cannot locate'):
                    h.enable({'enabled': True})
                self.assertEqual(h.writes, [])
                self.assertFalse(h.module.applied)

    def test_repeated_enable_is_idempotent(self):
        for name, fixture in FIXTURES.items():
            with self.subTest(module=name):
                h = ModuleHarness(name, fixture)
                h.enable({'enabled': True})
                memory, writes = bytes(h.memory), list(h.writes)
                h.enable({'enabled': True})
                self.assertEqual((bytes(h.memory), h.writes), (memory, writes))
                self.assertEqual(len(h.scans), 1)
                self.assertEqual(h.scans[0][1], 0, 'use the framework AOB cache')

    def test_old_empty_config_still_enables(self):
        for name, fixture in FIXTURES.items():
            with self.subTest(module=name):
                h = ModuleHarness(name, fixture)
                h.enable()
                self.assertTrue(h.writes)

    def test_runtime_disable_reports_restart_and_preserves_patch(self):
        for name, fixture in FIXTURES.items():
            with self.subTest(module=name):
                h = ModuleHarness(name, fixture)
                h.enable()
                before = bytes(h.memory)
                ok, reason = h.module.disable(h.module, h.lua.table())
                self.assertFalse(ok)
                self.assertIn('restart', reason)
                self.assertEqual(bytes(h.memory), before)

    def test_hop_rejects_missing_zero_extension(self):
        memory = bytearray(FIXTURES[HOP])
        memory[1] = 0xBF  # movsx instead of movzx: range check's assumption changed
        h = ModuleHarness(HOP, memory)
        with self.assertRaises(LuaError):
            h.enable()
        self.assertEqual(h.writes, [])

    def test_aiv_preflights_all_three_branches(self):
        memory = bytearray(FIXTURES[AIV])
        memory[37] = 0x90  # another patch has modified the last jump
        h = ModuleHarness(AIV, memory)
        with self.assertRaises(LuaError):
            h.enable()
        self.assertEqual(h.writes, [])

    def test_hop_machine_code_accepts_exactly_four_farm_types(self):
        h = ModuleHarness(HOP, FIXTURES[HOP])
        h.enable()
        self.assertEqual(len(h.writes), 1)
        address, patch = h.writes[0]
        self.assertEqual((address, len(patch)), (BASE + 3, 18))
        self.assertEqual(h.memory[:3], FIXTURES[HOP][:3])
        self.assertEqual(h.memory[21:], FIXTURES[HOP][21:])
        instructions = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(patch, address))
        self.assertEqual(instructions[2].mnemonic, 'ja')
        self.assertEqual(int(instructions[2].op_str, 16), address + 35)
        cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        cpu.mem_map(BASE, 4096)
        cpu.mem_write(address, patch)
        # Exhaust the actual 16-bit building-type domain, zero-extended by the game.
        for building_type in range(65536):
            cpu.reg_write(UC_X86_REG_ECX, building_type)
            cpu.emu_start(address, BASE + 4096, count=3)
            expected = address + (8 if building_type in {30, 31, 32, 33} else 35)
            self.assertEqual(cpu.reg_read(UC_X86_REG_EIP), expected, building_type)

    def test_aiv_machine_code_changes_only_rows_9_11_18(self):
        h = ModuleHarness(AIV, FIXTURES[AIV])
        h.enable()
        self.assertEqual([(a - BASE, len(b)) for a, b in h.writes], [(15, 6), (26, 6), (37, 6)])
        changed = {i for i, (a, b) in enumerate(zip(FIXTURES[AIV], h.memory)) if a != b}
        self.assertEqual(changed, set(range(15, 21)) | set(range(26, 32)) | set(range(37, 43)))
        cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        cpu.mem_map(BASE, 4096)
        stack = BASE + 2048
        cpu.reg_write(UC_X86_REG_ESP, stack)
        cpu.mem_write(stack + 0x38, (BASE + 3000).to_bytes(4, 'little'))
        endpoints = []
        for code in (FIXTURES[AIV], bytes(h.memory)):
            # Invalidate translated instructions before replacing original/patched code.
            cpu.ctl_remove_cache(BASE, BASE + 4096)
            cpu.mem_write(BASE, code)
            result = []
            for row in range(22):
                cpu.mem_write(stack + 0x1C, row.to_bytes(4, 'little'))
                # Stop immediately before either the row body or the skip destination.
                stop = BASE + len(code)
                if code == FIXTURES[AIV] and row in {9, 11, 18}:
                    stop = BASE + 0x347
                cpu.emu_start(BASE, stop, count=40)
                result.append(cpu.reg_read(UC_X86_REG_EIP))
            endpoints.append(result)
        self.assertEqual([i for i, (a, b) in enumerate(zip(*endpoints)) if a != b], [9, 11, 18])
        self.assertEqual(endpoints[0][13], endpoints[1][13], 'slave row is unchanged')
        self.assertEqual(set(endpoints[1]), {BASE + 43})

    def test_metadata_localization_and_package_inputs(self):
        for name in FIXTURES:
            with self.subTest(module=name):
                folder = ROOT / name
                definition = yaml.safe_load((folder / 'definition.yml').read_text(encoding='utf-8'))
                self.assertEqual(definition['name'], name)
                self.assertEqual(definition['type'], 'module')
                options_text = (folder / 'options.yml').read_text(encoding='utf-8')
                option = yaml.safe_load(options_text)['options'][0]
                self.assertEqual(option['url'], name + '.enabled')
                self.assertIs(option['contents']['value'], True)
                keys = set(re.findall(r'{{(.*?)}}', options_text))
                for lang in ('en', 'de'):
                    locale = yaml.safe_load((folder / 'locale' / (lang + '.yml')).read_text(encoding='utf-8'))
                    self.assertTrue(keys <= locale.keys())
                    self.assertTrue(all(isinstance(v, str) and v.strip() for v in locale.values()))
                    self.assertTrue((folder / 'locale' / ('description-' + lang + '.md')).is_file())
                self.assertEqual((folder / 'description.md').read_bytes(), (folder / 'locale/description-en.md').read_bytes())
                files = yaml.safe_load((folder / 'files.yml').read_text(encoding='utf-8'))['files']
                expected = {'definition.yml', 'init.lua', 'options.yml', 'description.md', 'README.md', 'locale'}
                if name == AIV: expected.add('behavior')
                self.assertEqual({x['src'] for x in files}, expected)
                self.assertTrue(all((folder / x['src']).exists() for x in files))


if __name__ == '__main__':
    unittest.main()
