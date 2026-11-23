"""Worker Delivery Fix next to UCP2 Legacy's ai_access, without game files.

ai_access ("Disable demolishing of inaccessible buildings", on in
ucp2-legacy-defaults) writes `jmp` over the `jne` that follows the AI heatmap's
accessibility call. A binding that requires the `jne` there stops the game at
startup with "AOB could not be found". ai_access drops
only the removal for result 0; result 2 (valid entrance, blocked keep route)
still removes, so this module's store query must stay active next to it.
A synthetic image holds every binding the module checks, laid out as in the
1.41 executables.
"""
from pathlib import Path
import re
import unittest

from lupa.lua54 import LuaRuntime, LuaError


MODULE = Path(__file__).resolve().parents[1] / 'worker-delivery-fix'
BASE, SIZE = 0x400000, 0x10000
# UCP2 Legacy 2.15.1/2.15.2 port/ai_access.lua: AOBScan(...) then writeCode(at, {0xEB}).
AI_ACCESS = ('75 07 66 C7 06 03 00 EB 12 83 F8 02 75 07 66 C7 06 03 00 EB 06 '
             '66 83 3E 03 75 14 0F BF 56 20 0F')
SLOT, UNITS, ROWS, AREAS, FLAGS = 0x70000000, 0x71000000, 0x72000000, 0x73000000, 0x74000000
STACK, BUILDINGS = 0x75000000, 0x76000000


def le(value):
    return (value & 0xFFFFFFFF).to_bytes(4, 'little')


def hexbytes(text):
    return bytes(int(token, 16) for token in text.split())


class Game:
    """Synthetic code image plus sparse data memory, read through a mocked `core`."""

    def __init__(self):
        self.image = bytearray(b'\xCC' * SIZE)
        self.data = {}
        self.detours = []
        at = self.at = {}

        def put(name, offset, *parts):
            at[name] = BASE + offset
            blob = b''.join(hexbytes(p) if isinstance(p, str) else p for p in parts)
            self.image[offset:offset + len(blob)] = blob

        accessible = 0x1000
        put('accessible', accessible, '83 EC 0C 8B 44 24 10 85 C0 57 8B F9 89 7C 24 04 7F 09 33 C0')
        put('row', accessible + 0x9B, '03 14 8D', le(ROWS), '0F B7 04 55', le(AREAS), '66 85 C0')
        put('area', accessible + 0xFC, '0F BF 04 55', le(AREAS), '3B C1 74 29 0F BF 96 E6 00 00 00')
        put('flags', accessible + 0x112, le(FLAGS))
        put('route', accessible + 0x119, '6A 00 50 51 55 B9', le(BUILDINGS), 'E8', le(0),
            '85 C0 75 05 BB 01 00 00 00')
        put('custom', 0x1400, '83 EC 08 8B 44 24 0C 85 C0 53 8B D9 89 5C 24 04 7F 09 33 C0')
        put('nextRow', 0x1460, '03 14 8D', le(ROWS), '0F B7 04 55', le(AREAS), '66 85 C0')
        put('storage', 0x1800, '53 55 56 8B 74 24 10 57 56 8B F9 E8', le(0),
            '83 F8 0A 0F 85', le(0))
        put('armory', 0x1A00, '8B 44 24 04 85 C0 57 8B F9 74 1B 8B 4C 24 14 8B 54 24 10 51')
        put('afterArmory', 0x1B00, '83 EC 08 53 55 33 C0 8B E9 BB 01 00 00 00 39 5D 08')
        heatmap = 0x2000
        call_end = BASE + heatmap + 27
        put('heatmap', heatmap, '0F BF 4E 02 83 3C 8D', le(FLAGS), '00 75 3E 6A 00 57 B9',
            le(BUILDINGS), 'E8', le(BASE + accessible - call_end),
            '85 C0 75 07 66 C7 06 03 00 EB 12 83 F8 02 75 07 66 C7 06 03 00 EB 06 '
            '66 83 3E 03 75 14 0F BF 56 20 0F')
        put('ox', 0x3000, '53 55 56 8B 35', le(SLOT), '69 F6 90 04 00 00 0F BF 86', le(0),
            '0F BF 8E', le(0), '33 ED 3B C5 57')
        put('afterOx', 0x3100, '51 53 8B 5C 24 0C 56 8B F3 69 F6 90 04 00 00 8B 86', le(0), '57')
        put('producers', 0x3200, '53 55 56 57 8B 3D', le(SLOT), '8B F7 69 F6 90 04 00 00 0F BF AE',
            le(UNITS + 0x348), '0F BF 9E', le(UNITS + 0x338), 'B9 0A 00 00 00')
        put('afterProducers', 0x3300, '51 8B 0D', le(SLOT), '8B C1 69 C0 90 04 00 00 53 55 0F BF A8',
            le(0), '89 6C 24 08')
        put('iron', 0x3400, '53 8B 1D', le(SLOT), '55 56 8B F3 69 F6 90 04 00 00 BD 05 00 00 00 33 D2')
        put('afterIron', 0x3500, '51 53 55 56 57 8B 3D', le(SLOT), '8B F7 69 F6 90 04 00 00 0F BF AE',
            le(0), '0F BF 86', le(0))
        self.write(UNITS - 0x614, 2500, 4)

        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        core = lua.table()
        core.AOBScan = self.aob
        core.scanForAOB = self.scan
        core.readInteger = lambda a: self.read(a, 4)
        core.readSmallInteger = lambda a: self.read(a, 2)
        core.readByte = lambda a: self.read(a, 1)
        core.readBytes = lambda a, n: lua.table_from([self.read(a + i, 1) for i in range(n)])
        core.detourCode = lambda cb, a, n: self.detours.append((a, n, cb))
        lua.globals().core = core
        lua.globals().package.path = str(MODULE).replace('\\', '/') + '/?.lua'
        self.delivery = lua.execute('return (require("delivery"))')

    def read(self, address, size):
        out = []
        for i in range(size):
            at = address + i
            if 0 <= at - BASE < SIZE:
                out.append(self.image[at - BASE])
            elif at in self.data:
                out.append(self.data[at])
            else:
                raise AssertionError(f'unexpected read at {at:#x}')
        return int.from_bytes(bytes(out), 'little')

    def write(self, address, value, size):
        for i, byte in enumerate((value & ((1 << 8 * size) - 1)).to_bytes(size, 'little')):
            self.data[address + i] = byte

    def scan(self, pattern, start=None, stop=None):
        rx = re.compile(b''.join(b'.' if t == '?' else re.escape(bytes([int(t, 16)]))
                                 for t in pattern.split()), re.DOTALL)
        found = rx.search(self.image, max(0, (start or BASE) - BASE))
        return BASE + found.start() if found else None

    def aob(self, pattern, start=None, stop=None):
        found = self.scan(pattern, start, stop)
        if found is None:
            raise RuntimeError('[data/cache]: AOB could not be found: ' + pattern)
        return found

    def apply_ai_access(self):
        """Do what UCP2 Legacy's ai_access does: scan its own AOB, write one jmp opcode."""
        site = self.aob(AI_ACCESS)
        self.image[site - BASE] = 0xEB
        return site

    def store_query(self, caller, kind=19, entry_area=5, blocked=0):
        """ECX after the detoured keep query for one granary/armory and one live worker.

        EAX is the entrance tile's area, ECX the keep's (3), EBX nonzero once the
        native check has already found the entrance invalid."""
        building_id, slot = 7, 3
        building = BUILDINGS + building_id * 0x32C
        unit = UNITS + slot * 0x490
        for address, value, size in (
                (STACK + 16, BUILDINGS, 4), (STACK + 28, caller, 4), (STACK + 32, building_id, 4),
                (BUILDINGS + 8, 100, 4), (building + 0xEA, 1, 2), (building + 0xE6, kind, 2),
                (SLOT, slot, 4), (unit + 0x98, 1234, 4), (unit + 0x96, 1, 2),
                (unit + 0xC4, 10, 2), (unit + 0xC6, 20, 2), (ROWS + 20 * 12, 20 * 400, 4),
                (AREAS + (20 * 400 + 10) * 2, 9, 2)):
            self.write(address, value, size)
        site, size, callback = self.detours[-1]
        registers = self.lua.table_from({'ESP': STACK, 'ESI': building, 'ECX': 3,
                                         'EAX': entry_area, 'EBX': blocked,
                                         'EDI': building_id})
        return callback(registers).ECX


