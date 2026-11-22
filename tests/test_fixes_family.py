"""The optional bundle selects existing fixes without copying their code."""

from pathlib import Path
import importlib.util
import tempfile
import unittest
import zipfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'ucp3-fixes'
MEMBERS = ('worker-delivery-fix', 'gatehouse-capture-fix', 'hunter-targeting-fix',
           'fixed-engineers', 'hopfarm-limit-fix')
EXTERNAL_DEPENDENCIES = {'smarter-gatehouses': '^1.0.4'}
# Bundle 0.1.4 keeps selecting the released default-on modules; the off-by-default
# modules got new minor versions, which its caret ranges do not accept.
RELEASED = {'worker-delivery-fix': ('^0.1.2', '0.1.'), 'gatehouse-capture-fix': ('^0.1.2', '0.1.'),
            'hunter-targeting-fix': ('^0.1.2', '0.1.'), 'fixed-engineers': ('^0.2.2', '0.2.'),
            'hopfarm-limit-fix': ('^0.1.4', '0.1.')}
LANGUAGES = ('de', 'en', 'fr', 'ru', 'hu', 'tr', 'ch', 'es', 'fa')


class FixesFamilyTests(unittest.TestCase):
    def test_root_selects_internal_and_external_fixes_without_copying_code(self):
        definitions = {
            name: yaml.safe_load((ROOT / name / 'definition.yml').read_text(encoding='utf-8'))
            for name in (FAMILY, *MEMBERS)
        }
        root = definitions[FAMILY]
        self.assertEqual(root['type'], 'module')
        self.assertEqual(root['family'], [{'name': FAMILY, 'root': True}])
        self.assertEqual(set(root['dependencies']) - {'frontend', 'framework'},
                         set(MEMBERS) | set(EXTERNAL_DEPENDENCIES))
        for name, version in EXTERNAL_DEPENDENCIES.items():
            self.assertEqual(root['dependencies'][name], version)
        for name in MEMBERS:
            member = definitions[name]
            self.assertNotIn('family', member)
            if name in ('worker-delivery-fix', 'gatehouse-capture-fix', 'hunter-targeting-fix'):
                self.assertIn('bugfixes', member['tags'])
            pinned, released_prefix = RELEASED[name]
            self.assertEqual(root['dependencies'][name], pinned)
            self.assertFalse(member['version'].startswith(released_prefix), name)
            option = yaml.safe_load((ROOT / name / 'options.yml').read_text(encoding='utf-8'))['options'][0]
            self.assertIs(option['contents']['value'], False)
            self.assertEqual(option['category'], ['{{ai}}', '{{fixes}}']
                             if name == 'hopfarm-limit-fix' else ['{{bugfixes}}'])

    def test_recommended_preset_suggests_every_member_option_default(self):
        preset = yaml.safe_load((ROOT / FAMILY / 'config.yml').read_text(encoding='utf-8'))
        sparse = preset['config-sparse']
        self.assertEqual(sparse['plugins'], {})
        self.assertEqual(set(sparse['modules']), set(MEMBERS) | set(EXTERNAL_DEPENDENCIES))

        def suggested(node, path=()):
            if 'contents' in node:
                yield '.'.join(path), node['contents']
                return
            for key, child in node.items():
                yield from suggested(child, (*path, key))

        for name in MEMBERS:
            options = yaml.safe_load((ROOT / name / 'options.yml').read_text(encoding='utf-8'))['options']
            urls = [option['url'].split('.', 1)[1] for option in options]
            # The modules default to off; the bundle suggests every fix on.
            self.assertEqual(dict(suggested(sparse['modules'][name]['config'])),
                             {url: {'suggested-value': True} for url in urls})
            self.assertTrue(all(option['contents']['value'] is False for option in options))
        gatehouses = dict(suggested(sparse['modules']['smarter-gatehouses']['config']))
        self.assertEqual(gatehouses, {
            'pathing.enemy_gates_closed': {'suggested-value': True},
            'detection.centred': {'suggested-value': True},
            'detection.reachable_only': {'suggested-value': True},
            'walls.stairs_needed': {'suggested-value': False},
            'walls.stairs_needed_ai': {'suggested-value': False},
        })

    def test_root_package_has_localized_description_and_no_fix_code(self):
        spec = importlib.util.spec_from_file_location('build_modules', ROOT / 'tools/build_modules.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as output:
            with zipfile.ZipFile(builder.build_module(ROOT / FAMILY, output)) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn('locale/', archive.namelist())
                self.assertEqual(archive.read('description.md'), archive.read('locale/description-en.md'))
                self.assertEqual([name for name in archive.namelist() if name.endswith('.lua')], ['init.lua'])
                self.assertEqual(yaml.safe_load(archive.read('config.yml')),
                                 yaml.safe_load((ROOT / FAMILY / 'config.yml').read_text(encoding='utf-8')))
                for language in LANGUAGES:
                    self.assertTrue(archive.read(f'locale/description-{language}.md').decode('utf-8').strip())


if __name__ == '__main__':
    unittest.main()
