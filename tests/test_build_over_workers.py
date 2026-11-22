"""Build Over Workers: package contract, vanilla defaults and the off path without a game.

The x86 placement checks need both 1.41 executables and UCP's fasm.dll; they live in
build-over-workers/bench (see its README) and are not part of this portable suite.
"""
from pathlib import Path
import importlib.util
import re
import tempfile
import unittest
import zipfile

from lupa.lua54 import LuaRuntime, LuaError
import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = 'build-over-workers'
FOLDER = ROOT / NAME
LANGUAGES = ('de', 'en', 'fr', 'ru', 'hu', 'tr', 'ch', 'es', 'fa')
# Unchanged from the reviewed source (Krarilotus/Build-over-Workers@b6caee5), so
# existing profiles keep their values.
URLS = ('build-over-workers.buildings', 'build-over-workers.walls',
        'build-over-workers.keepOnWalls', 'build-over-workers.allies')
SWITCHES = {'buildings': True, 'walls': True, 'allies': True, 'keepOnWalls': True}


def options():
    found = {}

    def walk(items):
        for item in items:
            if 'url' in item:
                found[item['url']] = item['contents']['value']
            walk(item.get('children', []))

    walk(yaml.safe_load((FOLDER / 'options.yml').read_text(encoding='utf-8'))['options'])
    return found


def entry():
    """Load init.lua with a core whose every access is recorded."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
      calls = {}
      core = setmetatable({}, {__index = function(_, name)
        return function(...)
          calls[#calls + 1] = name
          if name == "AOBScan" then error("AOB not found") end
          error("unexpected core." .. name)
        end
      end})
      package.preload.templates = function() return {} end
    ''')
    return lua, lua.execute((FOLDER / 'init.lua').read_text(encoding='utf-8'))


class BuildOverWorkersTests(unittest.TestCase):
    def test_definition(self):
        definition = yaml.safe_load((FOLDER / 'definition.yml').read_text(encoding='utf-8'))
        self.assertEqual((definition['name'], definition['version'], definition['type'], definition['author']),
                         (NAME, '1.1.0', 'module', 'Monsterfish'))
        self.assertEqual(definition['dependencies'], {'framework': '^3.0.7', 'frontend': '^1.0.2'})
        self.assertEqual(definition['game'], ['SHC==1.41', 'SHCE==1.41'])
        self.assertNotIn('family', definition)

    def test_every_switch_defaults_off_with_unchanged_urls(self):
        self.assertEqual(options(), {url: False for url in URLS})
        source = (FOLDER / 'init.lua').read_text(encoding='utf-8')
        self.assertIn('local DEFAULTS = { buildings = false, walls = false, allies = false, keepOnWalls = false }',
                      source)

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
                with self.assertRaisesRegex(LuaError, NAME + ': could not find'):
                    module.enable(module, lua.table_from({part: True}))
                self.assertEqual(list(lua.globals().calls.values()), ['AOBScan'])

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
                self.assertEqual(Path(archive.filename).name, f'{NAME}-1.1.0.zip')
                files = {n for n in archive.namelist() if not n.endswith('/')}
                self.assertEqual(files, {'definition.yml', 'description.md', 'options.yml', 'init.lua',
                                         'templates.lua', 'CREDITS.md',
                                         *(f'locale/{l}.yml' for l in LANGUAGES),
                                         *(f'locale/description-{l}.md' for l in LANGUAGES)})

    def test_credits(self):
        credits = (FOLDER / 'CREDITS.md').read_text(encoding='utf-8')
        self.assertIn('Monsterfish (author)', credits)
        self.assertIn('GPL-3.0', credits)
        self.assertIn('relicensed by\nthe author under GPL-3.0 for inclusion', credits)


if __name__ == '__main__':
    unittest.main()