class LegacyAiAccessTests(unittest.TestCase):
    def install(self, game):
        native = game.delivery.resolve()
        game.delivery.install(native)
        self.assertEqual([(a, n) for a, n, _ in game.detours], [(game.at['route'], 5)])
        return native

    def test_ai_access_owns_the_branch_after_the_heatmap_call(self):
        game = Game()
        self.assertEqual(game.scan(AI_ACCESS), game.at['heatmap'] + 29)

    def assert_queries(self, game):
        heatmap = game.at['heatmap'] + 27
        # A valid entrance in another area than the keep: the AI keeps the store
        # (same-area query, result 1 instead of the removing result 2).
        self.assertEqual(game.store_query(heatmap), 5)
        self.assertEqual(game.store_query(heatmap, kind=11), 5)
        # No usable entrance: left to the game, or to ai_access when it is on.
        self.assertEqual(game.store_query(heatmap, entry_area=0), 3)
        self.assertEqual(game.store_query(heatmap, blocked=1), 3)
        self.assertEqual(game.store_query(heatmap, kind=10), 3)  # stockpile
        # Worker deliveries use the worker's area.
        self.assertEqual(game.store_query(game.at['producers'] + 0x80), 9)
        self.assertEqual(game.store_query(game.at['storage'] + 0x109, kind=11), 9)

    def test_native_branch(self):
        game = Game()
        self.install(game)
        self.assert_queries(game)

    def test_starts_after_ai_access_and_keeps_both_fixes(self):
        game = Game()
        game.apply_ai_access()
        native = self.install(game)
        self.assertEqual(native.sites.heatmap, game.at['heatmap'])
        self.assert_queries(game)

    def test_ai_access_after_this_module_behaves_the_same(self):
        game = Game()
        self.install(game)
        before = bytes(game.image)
        site = game.apply_ai_access()
        changed = [BASE + i for i, (a, b) in enumerate(zip(before, game.image)) if a != b]
        self.assertEqual(changed, [site])
        self.assert_queries(game)

    def test_unknown_branch_is_refused_before_patching(self):
        game = Game()
        game.image[game.at['heatmap'] + 29 - BASE] = 0x74
        with self.assertRaisesRegex(LuaError, 'unexpected AI store removal branch 0x74'):
            game.delivery.resolve()
        self.assertEqual(game.detours, [])

    def test_changed_call_context_is_still_refused(self):
        game = Game()
        game.image[game.at['heatmap'] + 28 - BASE] = 0xC9
        # The mocked scanner raises in Python, as UCP's raises in Lua.
        with self.assertRaisesRegex((LuaError, RuntimeError), 'AOB could not be found'):
            game.delivery.resolve()
        self.assertEqual(game.detours, [])


if __name__ == '__main__':
    unittest.main()
