"""route-search: resolution, refusal, ordering, lifecycle and the redirected call's calling
convention, on a small synthetic image built from the two verified game code sequences."""
import importlib.util
import struct
import tempfile
import unittest
import zipfile

from lupa.lua54 import LuaError
import yaml

from route_search_harness import (ROOT, MODULE, FRAMEWORK_PROXY, Space, RouteSearch, Emulator, d,
                                  recording_policy, comparing_policy, reentering_policy)

LANGUAGES = ('de', 'en', 'fr', 'ru', 'hu', 'tr', 'ch', 'es', 'fa')
BASE = 0x400000
SITE_AT, SEARCH_AT, OTHER_AT = 0x1000, 0x3000, 0x5000
PATHFINDING = 0x02000000
ROW, AREA, FLAG = 0x02100000, 0x02200000, 0x02000080


def site_bytes(call_address, target):
    """setDestinationForUnit around its route search call (SHC 1.41 layout)."""
    head = bytes.fromhex('0F BF 8E AA 06 00 00 8B 44 24 14 50 51 B9') + d(PATHFINDING)
    call = b'\xE8' + d(target - (call_address + 5))
    tail = bytes.fromhex('3B C3 89 1D') + d(FLAG) + bytes.fromhex('0F 8E') + d(-0x18C)
    return head + call + tail


def search_bytes(row=ROW, area=AREA, area2=AREA):
    """PathFindingState::doPathfinding up to its first return (SHC 1.41 layout)."""
    return (bytes.fromhex('56 8B F1 8B 46 0C 8B 4E 14 8D 04 40 8B 04 85') + d(row)
            + bytes.fromhex('03 46 08 8D 0C 49 8B 0C 8D') + d(row)
            + bytes.fromhex('03 4E 10 0F B7 14 45') + d(area)
            + bytes.fromhex('0F B7 04 4D') + d(area2)
            + bytes.fromhex('57 33 FF 66 3B D0 74 37 39 BE 84 00 00 00 75 2F 39 BE 88 00 00 00 '
                            '75 27 66 3B C7 75 07 5F 33 C0 5E C2 08 00'))


def image(target=None, extra=()):
    memory = bytearray(0x8000)
    call = BASE + SITE_AT + 18
    memory[SITE_AT:SITE_AT + 35] = site_bytes(call, BASE + SEARCH_AT if target is None else target)
    search = search_bytes()
    memory[SEARCH_AT:SEARCH_AT + len(search)] = search
    for offset, data in extra:
        memory[offset:offset + len(data)] = data
    return bytes(memory)


def module(memory=None, hooks=True, enable=True):
    rs = RouteSearch(Space(image() if memory is None else memory, BASE), hooks=hooks)
    if enable:
        rs.enable()
    return rs


CALL = BASE + SITE_AT + 18
SEARCH = BASE + SEARCH_AT


