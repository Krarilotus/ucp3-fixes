"""Exercise every supported troop through assignment, mapper and movement hooks."""
import unittest
import yaml
from test_behavior import BehaviorHarness
from test_modules import ROOT, AIV

ROWS = {30: 1, 22: 6, 23: 7, 24: 8, 25: 9, 26: 10, 27: 11, 28: 12,
        71: 13, 72: 14, 73: 15, 70: 16, 74: 17, 75: 18, 76: 19}


class AllTroopPathsTests(unittest.TestCase):
    def test_defense_and_own_slot_mapping_cover_all_troops_and_personalities(self):
        h = BehaviorHarness()
        h.install(defaults={'InitialRole': 'defend', 'Movement': 'hold'})
        gate = h.callbacks[0x1E0000][0]
        mapper = h.hooks[h.sites['mapper']][0]
        unit_address = h.pointers['unitType'] + 0x490
        h.i16(h.pointers['unitOwner'] + 0x490, 1)
        for ai in range(1, 17):
            h.i32(h.pointers['aiType'] + 0x39F4, ai + 1)
            for unit, row in ROWS.items():
                with self.subTest(ai=ai, unit=unit):
                    h.i16(unit_address, unit)
                    for can_dig in (0, 1):
                        h.i16(unit_address + 0x2E0, can_dig)
                        self.assertEqual(gate(h.lua.table_from({'EBP': ai, 'ESI': unit_address})).EAX, 1)
                    self.assertEqual(mapper(0x1D0000, 1, 1), row)
                    # The recruitment conversion lookup must use the same row too.
                    h.i16(unit_address, 1)
                    h.i16(unit_address + 0x23C, unit)
                    self.assertEqual(mapper(0x1D0000, 1, 1), row)
        h.i16(h.pointers['unitOwner'] + 0x490, 3)  # Human
        self.assertEqual(mapper(0x1D0000, 1, 1), 12345)

    def test_hold_and_patrol_cover_all_troops_in_both_executable_layouts(self):
        for stride in (0x334, 0x688):
            for mode in ('hold', 'patrol'):
                h = BehaviorHarness()
                h.i32(h.sites['movement'] + 11, stride)
                h.install(defaults={'Movement': mode})
                move = h.hooks[h.sites['movement']][0]
                this, tribe, ordinal = 0x1D0000, 1, 1
                h.i32(h.pointers['tribeOwner'] + stride, 1)
                h.i32(h.pointers['tribeOwner'] + stride + 8, 42)
                h.i32(h.pointers['tribeIDs'] - 0x5B8 + 0x39F4, 2)
                for ai in range(1, 17):
                    h.i32(h.pointers['aiType'] + 0x39F4, ai + 1)
                    h.i32(this + ai * 0x2A4 + 0x114, 2)
                    for row in ROWS.values():
                        with self.subTest(stride=stride, mode=mode, ai=ai, row=row):
                            index = row * 10 + ordinal
                            h.i16(h.pointers['tribeIDs'] + 0x39F4 + index * 2, tribe)
                            h.i32(h.pointers['tribeIDs'] + 0x190 + 0x39F4 + index * 4, 42)
                            h.i32(h.pointers['slotCounts'] + 0x39F4 + row * 4, 5)
                            move(this, tribe, row, 0)
                            self.assertEqual(h.native_calls[-1][1], (this, tribe, row, 1 if mode == 'hold' else 4))
                            r = h.callback('groupLimit', EBP=1, EAX=row, EBX=99, EDX=2)
                            self.assertEqual(r.EBX, 5 if mode == 'hold' else 2)
                            h.i32(h.pointers['slotCounts'] + 0x39F4 + row * 4, 0)
                            count = len(h.native_calls)
                            self.assertEqual(move(this, tribe, row, 0), 0)
                            self.assertEqual(len(h.native_calls), count)

    def test_native_and_disabled_controls_preserve_original_paths(self):
        h = BehaviorHarness()
        h.enable({'behavior': h.lua.table_from({'enabled': False})})
        self.assertEqual(len(h.writes), 3)
        self.assertFalse(h.hooks or h.callbacks or h.aic)
        h = BehaviorHarness()
        h.install()
        gate = h.callbacks[0x1E0000][0]
        mapper = h.hooks[h.sites['mapper']][0]
        h.i16(h.pointers['unitOwner'] + 0x490, 1)
        for ai in range(1, 17):
            for unit in ROWS:
                h.i16(h.pointers['unitType'] + 0x490, unit)
                self.assertEqual(gate(h.lua.table_from({'EBP': ai, 'ESI': h.pointers['unitType'] + 0x490})).EAX, 0)
                self.assertEqual(mapper(0x1D0000, 1, 1), 12345)
        options = yaml.safe_load((ROOT / AIV / 'options.yml').read_text(encoding='utf-8'))['options']
        self.assertIs(options[1]['contents']['value'], False)


if __name__ == '__main__': unittest.main()
