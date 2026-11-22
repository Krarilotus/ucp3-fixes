"""UCP3 Fixes and the UCP3 setup family are plugins: dependencies and suggested settings only."""

from pathlib import Path
import importlib.util
import tempfile
import unittest
import zipfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'external-options.yml'
LANGUAGES = ('de', 'en', 'fr', 'ru', 'hu', 'tr', 'ch', 'es', 'fa')
FAMILY = 'ucp3'
FAMILY_FRONTEND = '>=1.0.17 <2.0.0'

FIXES = 'ucp3-fixes'
FIXES_DEPENDENCIES = {
    'framework': '^3.0.7', 'frontend': '^1.0.2',
    'worker-delivery-fix': '^0.2.0', 'gatehouse-capture-fix': '^0.2.0',
    'hunter-targeting-fix': '^0.2.0', 'fixed-engineers': '^0.3.0',
    'hopfarm-limit-fix': '^0.2.0', 'aiv-troops-behaviour': '^0.3.0',
    'interface-visual-fixes': '^0.2.0', 'audio-fixes': '^0.2.0',
}
# Every option URL UCP3 Fixes turns on (W2 proposal 2.1). Interface & Visual's two
# interface features and its Ghost Objects repair are deliberately absent.
FIXES_SUGGESTED = {
    'worker-delivery-fix.reachable_delivery', 'gatehouse-capture-fix.living_gatehouse_occupants',
    'hunter-targeting-fix.hunter_targeting', 'fixed-engineers.siege_target_stop',
    'fixed-engineers.crew_lifecycle', 'hopfarm-limit-fix.enabled', 'aiv-troops-behaviour.enabled',
    'interface-visual-fixes.clear-unique-building-preview',
    'interface-visual-fixes.building-preview-during-camera-movement',
    'interface-visual-fixes.distinct-dead-tree-sprites', 'interface-visual-fixes.tower-door-height',
    'interface-visual-fixes.cliff-texture-direction',
    'audio-fixes.startup-sfx-volume', 'audio-fixes.video-fx-volume', 'audio-fixes.positional-audio',
}
MEMBERS = {
    'ucp3-basics': dict(
        display='UCP3 Basics', label='Basics', root=True, tags=['modpack'], suggested=None,
        dependencies={'ucp2-legacy-defaults': '^2.15.1', 'graphicsApiReplacer': '^1.3.0'}),
    'ucp3-basics-fixes': dict(
        display='UCP3 Basics + Fixes', label='Basics + Fixes', root=False, tags=['modpack', 'bugfixes'],
        suggested=None, dependencies={'ucp3-basics': '^1.0.0', 'ucp3-fixes': '^0.2.0'}),
    'ucp3-recommended': dict(
        display='UCP3 Recommended', label='Recommended', root=False,
        tags=['modpack', 'bugfixes', 'textures', 'interface'],
        dependencies={'ucp3-basics': '^1.0.0', 'ucp3-fixes': '^0.2.0', 'ConqueringArabia': '^1.0.3',
                      'build-over-workers': '^1.1.0', 'interface-visual-fixes': '^0.2.0'},
        # Build Over Workers as its author shipped 1.0.3 (all on) and the two interface features.
        suggested={'interface-visual-fixes.lobby-map-descriptions', 'interface-visual-fixes.lobby-load',
                   'build-over-workers.buildings', 'build-over-workers.walls',
                   'build-over-workers.keepOnWalls', 'build-over-workers.allies'}),
}
PLUGINS = (FIXES, *MEMBERS)


def load(path):
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def definition(name):
    return load(ROOT / name / 'definition.yml')


PYTHON_TYPES = {'boolean': bool, 'number': (int, float), 'string': str}


def option_kind(contents):
    """An option's value type: its declared contents.type, else the type of its default."""
    if contents.get('type'):
        return contents['type']
    return {bool: 'boolean', int: 'number', float: 'number', str: 'string'}.get(type(contents.get('value')))


def option_types(module):
    """{url: value type} of a dependency: from this repository, or from the typed fixture."""
    if (ROOT / module / 'options.yml').is_file():
        found = {}

        def walk(items):
            for item in items:
                if 'url' in item:
                    found[item['url']] = option_kind(item.get('contents', {}))
                walk(item.get('children', []))

        walk(load(ROOT / module / 'options.yml')['options'])
        return found
    return dict(load(FIXTURE)[module]['options'])


def suggestions(name):
    """{url: contents} for a plugin's config.yml, or None when it has none."""
    path = ROOT / name / 'config.yml'
    if not path.exists():
        return None
    sparse = load(path)['config-sparse']
    found = {}

    def walk(node, path):
        if 'contents' in node:
            found['.'.join(path)] = node['contents']
            return
        for key, child in node.items():
            walk(child, (*path, key))

    for module, entry in sparse['modules'].items():
        walk(entry['config'], (module,))
    for plugin, entry in sparse.get('plugins', {}).items():
        walk(entry['config'], (plugin,))
    return found


class FixesPluginTests(unittest.TestCase):
    def test_plugin_depends_on_the_neutral_fix_modules(self):
        fixes = definition(FIXES)
        self.assertEqual((fixes['type'], fixes['version'], fixes['display-name']),
                         ('plugin', '0.2.0', 'UCP3 Fixes'))
        self.assertNotIn('family', fixes)
        self.assertEqual(fixes['dependencies'], FIXES_DEPENDENCIES)
        self.assertNotIn('smarter-gatehouses', fixes['dependencies'])
        self.assertFalse((ROOT / FIXES / 'init.lua').exists())
        for name in FIXES_DEPENDENCIES:
            if (ROOT / name / 'definition.yml').is_file():
                member = definition(name)
                self.assertEqual(f"^{member['version']}", FIXES_DEPENDENCIES[name], name)
                self.assertNotIn('family', member)

    def test_plugin_turns_on_exactly_the_listed_fixes(self):
        found = suggestions(FIXES)
        self.assertEqual(set(found), FIXES_SUGGESTED)
        for url, contents in found.items():
            self.assertEqual(set(contents), {'suggested-value'}, url)
            self.assertIs(contents['suggested-value'], True, url)