class ResolutionTests(unittest.TestCase):
    def test_installed_alone_changes_nothing(self):
        rs = module()
        before = bytes(rs.space.memory)
        rs.fire_after_init()
        self.assertEqual((rs.scans, rs.code_writes, rs.data_writes, rs.allocations), ([], [], [], []))
        self.assertEqual(bytes(rs.space.memory), before)
        self.assertEqual((rs.module.version, rs.api.version), (1, 1))

    def test_registering_does_not_redirect_the_call(self):
        rs = module()
        nxt, unit = rs.add('a', 100)
        self.assertEqual(rs.code_writes, [])
        self.assertEqual(rs.space.u32(nxt), SEARCH, 'an unused next slot reaches the game search')
        self.assertNotEqual(nxt, unit)
        self.assertEqual(rs.space.read(CALL, 5), image()[SITE_AT + 18:SITE_AT + 23])

    def test_first_enabled_policy_redirects_the_call_once(self):
        rs = module()
        rs.add('a', 100)
        rs.add('b', 200)
        rs.enable_policy('a', 0x7000000)
        rs.enable_policy('b', 0x7000100)
        self.assertEqual(len(rs.code_writes), 1)
        address, data = rs.code_writes[0]
        self.assertEqual((address, data[0]), (CALL, 0xE8))
        head = CALL + 5 + struct.unpack('<i', data[1:])[0]
        self.assertIn(('code', head, 35), rs.allocations)
        self.assertTrue(any('a (100) -> b (200) -> the game' in m for _, m in rs.logs))

    def test_uses_the_framework_cache_then_proves_uniqueness(self):
        rs = module()
        rs.add('a', 100)
        kinds = [kind for kind, *_ in rs.scans]
        self.assertEqual(kinds.count('AOBScan'), 2)
        # One match each, proven from the start of the image and after the match.
        later = [start for kind, _, start in rs.scans if kind == 'scanForAOB' and start is not None]
        self.assertEqual(sorted(later), [BASE + SITE_AT + 1, SEARCH + 1])

    def test_occupied_call_is_refused_before_any_write(self):
        rs = module(image(target=BASE + OTHER_AT))
        with self.assertRaisesRegex(LuaError, r'route-search: .*already goes to 0x405000 instead '
                                              r'of the game.s search at 0x403000'):
            rs.add('a', 100)
        self.assertEqual((rs.code_writes, rs.data_writes), ([], []))
        self.assertTrue(any(level == 'WARNING' for level, _ in rs.logs))
        # Every later attempt gets the same answer.
        with self.assertRaisesRegex(LuaError, 'already goes to'):
            rs.add('b', 200)

    def test_call_target_is_decoded_modulo_2_32(self):
        # rel32 wraps: a target at or above 0x80000000 (large-address-aware game) reads as itself.
        rs = module(image(target=0x90000000))
        with self.assertRaisesRegex(LuaError, 'already goes to 0x90000000 instead'):
            rs.add('a', 100)

    def test_call_changed_between_registration_and_enable_is_refused(self):
        rs = module()
        rs.add('a', 100)
        rs.space.write(CALL + 1, d(BASE + OTHER_AT - (CALL + 5)))   # a later module's change
        with self.assertRaisesRegex(LuaError, 'changed by another module before the first'):
            rs.enable_policy('a', 0x7000000)
        self.assertEqual(rs.code_writes, [])

    def test_call_changed_after_redirect_is_refused_and_reported(self):
        rs = module()
        rs.add('a', 100)
        rs.add('b', 200)
        rs.enable_policy('a', 0x7000000)
        rs.space.write(CALL + 1, d(BASE + OTHER_AT - (CALL + 5)))
        with self.assertRaisesRegex(LuaError, 'changed by another module after route-search'):
            rs.enable_policy('b', 0x7000100)
        rs.fire_after_init()
        self.assertTrue(any(level == 'ERROR' and 'no longer goes to route-search' in message
                            for level, message in rs.logs))

    def test_ambiguous_site_or_search_is_refused(self):
        for name, extra in (('call', [(OTHER_AT, site_bytes(BASE + OTHER_AT + 18, SEARCH))]),
                            ('search', [(OTHER_AT, search_bytes())])):
            with self.subTest(duplicate=name):
                rs = module(image(extra=extra))
                with self.assertRaisesRegex(LuaError, 'matches more than once; refusing to guess'):
                    rs.add('a', 100)
                self.assertEqual(rs.code_writes, [])

    def test_missing_site_or_search_is_refused(self):
        broken_search = bytearray(image())
        broken_search[SEARCH_AT + 0x54] = 0xC3            # its first return is no longer ret 8
        broken_site = bytearray(image())
        broken_site[SITE_AT + 23] = 0x85                   # the caller no longer tests eax
        for memory in (bytes(broken_search), bytes(broken_site), bytes(0x8000)):
            rs = module(memory)
            with self.assertRaisesRegex(LuaError, 'was not found; this executable is not supported'):
                rs.add('a', 100)
            self.assertEqual(rs.code_writes, [])

    def test_search_reading_different_tables_is_refused(self):
        memory = bytearray(image())
        search = search_bytes(area2=AREA + 4)
        memory[SEARCH_AT:SEARCH_AT + len(search)] = search
        rs = module(bytes(memory))
        with self.assertRaisesRegex(LuaError, 'does not read its tables'):
            rs.add('a', 100)


def with_pe_header(memory, section_start=0x1000, section_size=0x5000):
    """A minimal PE header at the image base: one section [base+start, base+start+size)."""
    memory = bytearray(memory)
    memory[0:2] = b'MZ'
    memory[0x3C:0x40] = d(0x80)
    memory[0x80:0x84] = b'PE\0\0'
    memory[0x86:0x88] = (1).to_bytes(2, 'little')          # NumberOfSections
    memory[0x94:0x96] = (0xE0).to_bytes(2, 'little')       # SizeOfOptionalHeader
    entry = 0x80 + 0x18 + 0xE0
    memory[entry + 8:entry + 12] = d(section_size)          # VirtualSize
    memory[entry + 12:entry + 16] = d(section_start)        # VirtualAddress
    return bytes(memory)


