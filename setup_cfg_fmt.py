from __future__ import annotations

import argparse
import configparser
import glob
import io
import os.path
import re
import string
import sys
from collections.abc import Generator
from collections.abc import Sequence
from re import Match

from identify import identify

Version = tuple[int, ...]

KEYS_ORDER: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        'metadata', (
            'name', 'version', 'description',
            'long_description', 'long_description_content_type',
            'url',
            'author', 'author_email', 'maintainer', 'maintainer_email',
            'license', 'license_files',
            'platforms', 'classifiers',
        ),
    ),
    (
        'options', (
            'packages', 'py_modules', 'install_requires', 'python_requires',
        ),
    ),
    ('options.packages.find', ('where', 'exclude', 'include')),
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


class NoTransformConfigParser(configparser.RawConfigParser):
    def optionxform(self, s: str) -> str:
        """disable default lower-casing"""
        return s


def _adjacent_filename(setup_cfg: str, filename: str) -> str:
    return os.path.join(os.path.dirname(setup_cfg), filename)


GLOB_PART = re.compile(r'(\[[^]]+\]|.)')


def _case_insensitive_glob(s: str) -> str:
    def cb(match: Match[str]) -> str:
        match_s = match[0]
        if len(match_s) == 1:
            return f'[{match_s.upper()}{match_s.lower()}]'
        else:
            inner = ''.join(f'{c.upper()}{c.lower()}' for c in match_s[1:-1])
            return f'[{inner}]'

    return GLOB_PART.sub(cb, s)


def _first_file(setup_cfg: str, prefix: str) -> str | None:
    prefix = _case_insensitive_glob(prefix)
    path = _adjacent_filename(setup_cfg, prefix)

    # prefer non-asciidoc because pypi does not render it
    # https://github.com/asottile/setup-cfg-fmt/issues/149
    def sort_key(filename: str) -> tuple[bool, str]:
        return (filename.endswith(('.adoc', '.asciidoc')), filename)

    for filename in sorted(glob.iglob(f'{path}*'), key=sort_key):
        if os.path.isfile(filename):
            return filename
    else:
        return None


def _parse_list(s: str) -> list[str]:
    return s.strip().splitlines()


def _fmt_list_always(items: list[str]) -> str:
    return '\n'.join(('', *items))


def _fmt_list(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    else:
        return _fmt_list_always(items)


def _format_python_requires(minimum: Version, excluded: set[Version]) -> str:
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
        python_requires: str | None,
) -> tuple[Version | None, set[Version]]:
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


def _tox_envlist(setup_cfg: str) -> Generator[str]:
    tox_ini = _adjacent_filename(setup_cfg, 'tox.ini')
    if os.path.exists(tox_ini):
        cfg = NoTransformConfigParser()
        cfg.read(tox_ini)

        envlist = cfg.get('tox', 'envlist', fallback='')
        if envlist:
            for env in envlist.split(','):
                env, _, _ = env.strip().partition('-')  # py36-foo
                yield env


TOX_ENV = re.compile(r'py3(\d+)')


def _python_requires(
        setup_cfg: str, *, min_py_version: tuple[int, int],
) -> str | None:
    cfg = NoTransformConfigParser()
    cfg.read(setup_cfg)
    current_value = cfg.get('options', 'python_requires', fallback='')
    classifiers = cfg.get('metadata', 'classifiers', fallback='')

    try:
        minimum, excluded = _parse_python_requires(current_value)
    except UnknownVersionError:  # assume they know what's up with weird things
        return current_value

    for env in _tox_envlist(setup_cfg):
        match = TOX_ENV.match(env)
        if match:
            version = _to_ver(f'3.{match[1]}')
            if minimum is None or version < minimum[:2]:
                minimum = version

    for classifier in _parse_list(classifiers):
        if classifier.startswith('Programming Language :: Python :: 3'):
            version_part = classifier.split()[-1]
            if '.' not in version_part:
                continue
            version = _to_ver(version_part)
            if minimum is None or version < minimum[:2]:
                minimum = version

    if minimum is None:
        return None
    elif min_py_version > minimum:
        return _format_python_requires(min_py_version, excluded)
    else:
        return _format_python_requires(minimum, excluded)


def _requires(
        cfg: NoTransformConfigParser, which: str, section: str = 'options',
) -> list[str]:
    raw = cfg.get(section, which, fallback='')

    require_group = _parse_list(raw)
    if not require_group:
        return []

    return sorted(
        (_normalize_req(req) for req in require_group),
        key=lambda req: (';' in req, _req_base(req), req),
    )


def _normalize_req(req: str) -> str:
    lib, _, envs = req.partition(';')
    normalized = _normalize_lib(lib)

    envs = envs.strip()
    if not envs:
        return normalized

    return f'{normalized};{envs}'


BASE_NAME_REGEX = re.compile(r'[^!=><\s@~]+')
REQ_REGEX = re.compile(r'(===|==|!=|~=|>=?|<=?|@)\s*([^,]+)')


def _normalize_lib(lib: str) -> str:
    base = _req_base(lib)

    conditions = ','.join(
        sorted(
            (f'{m[1]}{m[2]}' for m in REQ_REGEX.finditer(lib)),
            key=lambda c: ('<' in c, '>' in 'c', c),
        ),
    )

    return f'{base}{conditions}'


def _req_base(lib: str) -> str:
    basem = re.match(BASE_NAME_REGEX, lib)
    assert basem
    # pip replaces _ with - in package names
    return basem[0].replace('_', '-')


