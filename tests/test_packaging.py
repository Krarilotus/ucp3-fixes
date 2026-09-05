"""Check packaged locale discovery, not just translation files in the checkout."""
import importlib.util
import re
import tempfile
import unittest
import zipfile

import yaml
from test_modules import ROOT, FIXTURES

spec = importlib.util.spec_from_file_location('build_modules', ROOT / 'tools/build_modules.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
LANGUAGES = ('de', 'en', 'fr', 'ru', 'hu', 'tr', 'ch', 'es', 'fa')


class PackagingTests(unittest.TestCase):
    def test_all_frontend_languages_are_discoverable_inside_zip(self):
        with tempfile.TemporaryDirectory() as output:
            for name in FIXTURES:
                with self.subTest(module=name), zipfile.ZipFile(builder.build_module(ROOT / name, output)) as archive:
                    self.assertIsNone(archive.testzip())
                    # readLocales checks this exact entry before loading any .yml.
                    self.assertIn('locale/', archive.namelist())
                    keys = {k.lower() for k in re.findall(r'{{(.*?)}}', archive.read('options.yml').decode('utf-8'))}
                    for language in LANGUAGES:
                        locale = yaml.safe_load(archive.read(f'locale/{language}.yml'))
                        lowered = {k.lower(): v for k, v in locale.items()}
                        self.assertTrue(keys <= lowered.keys(), (name, language, keys - lowered.keys()))
                        self.assertTrue(all(isinstance(v, str) and v.strip() and '{{' not in v for v in lowered.values()))
                        self.assertTrue(archive.read(f'locale/description-{language}.md').decode('utf-8').strip())
                    self.assertEqual(archive.read('description.md'), archive.read('locale/description-en.md'))

    def test_tryout_changes_only_display_name(self):
        with tempfile.TemporaryDirectory() as output:
            for name in FIXTURES:
                folder = ROOT / name
                with zipfile.ZipFile(builder.build_module(folder, output, True)) as archive:
                    original = yaml.safe_load((folder / 'definition.yml').read_text(encoding='utf-8'))
                    installed = yaml.safe_load(archive.read('definition.yml'))
                    self.assertEqual(installed.pop('display-name'), original.pop('display-name') + ' (Local try-out)')
                    self.assertEqual(installed, original)
                    for entry in archive.infolist():
                        if not entry.is_dir() and entry.filename != 'definition.yml':
                            self.assertEqual(archive.read(entry), (folder / entry.filename).read_bytes())


if __name__ == '__main__': unittest.main()
