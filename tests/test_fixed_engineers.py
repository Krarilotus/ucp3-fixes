"""Integration ordering for the engineer-only module; native cases are separate."""
from pathlib import Path
import unittest
from lupa.lua54 import LuaRuntime, LuaError


class EngineerEntryTests(unittest.TestCase):
    def test_default_on_explicit_off_and_idempotence(self):
        for config, expected in ((None, 2), ({}, 2), ({'crew_lifecycle': False}, 0)):
            lua, module = self.entry()
            settings = None if config is None else lua.table_from(config)
            module.enable(module, settings)
            module.enable(module, settings)
            self.assertEqual(lua.globals().installed, expected)
            self.assertEqual(lua.globals().resolved, 1 if expected else 0)

    def test_last_preflight_failure_leaves_first_patch_uninstalled(self):
        lua, module = self.entry()
        lua.execute('package.preload.unman=function() return {prepare=function() error("occupied") end} end')
        with self.assertRaisesRegex(LuaError, 'occupied'):
            module.enable(module, lua.table())
        self.assertEqual(lua.globals().installed, 0)
        self.assertFalse(module.applied)

    @staticmethod
    def entry():
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
          resolved=0; installed=0
          package.preload['unit-handlers']=function() return {resolve=function()
            resolved=resolved+1; return {}
          end} end
          local function factory() return {prepare=function()
            return function() installed=installed+1 end
          end} end
          package.preload.crew=factory; package.preload.unman=factory
        ''')
        return lua, lua.execute((Path(__file__).resolve().parents[1] / 'fixed-engineers/init.lua').read_text())


if __name__ == '__main__':
    unittest.main()
