"""Check the customization's effective runtime default and patch lifecycle."""
from pathlib import Path
import unittest

from lupa.lua54 import LuaRuntime, LuaError


ENTRY = Path(__file__).resolve().parents[1] / 'worker-delivery-fix' / 'init.lua'


def entry():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
      resolved=0; installed=0
      package.preload.delivery=function() return {
        resolve=function() resolved=resolved+1; return {} end,
        install=function() installed=installed+1 end
      } end
    ''')
    return lua, lua.execute(ENTRY.read_text(encoding='utf-8'))


class WorkerDeliveryEntryTests(unittest.TestCase):
    def test_default_on_explicit_off_and_idempotence(self):
        for setting, expected in ((None, 1), ({}, 1), ({'reachable_delivery': True}, 1),
                                  ({'reachable_delivery': False}, 0)):
            with self.subTest(setting=setting):
                lua, module = entry()
                config = None if setting is None else lua.table_from(setting)
                module.enable(module, config)
                module.enable(module, config)
                self.assertEqual((lua.globals().resolved, lua.globals().installed),
                                 (expected, expected))

    def test_failed_preflight_does_not_install(self):
        lua, module = entry()
        lua.execute('package.preload.delivery=function() return {resolve=function() error("bad binding") end} end')
        with self.assertRaisesRegex(LuaError, 'bad binding'):
            module.enable(module, lua.table())
        self.assertEqual(lua.globals().installed, 0)
        self.assertFalse(module.applied)


if __name__ == '__main__':
    unittest.main()
