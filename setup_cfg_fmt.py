import argparse
import configparser
import glob
import io
import os.path
import re
import string
from typing import Dict
from typing import Generator
from typing import List
from typing import Match
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple

from identify import identify

Version = Tuple[int, ...]

KEYS_ORDER: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        'metadata', (
            'name', 'version', 'description',
            'long_description', 'long_description_content_type',
            'url',
            'author', 'author_email', 'maintainer', 'maintainer_email',
            'license', 'license_file', 'license_files',
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

TOX_TO_CLASSIFIERS = {
    'py': 'Programming Language :: Python :: Implementation :: CPython',
    'pypy': 'Programming Language :: Python :: Implementation :: PyPy',
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
    for filename in sorted(glob.iglob(f'{path}*')):
        if os.path.isfile(filename):
            return filename
    else:
        return None


def _py3_excluded(min_py3_version: Tuple[int, int]) -> Set[Tuple[int, int]]:
    _, end = min_py3_version
    return {(3, i) for i in range(end)}


def _format_python_requires(minimum: Version, excluded: Set[Version]) -> str:
    return ', '.join((
        f'>={_v(minimum)}', *(f'!={_v(v)}.*' for v in sorted(excluded)),
    ))


class UnknownVersionError(ValueError):
    pass


def _to_ver(s: str) -> Version:
    parts = [part for part in s.split('.') if part != '*']
    if len(parts) < 2:
        raise UnknownVersionError()
    else:
        return tuple(int(part) for part in parts)


def _v(x: Version) -> str:
    return '.'.join(str(p) for p in x)


def _parse_python_requires(
        python_requires: Optional[str],
) -> Tuple[Optional[Version], Set[Version]]:
    minimum = None
    excluded = set()

    if python_requires:
        for part in python_requires.split(','):
            part = part.strip()
            if part.startswith('>='):
                minimum = _to_ver(part[2:])
            elif part.startswith('!='):
                excluded.add(_to_ver(part[2:]))
            else:
                raise UnknownVersionError()

    return minimum, excluded


def _tox_envlist(setup_cfg: str) -> Generator[str, None, None]:
    tox_ini = _adjacent_filename(setup_cfg, 'tox.ini')
    if os.path.exists(tox_ini):
        cfg = configparser.ConfigParser()
        cfg.read(tox_ini)

        envlist = cfg.get('tox', 'envlist', fallback='')
        if envlist:
            for env in envlist.split(','):
                env, _, _ = env.strip().partition('-')  # py36-foo
                yield env


def _python_requires(
        setup_cfg: str, *, min_py3_version: Tuple[int, int],
) -> Optional[str]:
    cfg = configparser.ConfigParser()
    cfg.read(setup_cfg)
    current_value = cfg.get('options', 'python_requires', fallback='')
    classifiers = cfg.get('metadata', 'classifiers', fallback='')

    try:
        minimum, excluded = _parse_python_requires(current_value)
    except UnknownVersionError:  # assume they know what's up with weird things
        return current_value

    for env in _tox_envlist(setup_cfg):
        if (
                env.startswith('py') and
                len(env) == 4 and
                env[2:].isdigit()
        ):
            version = _to_ver('.'.join(env[2:]))
            if minimum is None or version < minimum[:2]:
                minimum = version

    for classifier in classifiers.strip().splitlines():
        if classifier.startswith('Programming Language :: Python ::'):
            version_part = classifier.split()[-1]
            if '.' not in version_part:
                continue
            version = _to_ver(version_part)
            if minimum is None or version < minimum[:2]:
                minimum = version

    if minimum is None:
        return None
    elif minimum[0] == 2:
        excluded.update(_py3_excluded(min_py3_version))
        return _format_python_requires(minimum, excluded)
    elif min_py3_version > minimum:
        return _format_python_requires(min_py3_version, excluded)
    else:
        return _format_python_requires(minimum, excluded)


def _requires(
        cfg: configparser.ConfigParser, which: str, section: str = 'options',
) -> List[str]:
    raw = cfg.get(section, which, fallback='')

    require_group = raw.strip().splitlines()
    if not require_group:
        return []

    normalized = sorted(
        (_normalize_req(req) for req in require_group),
        key=lambda req: (';' in req, _req_base(req), req),
    )
    normalized.insert(0, '')
    return normalized


def _normalize_req(req: str) -> str:
    lib, _, envs = req.partition(';')
    normalized = _normalize_lib(lib)

    envs = envs.strip()
    if not envs:
        return normalized

    return f'{normalized};{envs}'


BASE_NAME_REGEX = re.compile(r'[^!=><\s@]+')
REQ_REGEX = re.compile(r'(===|==|!=|~=|>=?|<=?|@)\s*([^,]+)')


def _normalize_lib(lib: str) -> str:
    base = _req_base(lib)

    conditions = ','.join(
        sorted(
            (
                f'{m.group(1)}{m.group(2)}'
                for m in REQ_REGEX.finditer(lib)
            ),
            key=lambda c: ('<' in c, '>' in 'c', c),
        ),
    )

    return f'{base}{conditions}'


def _req_base(lib: str) -> str:
    basem = re.match(BASE_NAME_REGEX, lib)
    assert basem
    return basem.group(0)


def _py_classifiers(
        python_requires: Optional[str], *, max_py_version: Tuple[int, int],
) -> Optional[str]:
    try:
        minimum, exclude = _parse_python_requires(python_requires)
    except UnknownVersionError:
        return None

    if minimum is None:  # don't have a sequence of versions to iterate over
        return None
    else:
        # classifiers only use the first two segments of version
        minimum = minimum[:2]

    versions: Set[Version] = set()
    while minimum <= max_py_version:
        if minimum not in exclude:
            versions.add(minimum)
            versions.add(minimum[:1])
        if minimum == (2, 7):
            minimum = (3, 0)
        else:
            minimum = (minimum[0], minimum[1] + 1)

    classifiers = [
        f'Programming Language :: Python :: {_v(v)}' for v in versions
    ]
    if (3,) in versions and (2,) not in versions:
        classifiers.append('Programming Language :: Python :: 3 :: Only')

    return '\n'.join(classifiers)


def _trim_py_classifiers(
        classifiers: List[str],
        python_requires: Optional[str],
        *,
        max_py_version: Tuple[int, int],
) -> List[str]:
    try:
        minimum, exclude = _parse_python_requires(python_requires)
    except UnknownVersionError:
        return classifiers

    def _is_ok_classifier(s: str) -> bool:
        parts = s.split(' :: ')
        if (
                # can't know if it applies without a minimum
                minimum is None or
                # handle Python :: 3 :: Only
                len(parts) != 3 or
                not s.startswith('Programming Language :: Python :: ')
        ):
            return True

        ver = tuple(int(p) for p in parts[-1].strip().split('.'))
        size = len(ver)
        return (
            ver not in exclude and
            minimum[:size] <= ver <= max_py_version[:size]
        )

    return [s for s in classifiers if _is_ok_classifier(s)]


def _imp_classifiers(setup_cfg: str) -> str:
    classifiers = set()

    for env in _tox_envlist(setup_cfg):
        # remove trailing digits: py39-django31
        classifier = TOX_TO_CLASSIFIERS.get(env.rstrip(string.digits))
        if classifier is not None:
            classifiers.add(classifier)

    return '\n'.join(sorted(classifiers))


def format_file(
        filename: str, *,
        min_py3_version: Tuple[int, int],
        max_py_version: Tuple[int, int],
) -> bool:
    with open(filename) as f:
        contents = f.read()

    cfg = configparser.ConfigParser()
    cfg.read_string(contents)
    _clean_sections(cfg)

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

    requires = _python_requires(filename, min_py3_version=min_py3_version)
    if requires is not None:
        if not cfg.has_section('options'):
            cfg.add_section('options')
        cfg['options']['python_requires'] = requires

    install_requires = _requires(cfg, 'install_requires')
    if install_requires:
        cfg['options']['install_requires'] = '\n'.join(install_requires)

    setup_requires = _requires(cfg, 'setup_requires')
    if setup_requires:
        cfg['options']['setup_requires'] = '\n'.join(setup_requires)

    if cfg.has_section('options.extras_require'):
        for key in cfg['options.extras_require']:
            group_requires = _requires(cfg, key, 'options.extras_require')
            cfg['options.extras_require'][key] = '\n'.join(group_requires)

    py_classifiers = _py_classifiers(requires, max_py_version=max_py_version)
    if py_classifiers:
        cfg['metadata']['classifiers'] = (
            cfg['metadata'].get('classifiers', '').rstrip() +
            f'\n{py_classifiers}'
        )

    imp_classifiers = _imp_classifiers(filename)
    if imp_classifiers:
        cfg['metadata']['classifiers'] = (
            cfg['metadata'].get('classifiers', '').rstrip() +
            f'\n{imp_classifiers}'
        )

    # sort the classifiers if present
    if 'classifiers' in cfg['metadata']:
        classifiers = sorted(set(cfg['metadata']['classifiers'].split('\n')))
        classifiers = _trim_py_classifiers(
            classifiers, requires, max_py_version=max_py_version,
        )
        cfg['metadata']['classifiers'] = '\n'.join(classifiers)

    sections: Dict[str, Dict[str, str]] = {}
    for section, key_order in KEYS_ORDER:
        if section not in cfg:
            continue

        entries = {k.replace('-', '_'): v for k, v in cfg[section].items()}

        new_section = {k: entries.pop(k) for k in key_order if k in entries}
        # sort any remaining keys
        new_section.update(sorted(entries.items()))

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


def _clean_sections(cfg: configparser.ConfigParser) -> None:
    """Removes any empty options and sections."""
    for section in cfg.sections():
        new_options = {k: v for k, v in cfg[section].items() if v}
        if new_options:
            cfg[section] = new_options
        else:
            cfg.pop(section)


def _ver_type(s: str) -> Version:
    try:
        version = _to_ver(s)
    except UnknownVersionError:
        version = ()

    if len(version) != 2:
        raise argparse.ArgumentTypeError(f'expected #.#, got {s!r}')
    else:
        return version


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    parser.add_argument('--min-py3-version', type=_ver_type, default=(3, 6))
    parser.add_argument('--max-py-version', type=_ver_type, default=(3, 9))
    args = parser.parse_args(argv)

    retv = 0
    for filename in args.filenames:
        if format_file(
                filename,
                min_py3_version=args.min_py3_version,
                max_py_version=args.max_py_version,
        ):
            print(f'Rewriting {filename}')
            retv = 1
    return retv


if __name__ == '__main__':
    exit(main())