class CodeSectionTests(unittest.TestCase):
    """With PE headers, uniqueness is proven in the code section only: fast in the game, and a
    copy of the bytes outside game code (another module's buffer) is not ambiguity."""

    def test_bounded_to_the_section_that_holds_the_match(self):
        rs = module(with_pe_header(image()))
        rs.add('a', 100)
        bounded = [r for r in rs.scan_ranges if r[1] is not None]
        self.assertEqual(len(bounded), 4)
        self.assertTrue(all(stop == BASE + 0x6000 for _, stop in bounded))
        self.assertEqual([r for r in rs.scan_ranges if r[1] is None], [])

    def test_copy_outside_the_section_is_not_ambiguous(self):
        copy = (0x6800, site_bytes(BASE + 0x6800 + 18, SEARCH))
        rs = module(with_pe_header(image(extra=[copy])))
        rs.add('a', 100)
        rs.enable_policy('a', 0x7000000)
        self.assertEqual(rs.code_writes[0][0], CALL)

    def test_second_match_inside_the_section_is_still_refused(self):
        rs = module(with_pe_header(image(extra=[(OTHER_AT, site_bytes(BASE + OTHER_AT + 18, SEARCH))])))
        with self.assertRaisesRegex(LuaError, 'matches more than once'):
            rs.add('a', 100)

    def test_without_headers_the_whole_default_range_is_scanned(self):
        rs = module()
        rs.add('a', 100)
        self.assertTrue(all(stop is None for _, stop in rs.scan_ranges))


class OrderAndLifecycleTests(unittest.TestCase):
    def test_lower_order_runs_outside_whatever_the_enable_order(self):
        for enable_order in (('a', 'b', 'c'), ('c', 'a', 'b'), ('b', 'c', 'a')):
            with self.subTest(enable_order=enable_order):
                rs = module()
                orders = {'a': 250, 'b': 100, 'c': 200}
                entries = {'a': 0x7000000, 'b': 0x7000100, 'c': 0x7000200}
                slots = {name: rs.add(name, orders[name])[0] for name in enable_order}
                for name in enable_order:
                    rs.enable_policy(name, entries[name])
                self.assertEqual([p['id'] for p in rs.policies()], ['b', 'c', 'a'])
                head = CALL + 5 + struct.unpack('<i', rs.space.read(CALL + 1, 4))[0]
                first = struct.unpack('<I', rs.space.read(head + 22, 4))[0]
                self.assertEqual(rs.space.u32(first), entries['b'])
                self.assertEqual(rs.space.u32(slots['b']), entries['c'])
                self.assertEqual(rs.space.u32(slots['c']), entries['a'])
                self.assertEqual(rs.space.u32(slots['a']), SEARCH)

    def test_registered_but_not_enabled_policy_is_skipped(self):
        rs = module()
        a, _ = rs.add('a', 100)
        b, _ = rs.add('b', 200)
        rs.enable_policy('b', 0x7000100)
        self.assertEqual([p['id'] for p in rs.policies()], ['b'])
        self.assertEqual((rs.space.u32(a), rs.space.u32(b)), (SEARCH, SEARCH))

    def test_equal_orders_and_duplicate_ids_are_refused(self):
        rs = module()
        rs.add('a', 100)
        with self.assertRaisesRegex(LuaError, "'a' and 'b' both ask for order 100"):
            rs.add('b', 100)
        with self.assertRaisesRegex(LuaError, "'a' is already registered"):
            rs.add('a', 150)
        self.assertEqual([p['id'] for p in rs.policies()], [])

    def test_bad_registrations_are_refused(self):
        rs = module()
        for spec in ({'order': 100}, {'id': '', 'order': 100}, {'id': 'x', 'order': 0},
                     {'id': 'x', 'order': 1000}, {'id': 'x', 'order': 100.5},
                     {'id': 'x', 'order': '100'}, {'id': 'x'}):
            with self.subTest(spec=spec), self.assertRaises(LuaError):
                rs.call('addPolicy', rs.lua.table_from(spec))
        with self.assertRaisesRegex(LuaError, 'expects'):
            rs.call('addPolicy', 'x')
        with self.assertRaisesRegex(LuaError, 'was not registered'):
            rs.enable_policy('unknown', 0x7000000)
        rs.add('x', 100)
        for entry in (0, 1.5, 'here'):
            with self.subTest(entry=entry), self.assertRaisesRegex(LuaError, 'address of its code'):
                rs.call('enablePolicy', 'x', entry)
        rs.enable_policy('x', 0x7000000)
        with self.assertRaisesRegex(LuaError, 'already enabled'):
            rs.enable_policy('x', 0x7000000)

    def test_registration_only_while_modules_are_enabled(self):
        rs = module(enable=False)
        with self.assertRaisesRegex(LuaError, 'before route-search was enabled; declare route-search'):
            rs.add('a', 100)
        rs.enable()
        rs.add('a', 100)
        self.assertEqual([name for name, _ in rs.after_init], ['afterInit'])
        rs.fire_after_init()
        with self.assertRaisesRegex(LuaError, 'before the game starts'):
            rs.add('b', 200)
        with self.assertRaisesRegex(LuaError, 'before the game starts'):
            rs.enable_policy('a', 0x7000000)

    def test_without_framework_hooks_it_still_works(self):
        rs = module(hooks=False)
        rs.add('a', 100)
        rs.enable_policy('a', 0x7000000)
        self.assertEqual(len(rs.code_writes), 1)

    def test_framework_proxy_needs_the_declared_options(self):
        # UCP 3.0.7 stops the launch when a proxied method returns a table and the module
        # declared no proxy options.
        rs = module()
        bare = rs.lua.execute(FRAMEWORK_PROXY)(rs.module, None)
        with self.assertRaisesRegex(LuaError, 'table expected, got nil'):
            bare.addPolicy(bare, rs.lua.table_from({'id': 'a', 'order': 100}))
        self.assertEqual(set(rs.options['proxy']['ignored'].values()), {'addPolicy', 'policies'})
        slots = rs.call('addPolicy', rs.lua.table_from({'id': 'b', 'order': 200}))
        self.assertEqual(rs.lua.eval('type')(slots), 'table')
        rs.enable_policy('b', 0x7000000)
        self.assertEqual([p['id'] for p in rs.policies()], ['b'])
        self.assertIsNone(rs.api.enable, 'the framework hides enable from other modules')

    def test_runtime_disable_reports_restart(self):
        rs = module()
        ok, reason = rs.module.disable(rs.module, rs.lua.table())
        self.assertFalse(ok)
        self.assertIn('restart', reason)


