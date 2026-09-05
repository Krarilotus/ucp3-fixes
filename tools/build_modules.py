"""Build unsigned module ZIPs from files.yml, including directory entries.

Usage: python tools/build_modules.py --output /path/to/packages [--local-tryout]
"""
import argparse
from pathlib import Path
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]


def build_module(folder, output, local_tryout=False):
    folder, output = Path(folder).resolve(), Path(output)
    definition = yaml.safe_load((folder / 'definition.yml').read_text(encoding='utf-8'))
    manifest = yaml.safe_load((folder / 'files.yml').read_text(encoding='utf-8'))['files']
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
    if local_tryout:
        definition['display-name'] += ' (Local try-out)'
        entries['definition.yml'] = yaml.safe_dump(definition, allow_unicode=True, sort_keys=False).encode('utf-8')
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--local-tryout', action='store_true')
    args = parser.parse_args()
    for definition in sorted(ROOT.glob('*/definition.yml')):
        if (definition.parent / 'files.yml').is_file():
            print(build_module(definition.parent, args.output, args.local_tryout))
