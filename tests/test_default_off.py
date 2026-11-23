"""Every fix module touches the game only when its switch is exactly `true`.

Each entry point runs with a core and helper modules that record every call. Absent,
empty, false and wrong-type values must leave no trace; `true` must start the scan.
"""
from pathlib import Path
import unittest

from lupa.lua54 import LuaRuntime, LuaError

ROOT = Path(__file__).resolve().parents[1]
MISSING = object()
VALUES = (None, MISSING, False, 'true', 1, True)  # None: no config table; MISSING: {}
# Module, switches to try one at a time.
MODULES = {
    'worker-delivery-fix': ('reachable_delivery',),
    'gatehouse-capture-fix': ('living_gatehouse_occupants',),
    'hunter-targeting-fix': ('hunter_targeting',),
    'fixed-engineers': ('crew_lifecycle', 'siege_target_stop'),
    'hopfarm-limit-fix': ('enabled',),
    'aiv-troops-behaviour': ('enabled',),
    'build-over-workers': ('buildings', 'walls'),
}
HELPERS = ('delivery', 'capture', 'hunting', 'unit-handlers', 'crew', 'unman', 'siege-targeting', 'behavior')


def entry(name):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
      calls = {}
      local function recorder(owner)
        return setmetatable({}, {__index = function(_, key)
          return function(...)
            calls[#calls + 1] = owner .. "." .. key
            error("stop after the first call")
          end
        end})
      end
      core = recorder("core")
      INFO, WARNING, ERROR = 0, 1, 2
      log = function(...) end
      package.preload.templates = function() return {} end
      for _, helper in ipairs({...}) do
        package.preload[helper] = function() return recorder(helper) end
      end
    '''.replace('{...}', '{' + ', '.join(f'"{h}"' for h in HELPERS) + '}'))
    return lua, lua.execute((ROOT / name / 'init.lua').read_text(encoding='utf-8'))


class DefaultOffTests(unittest.TestCase):
    def test_only_true_switches_a_fix_on(self):
        for name, switches in MODULES.items():
            for switch in switches:
                for value in VALUES:
                    with self.subTest(module=name, switch=switch, value=value):
                        lua, module = entry(name)
                        if value is None:
                            config = None
                        elif value is MISSING:
                            config = lua.table()
                        else:
                            config = lua.table_from({switch: value})
                        if value is True:
                            with self.assertRaises(LuaError):  # the recorder stops at the first call
                                module.enable(module, config)
                            self.assertTrue(list(lua.globals().calls.values()))
                        else:
                            module.enable(module, config)
                            self.assertEqual(list(lua.globals().calls.values()), [])


if __name__ == '__main__':
    unittest.main()
