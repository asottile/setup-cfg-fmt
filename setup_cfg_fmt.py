import argparse
import configparser
import glob
import io
import os.path
import re
from typing import Dict
from typing import Match
from typing import Optional
from typing import Sequence
from typing import Tuple

from identify import identify


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


LICENSE_TO_CLASSIFIER = {
    '0BSD': 'License :: OSI Approved :: BSD License',
    'AFL-3.0': 'License :: OSI Approved :: Academic Free License (AFL)',
    'AGPL-3.0': 'License :: OSI Approved :: GNU Affero General Public License v3',  # noqa: E501
    'Apache-2.0': 'License :: OSI Approved :: Apache Software License',
    'Artistic-2.0': 'License :: OSI Approved :: Artistic License',
    'BSD-2-Clause': 'License :: OSI Approved :: BSD License',
    'BSD-3-Clause': 'License :: OSI Approved :: BSD License',
    'BSD-3-Clause-Clear': 'License :: OSI Approved :: BSD License',
    'BSL-1.0': 'License :: OSI Approved :: Boost Software License 1.0 (BSL-1.0)',  # noqa: E501
    'CC0-1.0': 'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',  # noqa: E501
    'EPL-1.0': 'License :: OSI Approved :: Eclipse Public License 1.0 (EPL-1.0)',  # noqa: E501
    'EPL-2.0': 'License :: OSI Approved :: Eclipse Public License 2.0 (EPL-2.0)',  # noqa: E501
    'EUPL-1.1': 'License :: OSI Approved :: European Union Public Licence 1.1 (EUPL 1.1)',  # noqa: E501
    'EUPL-1.2': 'License :: OSI Approved :: European Union Public Licence 1.2 (EUPL 1.2)',  # noqa: E501
    'GPL-2.0': 'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',  # noqa: E501
    'GPL-3.0': 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',  # noqa: E501
    'ISC': 'License :: OSI Approved :: ISC License (ISCL)',
    'LGPL-2.1': 'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',  # noqa: E501
    'LGPL-3.0': 'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',  # noqa: E501
    'MIT': 'License :: OSI Approved :: MIT License',
    'MPL-2.0': 'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',  # noqa: E501
    'NCSA': 'License :: OSI Approved :: University of Illinois/NCSA Open Source License',  # noqa: E501
    'OFL-1.1': 'License :: OSI Approved :: SIL Open Font License 1.1 (OFL-1.1)',  # noqa: E501
    'PostgreSQL': 'License :: OSI Approved :: PostgreSQL License',
    'UPL-1.0': 'License :: OSI Approved :: Universal Permissive License (UPL)',
    'Zlib': 'License :: OSI Approved :: zlib/libpng License',
}


def _adjacent_filename(setup_cfg: str, filename: str) -> str:
    return os.path.join(os.path.dirname(setup_cfg), filename)


GLOB_PART = re.compile(r'(\[[^]]+\]|.)')


def _case_insensitive_glob(s: str) -> str:
    def cb(match: Match[str]) -> str:
        match_s = match.group()
        if len(match_s) == 1:
            return f'[{match_s.upper()}{match_s.lower()}]'
        else:
            inner = ''.join(f'{c.upper()}{c.lower()}' for c in match_s[1:-1])
            return f'[{inner}]'

    return GLOB_PART.sub(cb, s)


def _first_file(setup_cfg: str, prefix: str) -> Optional[str]:
    prefix = _case_insensitive_glob(prefix)
    path = _adjacent_filename(setup_cfg, prefix)
    for filename in glob.iglob(f'{path}*'):
        return filename
    else:
        return None


def format_file(filename: str) -> bool:
    with open(filename) as f:
        contents = f.read()

    cfg = configparser.ConfigParser()
    cfg.read_string(contents)

    # normalize names to underscores so sdist / wheel have the same prefix
    cfg['metadata']['name'] = cfg['metadata']['name'].replace('-', '_')

    # if README.md exists, set `long_description` + content type
    readme = _first_file(filename, 'readme')
    if readme is not None:
        long_description = f'file: {os.path.basename(readme)}'
        cfg['metadata']['long_description'] = long_description

        tags = identify.tags_from_filename(readme)
        if 'markdown' in tags:
            cfg['metadata']['long_description_content_type'] = 'text/markdown'
        elif 'rst' in tags:
            cfg['metadata']['long_description_content_type'] = 'text/x-rst'
        else:
            cfg['metadata']['long_description_content_type'] = 'text/plain'

    # set license fields if a license exists
    license_filename = _first_file(filename, 'licen[sc]e')
    if license_filename is not None:
        cfg['metadata']['license_file'] = os.path.basename(license_filename)

        license_id = identify.license_id(license_filename)
        if license_id is not None:
            cfg['metadata']['license'] = license_id

        if license_id in LICENSE_TO_CLASSIFIER:
            cfg['metadata']['classifiers'] = (
                cfg['metadata'].get('classifiers', '').rstrip() +
                f'\n{LICENSE_TO_CLASSIFIER[license_id]}'
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
