"""Build Over Workers: vanilla defaults, the off path and the package, without a game."""
from pathlib import Path
import importlib.util
import re
import tempfile
import unittest
import zipfile

from lupa.lua54 import LuaRuntime
import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = 'build-over-workers'
FOLDER = ROOT / NAME
LANGUAGES = ('de', 'en', 'fr', 'ru', 'hu', 'tr', 'ch', 'es', 'fa')
# Saved profiles refer to these URLs.
URLS = ('build-over-workers.buildings', 'build-over-workers.walls',
        'build-over-workers.keepOnWalls', 'build-over-workers.allies')
# keepOnWalls does nothing while walls is off.
DEFAULTS = {'build-over-workers.buildings': False, 'build-over-workers.walls': False,
            'build-over-workers.keepOnWalls': True, 'build-over-workers.allies': False}


def options():
    found = {}

    def walk(items):
        for item in items:
            if 'url' in item:
                found[item['url']] = item['contents']['value']
            walk(item.get('children', []))

    walk(yaml.safe_load((FOLDER / 'options.yml').read_text(encoding='utf-8'))['options'])
    return found


def entry(ambiguous=False):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ambiguous = ambiguous
    lua.execute("""
      ERROR = 2
      calls, logs = {}, {}
      log = function(level, message) logs[#logs + 1] = {level, message} end
      core = setmetatable({}, {__index = function(_, name)
        return function()
          calls[#calls + 1] = name
          if name == "AOBScanUnique" then
            return nil, ambiguous and "found more than once" or "not found"
          end
          error("unexpected core." .. name)
        end
      end})
      package.preload.templates = function() return {} end
    """)
    return lua, lua.execute((FOLDER / 'init.lua').read_text(encoding='utf-8'))


class BuildOverWorkersTests(unittest.TestCase):
    def test_defaults_with_unchanged_urls(self):
        self.assertEqual(set(options()), set(URLS))
        self.assertEqual(options(), DEFAULTS)

    def test_unconfigured_or_switched_off_module_touches_nothing(self):
        for config in (None, {}, {'buildings': False, 'walls': False},
                       {'allies': True, 'keepOnWalls': True}):
            with self.subTest(config=config):
                lua, module = entry()
                module.enable(module, None if config is None else lua.table_from(config))
                self.assertEqual(list(lua.globals().calls.values()), [])

    def test_enabled_part_resolves_before_writing(self):
        for part in ('buildings', 'walls'):
            with self.subTest(part=part):
                lua, module = entry()
                module.enable(module, lua.table_from({part: True}))
                self.assertEqual(list(lua.globals().calls.values()), ['AOBScanUnique'])
                self.assertIn('is off:', lua.globals().logs[1][2])
                self.assertEqual(lua.globals().logs[1][1], 2)

    def test_ambiguous_signature_is_refused_before_writing(self):
        lua, module = entry(ambiguous=True)
        module.enable(module, lua.table_from({'buildings': True}))
        self.assertEqual(list(lua.globals().calls.values()), ['AOBScanUnique'])
        self.assertEqual(lua.globals().logs[1][2],
                         'Building over workers is off: the building placement test: found more than once')

    def test_runtime_disable_reports_restart(self):
        lua, module = entry()
        ok, reason = module.disable(module, lua.table())
        self.assertIs(ok, False)
        self.assertEqual(reason, 'build-over-workers: restart the game to turn it off')

    def test_writes_no_save_data(self):
        # No map-extensions section or other persisted state: members of a setup
        # family may differ in this module without breaking saves.
        for name in ('init.lua', 'templates.lua'):
            source = (FOLDER / name).read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'map.?extensions|modules\.|io\.|require\("(?!templates)', source), name)
        definition = yaml.safe_load((FOLDER / 'definition.yml').read_text(encoding='utf-8'))
        self.assertNotIn('map-extensions', definition['dependencies'])

    def test_locales_and_package(self):
        keys = set(yaml.safe_load((FOLDER / 'locale/en.yml').read_text(encoding='utf-8')))
        for language in LANGUAGES:
            locale = yaml.safe_load((FOLDER / f'locale/{language}.yml').read_text(encoding='utf-8'))
            self.assertEqual(set(locale), keys, language)
            self.assertTrue(all(isinstance(v, str) and v.strip() for v in locale.values()), language)
            description = (FOLDER / f'locale/description-{language}.md').read_text(encoding='utf-8')
            self.assertTrue(description.startswith('# Build Over Workers\n'), language)
        self.assertEqual((FOLDER / 'description.md').read_bytes(), (FOLDER / 'locale/description-en.md').read_bytes())
        spec = importlib.util.spec_from_file_location('build_modules', ROOT / 'tools/build_modules.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as output:
            with zipfile.ZipFile(builder.build_module(FOLDER, output)) as archive:
                self.assertEqual(Path(archive.filename).name, f'{NAME}-1.1.1.zip')
                files = {n for n in archive.namelist() if not n.endswith('/')}
                self.assertEqual(files, {'definition.yml', 'description.md', 'options.yml', 'init.lua',
                                         'templates.lua', 'CREDITS.md', 'LICENSE',
                                         *(f'locale/{l}.yml' for l in LANGUAGES),
                                         *(f'locale/description-{l}.md' for l in LANGUAGES)})


if __name__ == '__main__':
    unittest.main()
