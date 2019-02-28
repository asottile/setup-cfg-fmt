import argparse

import pytest

from setup_cfg_fmt import _case_insensitive_glob
from setup_cfg_fmt import _ver_type
from setup_cfg_fmt import main


def test_ver_type_ok():
    assert _ver_type('1.2') == (1, 2)


def test_ver_type_error():
    with pytest.raises(argparse.ArgumentTypeError) as excinfo:
        _ver_type('1.2.3')
    msg, = excinfo.value.args
    assert msg == "expected #.#, got '1.2.3'"


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('foo', '[Ff][Oo][Oo]'),
        ('FOO', '[Ff][Oo][Oo]'),
        ('licen[sc]e', '[Ll][Ii][Cc][Ee][Nn][SsCc][Ee]'),
    ),
)
def test_case_insensitive_glob(s, expected):
    assert _case_insensitive_glob(s) == expected


def test_noop(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        '\n'
        '[bdist_wheel]\n'
        'universal = true\n',
    )

    main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        '\n'
        '[bdist_wheel]\n'
        'universal = true\n'
    )


@pytest.mark.parametrize(
    ('input_s', 'expected'),
    (
        pytest.param(
            '[bdist_wheel]\n'
            'universal = true\n'
            '\n'
            '[metadata]\n'
            'version = 1.0\n'
            'name = pkg\n',

            '[metadata]\n'
            'name = pkg\n'
            'version = 1.0\n'
            '\n'
            '[bdist_wheel]\n'
            'universal = true\n',

            id='orders fields and sections',
        ),
        pytest.param(
            '[metadata]\n'
            'name = pkg-name\n'
            'version = 1.0\n',

            '[metadata]\n'
            'name = pkg_name\n'
            'version = 1.0\n',

            id='normalizes names dashes -> underscores',
        ),
        pytest.param(
            '[metadata]\n'
            'name = pkg\n'
            'version = 1.0\n'
            'classifiers =\n'
            '    Programming Language :: Python :: 3\n'
            '    License :: OSI Approved :: MIT License\n'
            '    Programming Language :: Python :: 2\n',

            '[metadata]\n'
            'name = pkg\n'
            'version = 1.0\n'
            'classifiers =\n'
            '    License :: OSI Approved :: MIT License\n'
            '    Programming Language :: Python :: 2\n'
            '    Programming Language :: Python :: 3\n',

            id='sorts classifiers',
        ),
    ),
)
def test_rewrite(input_s, expected, tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(input_s)

    main((str(setup_cfg),))

    assert setup_cfg.read() == expected


@pytest.mark.parametrize(
    ('filename', 'content_type'),
    (
        ('README.rst', 'text/x-rst'),
        ('README.markdown', 'text/markdown'),
        ('README.md', 'text/markdown'),
        ('README', 'text/plain'),
        ('readme.txt', 'text/plain'),
    ),
)
def test_adds_long_description_with_readme(filename, content_type, tmpdir):
    tmpdir.join(filename).write('my project!')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    main((str(setup_cfg),))

    assert setup_cfg.read() == (
        f'[metadata]\n'
        f'name = pkg\n'
        f'version = 1.0\n'
        f'long_description = file: {filename}\n'
        f'long_description_content_type = {content_type}\n'
    )


@pytest.mark.parametrize(
    'filename', ('LICENSE', 'LICENCE', 'LICENSE.md', 'license.txt'),
)
def test_sets_license_file_if_license_exists(filename, tmpdir):
    tmpdir.join(filename).write('COPYRIGHT (C) 2019 ME')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    main((str(setup_cfg),))

    assert setup_cfg.read() == (
        f'[metadata]\n'
        f'name = pkg\n'
        f'version = 1.0\n'
        f'license_file = {filename}\n'
    )


def test_rewrite_sets_license_type_and_classifier(tmpdir):
    with open('LICENSE') as f:
        tmpdir.join('LICENSE').write(f.read())
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'license = MIT\n'
        'license_file = LICENSE\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
    )


def test_rewrite_identifies_license(tmpdir):
    zlib_license = '''\
zlib License

(C) 2019 Anthony Sottile

This software is provided 'as-is', without any express or implied
warranty.  In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
'''
    tmpdir.join('LICENSE').write(zlib_license)
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'license = Zlib\n'
        'license_file = LICENSE\n'
        'classifiers =\n'
        '    License :: OSI Approved :: zlib/libpng License\n'
    )


@pytest.mark.parametrize(
    's',
    (
        pytest.param(
            '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
            id='already correct',
        ),
        pytest.param('~=3.6', id='weird comparator'),
    ),
)
def test_python_requires_left_alone(tmpdir, s):
    tmpdir.join('tox.ini').ensure()  # present, but not useful
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        f'[metadata]\n'
        f'name = pkg\n'
        f'version = 1.0\n'
        f'\n'
        f'[options]\n'
        f'python_requires = {s}\n',
    )

    assert not main((
        str(setup_cfg), '--min-py3-version=3.2',
        '--max-py-version=0.0',  # disable classifier generation
    ))

    assert setup_cfg.read() == (
        f'[metadata]\n'
        f'name = pkg\n'
        f'version = 1.0\n'
        f'\n'
        f'[options]\n'
        f'python_requires = {s}\n'
    )


def test_guess_python_requires_python2_tox_ini(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist=py36,py27,py37\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    main((str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7'))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 2\n'
        '    Programming Language :: Python :: 2.7\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*\n'
    )


def test_guess_python_requires_tox_ini_dashed_name(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist = py37-flake8\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    main((str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7'))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.7\n'
    )


def test_guess_python_requires_ignores_insufficient_version_envs(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist = py,py2,py3\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    assert not main((
        str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7',
    ))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
    )


def test_guess_python_requires_from_classifiers(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 2\n'
        '    Programming Language :: Python :: 2.7\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3.6\n',
    )

    main((str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7'))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 2\n'
        '    Programming Language :: Python :: 2.7\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*\n'
    )


def test_min_py3_version_updates_python_requires(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        '\n'
        '[options]\n'
        'python_requires = >=2.7, !=3.0.*, !=3.1.*\n',
    )

    main((str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7'))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 2\n'
        '    Programming Language :: Python :: 2.7\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*\n'
    )


def test_min_py3_version_greater_than_minimum(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.2\n',
    )

    main((str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7'))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.4\n'
    )


def test_min_py3_version_less_than_minimum(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist=py36\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    main((str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7'))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.6\n'
    )