class CallingConventionTests(unittest.TestCase):
    """The redirected call, run from setDestinationForUnit's own instructions."""

    UNIT, OTHER, PREVIOUS = 0x00480000, 0x00490000, 0xCAFEBABE

    def prepare(self, results, policies):
        rs = module()
        space = rs.space
        space.put16(self.UNIT + 0x6AA, 0xFFFE)              # owner -2: sign extension visible
        space.put16(self.OTHER + 0x6AA, 3)
        made = {}
        for name, order, build in policies:
            nxt, unit = rs.add(name, order)
            made[name] = (nxt, unit, build)
        for name, (nxt, unit, build) in made.items():
            at = space.allocate(0x80)
            code = build(at, nxt, unit, rs)
            space.write(at, code)
            rs.enable_policy(name, at)
        unit = next(iter(made.values()))[1]
        space.put32(unit, self.PREVIOUS)                    # an outer search in progress
        head = CALL + 5 + struct.unpack('<i', space.read(CALL + 1, 4))[0]
        return rs, Emulator(space, SEARCH, unit, results), unit, head

    def run_site(self, emulator, unit=None):
        regs = {'esi': unit or self.UNIT, 'ebx': 0, 'edi': 0x1111, 'ebp': 0x2222,
                'eax': 0, 'ecx': 0, 'edx': 0}
        # [esp+0x14] at the site is setDestinationForUnit's canClimb argument.
        out, sp = emulator.run(BASE + SITE_AT, CALL + 5, regs, stack=[0, 0, 0, 0, 0, 1, 0])
        self.assertEqual(out['esp'], sp, 'ret 8 removes both arguments')
        self.assertEqual((out['ebx'], out['esi'], out['edi'], out['ebp']),
                         (0, unit or self.UNIT, 0x1111, 0x2222), 'preserved registers')
        return out

    def test_single_policy_reaches_the_game_search_with_the_same_call(self):
        log, count = 0x004A0000, 0x004A0100
        rs, emulator, unit, _ = self.prepare([42], [
            ('gate', 200, lambda at, n, u, rs: recording_policy(u, n, log, count))])
        out = self.run_site(emulator)
        self.assertEqual(out['eax'], 42)
        self.assertEqual(emulator.calls, [dict(ecx=PATHFINDING, owner=0xFFFFFFFE, climb=1, unit=self.UNIT)])
        self.assertEqual((emulator.u32(count), emulator.u32(log)), (1, self.UNIT))
        self.assertEqual(emulator.u32(unit), self.PREVIOUS, '[unit] is restored')

    def test_candidate_policy_outside_a_single_search_policy(self):
        log, count = 0x004A0000, 0x004A0100
        rs, emulator, unit, _ = self.prepare([30, 12], [
            ('gate', 200, lambda at, n, u, rs: recording_policy(u, n, log, count)),
            ('shortcut', 100, lambda at, n, u, rs: comparing_policy(n))])
        out = self.run_site(emulator)
        self.assertEqual(out['eax'], 42, 'the outer policy saw both inner results')
        self.assertEqual(len(emulator.calls), 2, 'one game search per candidate')
        for call in emulator.calls:
            self.assertEqual(call, dict(ecx=PATHFINDING, owner=0xFFFFFFFE, climb=1, unit=self.UNIT))
        # The inner policy ran once per candidate and saw the unit, not the esi the outer one
        # left (the PathFindingState).
        self.assertEqual(emulator.u32(count), 2)
        self.assertEqual((emulator.u32(log), emulator.u32(log + 4)), (self.UNIT, self.UNIT))
        self.assertEqual(emulator.u32(unit), self.PREVIOUS)

    def test_nested_search_for_another_unit_keeps_each_unit(self):
        log, flag = 0x004A0000, 0x004A0100
        holder = {}

        def build(at, n, u, rs):
            return reentering_policy(at, holder['head'], n, self.OTHER, u, log, flag)

        rs = module()
        space = rs.space
        space.put16(self.UNIT + 0x6AA, 2)
        nxt, unit = rs.add('nesting', 200)
        at = space.allocate(0x80)
        space.write(at, b'\xC3')
        rs.enable_policy('nesting', at)
        holder['head'] = CALL + 5 + struct.unpack('<i', space.read(CALL + 1, 4))[0]
        space.write(at, build(at, nxt, unit, rs))
        space.put32(unit, self.PREVIOUS)
        emulator = Emulator(space, SEARCH, unit, [9, 4])
        out = self.run_site(emulator)
        self.assertEqual(out['eax'], 4)
        self.assertEqual([(c['unit'], c['owner'], c['climb']) for c in emulator.calls],
                         [(self.OTHER, 7, 0), (self.UNIT, 2, 1)])
        self.assertEqual(emulator.u32(log), self.UNIT, '[unit] is back after the nested search')
        self.assertEqual(emulator.u32(unit), self.PREVIOUS)


