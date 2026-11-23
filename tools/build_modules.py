"""Build unsigned module and plugin ZIPs, including directory entries.

Modules follow their files.yml. A plugin without files.yml is packaged with its
whole folder, as the Store's build-plugin.ps1 does.

Usage: python tools/build_modules.py --output /path/to/packages
"""
import argparse
from pathlib import Path
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]


def build_module(folder, output):
    folder, output = Path(folder).resolve(), Path(output)
    definition = yaml.safe_load((folder / 'definition.yml').read_text(encoding='utf-8'))
    if (folder / 'files.yml').is_file():
        manifest = yaml.safe_load((folder / 'files.yml').read_text(encoding='utf-8'))['files']
    elif definition.get('type') == 'plugin':
        manifest = [{'src': path.name} for path in sorted(folder.iterdir())]
    else:
        raise ValueError('A module needs files.yml: ' + str(folder))
    entries = {}
    directories = set()
    for entry in manifest:
        item = (folder / entry['src']).resolve()
        if not item.is_relative_to(folder) or not item.exists():
            raise ValueError('Invalid package input: ' + entry['src'])
        for path in ([item] + sorted(item.rglob('*')) if item.is_dir() else [item]):
            relative = path.relative_to(folder)
            for parent in relative.parents:
                if parent != Path('.'): directories.add(parent.as_posix() + '/')
            if path.is_dir():
                directories.add(relative.as_posix() + '/')
            else:
                entries[relative.as_posix()] = path.read_bytes()
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{definition['name']}-{definition['version']}.zip"
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        # The frontend probes locale/ by its exact ZIP entry name before reading
        # any translations. Having locale/en.yml alone does not satisfy that probe.
        for directory in sorted(directories):
            archive.writestr(directory, b'')
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)
    return target


def is_package(folder):
    """A module with files.yml or a plugin folder."""
    if (folder / 'files.yml').is_file():
        return True
    return yaml.safe_load((folder / 'definition.yml').read_text(encoding='utf-8')).get('type') == 'plugin'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    for definition in sorted(ROOT.glob('*/definition.yml')):
        if is_package(definition.parent):
            print(build_module(definition.parent, args.output))
