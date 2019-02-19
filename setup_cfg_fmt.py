import argparse
import configparser
import io
import os.path
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Tuple

KEYS_ORDER: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        'metadata', (
            'name', 'version', 'description',
            'long_description', 'long_description_content_type',
            'url', 'author', 'author_email', 'license', 'license_file',
            'platforms', 'classifiers',
        ),
    ),
    (
        'options', (
            'packages', 'py_modules', 'install_requires', 'python_requires',
        ),
    ),
    ('options.sections.find', ('where', 'exclude', 'include')),
    ('options.entry_points', ('console_scripts',)),
    ('options.extras_require', ()),
    ('options.package_data', ()),
    ('options.exclude_package_data', ()),
)


def _adjacent_filename(setup_cfg: str, filename: str) -> str:
    return os.path.join(os.path.dirname(setup_cfg), filename)


def format_file(filename: str) -> bool:
    with open(filename) as f:
        contents = f.read()

    cfg = configparser.ConfigParser()
    cfg.read_string(contents)

    # normalize names to underscores so sdist / wheel have the same prefix
    cfg['metadata']['name'] = cfg['metadata']['name'].replace('-', '_')

    # if README.md exists, set `long_description` + content type
    if os.path.exists(_adjacent_filename(filename, 'README.md')):
        cfg['metadata']['long_description'] = 'file: README.md'
        cfg['metadata']['long_description_content_type'] = 'text/markdown'

    # set license fields if a license exists
    license_filename = _adjacent_filename(filename, 'LICENSE')
    if os.path.exists(license_filename):
        cfg['metadata']['license_file'] = 'LICENSE'

        with open(license_filename) as f:
            license_s = f.read()

        # TODO: pick a better way to identify licenses
        if 'Permission is hereby granted, free of charge, to any' in license_s:
            cfg['metadata']['license'] = 'MIT'
            cfg['metadata']['classifiers'] = (
                cfg['metadata'].get('classifiers', '').rstrip() +
                '\nLicense :: OSI Approved :: MIT License'
            )

    # sort the classifiers if present
    if 'classifiers' in cfg['metadata']:
        classifiers = sorted(set(cfg['metadata']['classifiers'].split('\n')))
        cfg['metadata']['classifiers'] = '\n'.join(classifiers)

    sections: Dict[str, Dict[str, str]] = {}
    for section, key_order in KEYS_ORDER:
        if section not in cfg:
            continue

        new_section = {
            k: cfg[section].pop(k) for k in key_order if k in cfg[section]
        }
        # sort any remaining keys
        new_section.update(sorted(cfg[section].items()))

        sections[section] = new_section
        cfg.pop(section)

    for section in cfg.sections():
        sections[section] = dict(cfg[section])
        cfg.pop(section)

    for k, v in sections.items():
        cfg[k] = v

    sio = io.StringIO()
    cfg.write(sio)
    new_contents = sio.getvalue().strip() + '\n'
    new_contents = new_contents.replace('\t', '    ')
    new_contents = new_contents.replace(' \n', '\n')

    if new_contents != contents:
        with open(filename, 'w') as f:
            f.write(new_contents)

    return new_contents != contents


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    retv = 0
    for filename in args.filenames:
        if format_file(filename):
            retv = 1
            print(f'Rewriting {filename}')

    return retv


if __name__ == '__main__':
    exit(main())
