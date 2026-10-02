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
EXTERNAL_DEPENDENCIES = {'smarter-gatehouses': '^1.0.3'}
LANGUAGES = ('de', 'en', 'fr', 'ru', 'hu', 'tr', 'ch', 'es', 'fa')


class FixesFamilyTests(unittest.TestCase):
    def test_root_selects_internal_and_external_fixes_without_copying_code(self):
        definitions = {
            name: yaml.safe_load((ROOT / name / 'definition.yml').read_text(encoding='utf-8'))
            for name in (FAMILY, *MEMBERS)
        }
        root = definitions[FAMILY]
        self.assertEqual(root['type'], 'module')
        self.assertNotIn('family', root)
        self.assertEqual(set(root['dependencies']) - {'frontend', 'framework'},
                         set(MEMBERS) | set(EXTERNAL_DEPENDENCIES))
        for name, version in EXTERNAL_DEPENDENCIES.items():
            self.assertEqual(root['dependencies'][name], version)
        self.assertFalse((ROOT / FAMILY / 'config.yml').exists())
        for name in MEMBERS:
            member = definitions[name]
            self.assertNotIn('family', member)
            if name in ('worker-delivery-fix', 'gatehouse-capture-fix', 'hunter-targeting-fix'):
                self.assertIn('bugfixes', member['tags'])
            self.assertEqual(root['dependencies'][name], f"^{member['version']}")
            option = yaml.safe_load((ROOT / name / 'options.yml').read_text(encoding='utf-8'))['options'][0]
            self.assertIs(option['contents']['value'], True)
            self.assertEqual(option['category'], ['{{ai}}', '{{fixes}}']
                             if name == 'hopfarm-limit-fix' else ['{{bugfixes}}'])

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
                for language in LANGUAGES:
                    self.assertTrue(archive.read(f'locale/description-{language}.md').decode('utf-8').strip())


if __name__ == '__main__':
    unittest.main()