def _py_classifiers(
        python_requires: str | None, *, max_py_version: tuple[int, int],
) -> list[str]:
    try:
        minimum, exclude = _parse_python_requires(python_requires)
    except UnknownVersionError:
        return []

    if minimum is None:  # don't have a sequence of versions to iterate over
        return []
    else:
        # classifiers only use the first two segments of version
        minimum = minimum[:2]

    versions: set[Version] = set()
    while minimum <= max_py_version:
        if minimum not in exclude:
            versions.add(minimum)
            versions.add(minimum[:1])
        minimum = (minimum[0], minimum[1] + 1)

    classifiers = [
        f'Programming Language :: Python :: {_v(v)}' for v in versions
    ]
    classifiers.append('Programming Language :: Python :: 3 :: Only')

    return classifiers


def _trim_py_classifiers(
        classifiers: list[str],
        python_requires: str | None,
        *,
        include_version_classifiers: bool,
        max_py_version: tuple[int, int],
) -> list[str]:
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
            ver >= (3,) and ver not in exclude and (
                size == 1 or (
                    include_version_classifiers and
                    minimum[:size] <= ver <= max_py_version[:size]
                )
            )
        )

    return [s for s in classifiers if _is_ok_classifier(s)]


def _imp_classifiers(setup_cfg: str) -> list[str]:
    classifiers = set()

    for env in _tox_envlist(setup_cfg):
        # remove trailing digits: py39-django31
        classifier = TOX_TO_CLASSIFIERS.get(env.rstrip(string.digits))
        if classifier is not None:
            classifiers.add(classifier)

    return sorted(classifiers)


def _natural_sort(items: Sequence[str]) -> list[str]:
    return sorted(
        set(items),
        key=lambda s: [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r'(\d+)', s)
        ],
    )


def format_file(
        filename: str, *,
        include_version_classifiers: bool,
        min_py_version: tuple[int, int],
        max_py_version: tuple[int, int],
) -> bool:
    with open(filename) as f:
        contents = f.read()

    cfg = NoTransformConfigParser()
    cfg.read_string(contents)
    _clean_sections(cfg)

    # normalize names to underscores so sdist / wheel have the same prefix
    cfg['metadata']['name'] = cfg['metadata']['name'].replace('-', '_')

    # if README exists, set `long_description` + content type
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

    classifiers = _parse_list(cfg['metadata'].get('classifiers', ''))
    licenses = _parse_list(cfg['metadata'].get('license_files', ''))

    # combines license_file and license_files
    if 'license_file' in cfg['metadata']:
        licenses.append(cfg['metadata'].pop('license_file'))

    # set license fields if a license exists
    license_filename = _first_file(filename, 'licen[sc]e')
    if license_filename is not None:
        license_basename = os.path.basename(license_filename)
        licenses.append(license_basename)

        license_id = identify.license_id(license_filename)
        if license_id is not None:
            cfg['metadata']['license'] = license_id

        if license_id in LICENSE_TO_CLASSIFIER:
            classifiers.append(LICENSE_TO_CLASSIFIER[license_id])

    # sort license_files if it exists
    if licenses:
        cfg['metadata']['license_files'] = _fmt_list(sorted(set(licenses)))

    requires = _python_requires(filename, min_py_version=min_py_version)
    if requires is not None:
        if not cfg.has_section('options'):
            cfg.add_section('options')
        cfg['options']['python_requires'] = requires

    install_requires = _requires(cfg, 'install_requires')
    if install_requires:
        cfg['options']['install_requires'] = _fmt_list_always(install_requires)

    setup_requires = _requires(cfg, 'setup_requires')
    if setup_requires:
        cfg['options']['setup_requires'] = _fmt_list_always(setup_requires)

    if cfg.has_section('options.extras_require'):
        for key in cfg['options.extras_require']:
            cfg['options.extras_require'][key] = _fmt_list_always(
                _requires(cfg, key, 'options.extras_require'),
            )

    py_classifiers = _py_classifiers(requires, max_py_version=max_py_version)
    classifiers.extend(py_classifiers)
    classifiers.extend(_imp_classifiers(filename))

    # sort the classifiers if present
    if classifiers:
        classifiers = _trim_py_classifiers(
            _natural_sort(classifiers),
            requires,
            max_py_version=max_py_version,
            include_version_classifiers=include_version_classifiers,
        )
        cfg['metadata']['classifiers'] = _fmt_list_always(classifiers)

    sections: dict[str, dict[str, str]] = {}
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


def _clean_sections(cfg: NoTransformConfigParser) -> None:
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
    elif version[0] < 3:
        raise argparse.ArgumentTypeError(f'must be at least 3, got {s!r}')
    else:
        return version


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    parser.add_argument('--include-version-classifiers', action='store_true')
    parser.add_argument(
        '--min-py3-version', type=_ver_type, default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument('--min-py-version', type=_ver_type, default=(3, 9))
    parser.add_argument('--max-py-version', type=_ver_type, default=(3, 13))
    args = parser.parse_args(argv)

    if args.min_py3_version:
        print(
            'WARNING: setup-cfg-fmt will replace --min-py3-version '
            'with --min-py-version in a future release',
            file=sys.stderr,
        )
        min_py_version = args.min_py3_version
    else:
        min_py_version = args.min_py_version

    retv = 0
    for filename in args.filenames:
        if format_file(
                filename,
                include_version_classifiers=args.include_version_classifiers,
                min_py_version=min_py_version,
                max_py_version=args.max_py_version,
        ):
            print(f'Rewriting {filename}')
            retv = 1
    return retv


if __name__ == '__main__':
    raise SystemExit(main())
