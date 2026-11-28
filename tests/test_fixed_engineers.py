"""Integration ordering for the engineer-only module; native cases are separate."""
from pathlib import Path
import unittest
from lupa.lua54 import LuaRuntime


class EngineerEntryTests(unittest.TestCase):
    def test_default_off_explicit_on_and_idempotence(self):
        for config, expected, resolved in ((None, 0, 0), ({}, 0, 0),
                                           ({'crew_lifecycle': True,
                                             'siege_target_stop': True}, 3, 1),
                                           ({'crew_lifecycle': True}, 2, 1),
                                           ({'siege_target_stop': True}, 1, 0),
                                           ({'crew_lifecycle': True,
                                             'siege_target_stop': False}, 2, 1),
                                           ({'crew_lifecycle': False,
                                             'siege_target_stop': False}, 0, 0)):
            lua, module = self.entry()
            settings = None if config is None else lua.table_from(config)
            module.enable(module, settings)
            module.enable(module, settings)
            self.assertEqual(lua.globals().installed, expected)
            self.assertEqual(lua.globals().resolved, resolved)

    def test_failed_crew_preflight_leaves_siege_targeting_enabled(self):
        lua, module = self.entry()
        lua.execute('''
          package.preload.unman=function() return {prepare=function() error("AOB not found") end} end
          package.preload['siege-targeting']=function() return {prepare=function()
            return function() targeting_installed=true end
          end} end
        ''')
        module.enable(module, lua.table_from({'crew_lifecycle': True, 'siege_target_stop': True}))
        self.assertEqual(lua.globals().installed, 0)
        self.assertTrue(lua.globals().targeting_installed)
        errors = list(lua.globals().errors.values())
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith('Siege crew cleanup is off:'))
        self.assertIn('AOB not found', errors[0])

    @staticmethod
    def entry():
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
          resolved=0; installed=0
          ERROR=2; errors={}
          function log(level, message)
            assert(level == ERROR)
            table.insert(errors, message)
          end
          package.preload['unit-handlers']=function() return {resolve=function()
            resolved=resolved+1; return {}
          end} end
          local function factory() return {prepare=function()
            return function() installed=installed+1 end
          end} end
          package.preload.crew=factory; package.preload.unman=factory
          package.preload['siege-targeting']=factory
        ''')
        return lua, lua.execute((Path(__file__).resolve().parents[1] / 'fixed-engineers/init.lua').read_text())


if __name__ == '__main__':
    unittest.main()