class PackageTests(unittest.TestCase):
    def test_manifest_locale_and_package(self):
        definition = yaml.safe_load((MODULE / 'definition.yml').read_text(encoding='utf-8'))
        self.assertEqual((definition['name'], definition['type']), ('route-search', 'module'))
        self.assertEqual(definition['game'], ['SHC==1.41', 'SHCE==1.41'])
        self.assertEqual(set(definition['dependencies']), {'framework', 'frontend'})
        self.assertNotIn('family', definition)
        self.assertFalse((MODULE / 'options.yml').exists(), 'an owner module has no settings')
        self.assertEqual((MODULE / 'description.md').read_bytes(),
                         (MODULE / 'locale/description-en.md').read_bytes())
        spec = importlib.util.spec_from_file_location('build_modules', ROOT / 'tools/build_modules.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as output:
            with zipfile.ZipFile(builder.build_module(MODULE, output)) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertIn('locale/', names)
                for required in ('definition.yml', 'init.lua', 'description.md', 'README.md',
                                 'CREDITS.md', 'LICENSE'):
                    self.assertIn(required, names)
                self.assertEqual(yaml.safe_load(archive.read('definition.yml')), definition)
                for language in LANGUAGES:
                    text = archive.read(f'locale/description-{language}.md').decode('utf-8')
                    self.assertTrue(text.strip(), language)
                for entry in archive.infolist():
                    if not entry.is_dir():
                        self.assertEqual(archive.read(entry), (MODULE / entry.filename).read_bytes())
        self.assertTrue((MODULE / 'LICENSE').read_text(encoding='utf-8').startswith('MIT License'))


if __name__ == '__main__':
    unittest.main()