class SetupFamilyTests(unittest.TestCase):
    def test_exactly_one_family_root(self):
        roots, members = [], []
        for path in sorted(ROOT.glob('*/definition.yml')):
            for entry in load(path).get('family', []):
                self.assertEqual(entry['name'], FAMILY, path)
                self.assertIn(entry.get('root', False), (True, False), path)
                members.append(path.parent.name)
                if entry.get('root') is True:
                    roots.append(path.parent.name)
        self.assertEqual(roots, ['ucp3-basics'])
        self.assertEqual(sorted(members), sorted(MEMBERS))

    def test_members(self):
        for name, expected in MEMBERS.items():
            with self.subTest(member=name):
                member = definition(name)
                self.assertEqual((member['name'], member['type'], member['version'], member['author'],
                                  member['display-name']),
                                 (name, 'plugin', '1.0.0', 'UCP contributors', expected['display']))
                self.assertEqual(member['family'], [{'name': FAMILY, 'root': True}] if expected['root']
                                 else [{'name': FAMILY}])
                self.assertEqual(member['tags'], expected['tags'])
                self.assertEqual(member['dependencies'],
                                 {'framework': '^3.0.7', 'frontend': FAMILY_FRONTEND, **expected['dependencies']})
                self.assertFalse((ROOT / name / 'init.lua').exists())

    def test_root_and_fixes_member_have_no_configuration_demands(self):
        # A dependency-only root never claims the family slot of a member that depends on it.
        self.assertIsNone(suggestions('ucp3-basics'))
        self.assertIsNone(suggestions('ucp3-basics-fixes'))
        self.assertFalse((ROOT / 'ucp3-basics' / 'options.yml').exists())

    def test_recommended_suggestions(self):
        found = suggestions('ucp3-recommended')
        self.assertEqual(set(found), MEMBERS['ucp3-recommended']['suggested'])
        for url, contents in found.items():
            self.assertEqual(set(contents), {'suggested-value'}, url)
            self.assertIs(contents['suggested-value'], True, url)


class PluginPackageTests(unittest.TestCase):
    def test_every_suggested_key_is_an_option_of_a_dependency_with_its_type(self):
        for name in PLUGINS:
            found = suggestions(name) or {}
            dependencies = definition(name)['dependencies']
            for url, contents in found.items():
                module = url.split('.', 1)[0]
                with self.subTest(plugin=name, url=url):
                    self.assertIn(module, dependencies)
                    types = option_types(module)
                    self.assertIn(url, types)
                    expected = PYTHON_TYPES[types[url]]
                    for value in contents.values():
                        self.assertIsInstance(value, expected)
                        if expected is not bool:  # bool is an int subclass; keep numbers numeric
                            self.assertNotIsInstance(value, bool)

    def test_fixture_names_its_source(self):
        for module, entry in load(FIXTURE).items():
            self.assertRegex(entry['source'], r'^https://github\.com/\S+ [0-9a-f]{40} options\.yml$', module)

    def test_locales_and_descriptions_in_all_languages(self):
        for name in PLUGINS:
            with self.subTest(plugin=name):
                folder = ROOT / name
                locales = {language: load(folder / 'locale' / f'{language}.yml') for language in LANGUAGES}
                keys = set(locales['en'])
                for language, locale in locales.items():
                    self.assertEqual(set(locale), keys, language)
                    self.assertTrue(all(isinstance(v, str) and v.strip() for v in locale.values()), language)
                    self.assertTrue((folder / 'locale' / f'description-{language}.md').read_text(encoding='utf-8')
                                    .startswith('# '), language)
                self.assertEqual((folder / 'description.md').read_bytes(),
                                 (folder / 'locale' / 'description-en.md').read_bytes())
                tags = definition(name).get('tags', [])
                self.assertEqual({k for k in keys if k.startswith('tags.')}, {f'tags.{t}' for t in tags})
                if name in MEMBERS:
                    self.assertEqual(locales['en']['family.ucp3'], 'UCP3')
                    self.assertEqual(locales['en']['family.ucp3.configuration'], MEMBERS[name]['label'])
                    self.assertTrue(all(locale['family.ucp3'] == 'UCP3' for locale in locales.values()))
                    self.assertEqual(keys, {'family.ucp3', 'family.ucp3.configuration', *(f'tags.{t}' for t in tags)})

    def test_packages_contain_metadata_and_no_code(self):
        spec = importlib.util.spec_from_file_location('build_modules', ROOT / 'tools/build_modules.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as output:
            for name in PLUGINS:
                with self.subTest(plugin=name):
                    folder = ROOT / name
                    self.assertTrue(builder.is_package(folder))
                    with zipfile.ZipFile(builder.build_module(folder, output)) as archive:
                        self.assertIsNone(archive.testzip())
                        self.assertIn('locale/', archive.namelist())
                        files = {n for n in archive.namelist() if not n.endswith('/')}
                        expected = {'definition.yml', 'description.md', 'CREDITS.md',
                                    *(f'locale/{l}.yml' for l in LANGUAGES),
                                    *(f'locale/description-{l}.md' for l in LANGUAGES)}
                        if (folder / 'config.yml').exists():
                            expected.add('config.yml')
                        self.assertEqual(files, expected)
                        self.assertEqual(load(folder / 'definition.yml'), yaml.safe_load(archive.read('definition.yml')))


if __name__ == '__main__':
    unittest.main()
