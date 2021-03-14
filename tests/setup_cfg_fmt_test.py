import argparse
import os

import pytest

from setup_cfg_fmt import _case_insensitive_glob
from setup_cfg_fmt import _natural_sort
from setup_cfg_fmt import _normalize_lib
from setup_cfg_fmt import _ver_type
from setup_cfg_fmt import main


def test_ver_type_ok():
    assert _ver_type('1.2') == (1, 2)


def test_ver_type_error():
    with pytest.raises(argparse.ArgumentTypeError) as excinfo:
        _ver_type('1.2.3')
    msg, = excinfo.value.args
    assert msg == "expected #.#, got '1.2.3'"


def test_ver_type_not_a_version():
    with pytest.raises(argparse.ArgumentTypeError) as excinfo:
        _ver_type('wat')
    msg, = excinfo.value.args
    assert msg == "expected #.#, got 'wat'"


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

    assert not main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        '\n'
        '[bdist_wheel]\n'
        'universal = true\n'
    )


@pytest.mark.parametrize(
    ('input_tpl', 'expected_tpl'),
    (
        pytest.param(
            '[metadata]\n'
            'version = 1.0\n'
            'name = pkg\n'
            '[options]\n'
            '{} =\n'
            '    req03\n'
            '    req05 <= 2,!=1\n'
            '    req06 ;python_version==2.7\n'
            '    req07 ;os_version!=windows\n'
            '    req13 !=2, >= 7\n'
            '    req >= 2\n'
            '    req14 <=2, >= 1\n'
            '    req01\n'
            '       req02\n'
            '    req09 ~= 7\n'
            '    req10 === 8\n'
            '    req11; python_version=="2.7"\n'
            '    req08    ==    2\n'
            '    req12;\n'
            '    req04 >= 1\n'
            '    req15 @ git+https://github.com/foo/bar.git@master\n'
            '    req16@git+https://github.com/biz/womp.git@tag\n',

            '[metadata]\n'
            'name = pkg\n'
            'version = 1.0\n'
            '\n'
            '[options]\n'
            '{} =\n'
            '    req>=2\n'
            '    req01\n'
            '    req02\n'
            '    req03\n'
            '    req04>=1\n'
            '    req05!=1,<=2\n'
            '    req08==2\n'
            '    req09~=7\n'
            '    req10===8\n'
            '    req12\n'
            '    req13!=2,>=7\n'
            '    req14>=1,<=2\n'
            '    req15@git+https://github.com/foo/bar.git@master\n'
            '    req16@git+https://github.com/biz/womp.git@tag\n'
            '    req06;python_version==2.7\n'
            '    req07;os_version!=windows\n'
            '    req11;python_version=="2.7"\n',

            id='normalizes requires',
        ),
    ),
)
@pytest.mark.parametrize(
    'which',
    ('install_requires', 'setup_requires'),
)
def test_rewrite_requires(which, input_tpl, expected_tpl, tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(input_tpl.format(which))

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == expected_tpl.format(which)


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
            '[bdist_wheel]\n'
            'universal = true\n'
            '\n'
            '[metadata]\n'
            'name = pkg\n'
            'version = 1.0\n'
            '\n'
            '[options.packages.find]\n'
            'where = src\n',

            '[metadata]\n'
            'name = pkg\n'
            'version = 1.0\n'
            '\n'
            '[options.packages.find]\n'
            'where = src\n'
            '\n'
            '[bdist_wheel]\n'
            'universal = true\n',

            id='orders sections (options.packages.find)',
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
        pytest.param(
            '[metadata]\n'
            'maintainer_email = jane@example.com\n'
            'maintainer = jane\n'
            'license = foo\n'
            'name = pkg\n'
            'author_email = john@example.com\n'
            'author = john\n',

            '[metadata]\n'
            'name = pkg\n'
            'author = john\n'
            'author_email = john@example.com\n'
            'maintainer = jane\n'
            'maintainer_email = jane@example.com\n'
            'license = foo\n',

            id='orders authors and maintainers',
        ),
        pytest.param(
            '[metadata]\n'
            'name = pkg\n'
            'author-email = john@example.com\n'
            'maintainer-email = jane@example.com\n',

            '[metadata]\n'
            'name = pkg\n'
            'author_email = john@example.com\n'
            'maintainer_email = jane@example.com\n',

            id='normalize dashes to underscores in keys',
        ),
    ),
)
def test_rewrite(input_s, expected, tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(input_s)

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == expected


@pytest.mark.parametrize(
    ('lib', 'expected'),
    (
        pytest.param('req01', 'req01', id='no conditions'),
        pytest.param('req04 >= 1', 'req04>=1', id='whitespace stripped'),
        pytest.param('req05 <= 2,!=1', 'req05!=1,<=2', id='<= cond at end'),
        pytest.param('req13 !=2, >= 7', 'req13!=2,>=7', id='>= cond at end'),
        pytest.param('req14 <=2, >= 1', 'req14>=1,<=2', id='b/w conds sorted'),
        pytest.param('req15~=2', 'req15~=2', id='compatible release'),
    ),
)
def test_normalize_lib(lib, expected):
    assert _normalize_lib(lib) == expected


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

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == (
        f'[metadata]\n'
        f'name = pkg\n'
        f'version = 1.0\n'
        f'long_description = file: {filename}\n'
        f'long_description_content_type = {content_type}\n'
    )


def test_readme_discover_prefers_file_over_directory(tmpdir):
    tmpdir.join('README').mkdir()
    tmpdir.join('README.md').write('my project!')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n',
    )
    assert main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'long_description = file: README.md\n'
        'long_description_content_type = text/markdown\n'
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

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == (
        f'[metadata]\n'
        f'name = pkg\n'
        f'version = 1.0\n'
        f'license_file = {filename}\n'
    )


def test_license_does_not_match_directories(tmpdir):
    tmpdir.join('licenses').ensure_dir()
    test_sets_license_file_if_license_exists('LICENSE', tmpdir)


def test_rewrite_sets_license_type_and_classifier(tmpdir):
    here = os.path.dirname(__file__)
    license_file = os.path.join(here, os.pardir, 'LICENSE')
    with open(license_file) as f:
        tmpdir.join('LICENSE').write(f.read())
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    assert main((str(setup_cfg),))

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

    assert main((str(setup_cfg),))

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
        pytest.param('>=3', id='not enough version segments'),
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


@pytest.mark.parametrize(
    ('section', 'expected'),
    (
        pytest.param(
            '\n'
            '[options]\n'
            'dependency_links = \n'
            'py_modules = pkg\n',
            '\n'
            '[options]\n'
            'py_modules = pkg\n',
            id='only empty options removed',
        ),
        pytest.param(
            '\n'
            '[options]\n'
            'dependency_links = \n',
            '',
            id='entire section removed if all empty options are removed',
        ),
    ),
)
def test_strips_empty_options_and_sections(tmpdir, section, expected):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        f'{section}',
    )

    assert main((str(setup_cfg),))
    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        f'{expected}'
    )


def test_guess_python_requires_python2_tox_ini(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist=py36,py27,py37,pypy\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert main(args)

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
        '    Programming Language :: Python :: Implementation :: CPython\n'
        '    Programming Language :: Python :: Implementation :: PyPy\n'
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

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.7\n'
        '    Programming Language :: Python :: Implementation :: CPython\n'
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
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: Implementation :: CPython\n',
    )

    assert not main((
        str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7',
    ))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: Implementation :: CPython\n'
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

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert main(args)

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

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert main(args)

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

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert main(args)

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


def test_min_version_removes_classifiers(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.2\n'
        '    Programming Language :: Python :: 3.3\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.2, !=3.6.*\n',
    )

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.4, !=3.6.*\n'
    )


def test_python_requires_with_patch_version(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        # added this to make sure that it doesn't revert to 3.6
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.6.1\n',
    )

    # added this to make sure it doesn't revert to 3.6
    tmpdir.join('tox.ini').write('[tox]\nenvlist=py36\n')

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.8')
    assert main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '    Programming Language :: Python :: 3.8\n'
        '    Programming Language :: Python :: Implementation :: CPython\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.6.1\n'
    )


def test_classifiers_left_alone_for_odd_python_requires(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.2\n'
        '    Programming Language :: Python :: 3.3\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = ~=3.2\n',
    )

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert not main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.2\n'
        '    Programming Language :: Python :: 3.3\n'
        '    Programming Language :: Python :: 3.4\n'
        '    Programming Language :: Python :: 3.5\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '\n'
        '[options]\n'
        'python_requires = ~=3.2\n'
    )


def test_min_py3_version_less_than_minimum(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist=py36\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n',
    )

    args = (str(setup_cfg), '--min-py3-version=3.4', '--max-py-version=3.7')
    assert main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.6\n'
        '    Programming Language :: Python :: 3.7\n'
        '    Programming Language :: Python :: Implementation :: CPython\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.6\n'
    )


def test_rewrite_extras(tmpdir):
    setup_cfg_content = (
        '[metadata]\n'
        'name = test\n'
        '[options.extras_require]\n'
        'dev =\n'
        '    pytest\n'
        '    hypothesis\n'
        'ci =\n'
        '    hypothesis\n'
        '    pytest\n'
        'arg =\n'
    )
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(setup_cfg_content)

    main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = test\n'
        '\n'
        '[options.extras_require]\n'
        'ci =\n'
        '    hypothesis\n'
        '    pytest\n'
        'dev =\n'
        '    hypothesis\n'
        '    pytest\n'
    )


def test_imp_classifiers_from_tox_ini(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist = py39-django31,pypy3,docs\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = test\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.9\n',
    )

    args = (str(setup_cfg), '--min-py3-version=3.9', '--max-py-version=3.9')
    assert main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = test\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.9\n'
        '    Programming Language :: Python :: Implementation :: CPython\n'
        '    Programming Language :: Python :: Implementation :: PyPy\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.9\n'
    )


def test_imp_classifiers_no_change(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist = py39,pypy3-django31\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = test\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.9\n'
        '    Programming Language :: Python :: Implementation :: CPython\n'
        '    Programming Language :: Python :: Implementation :: PyPy\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.9\n',
    )

    args = (str(setup_cfg), '--min-py3-version=3.9', '--max-py-version=3.9')
    assert not main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = test\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.9\n'
        '    Programming Language :: Python :: Implementation :: CPython\n'
        '    Programming Language :: Python :: Implementation :: PyPy\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.9\n'
    )


def test_imp_classifiers_pypy_only(tmpdir):
    tmpdir.join('tox.ini').write('[tox]\nenvlist = pypy3\n')
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = test\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.9\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.9\n',
    )

    args = (str(setup_cfg), '--min-py3-version=3.9', '--max-py-version=3.9')
    assert main(args)

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = test\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3 :: Only\n'
        '    Programming Language :: Python :: 3.9\n'
        '    Programming Language :: Python :: Implementation :: PyPy\n'
        '\n'
        '[options]\n'
        'python_requires = >=3.9\n'
    )


def test_natural_sort():
    classifiers = [
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
    ]

    sorted_classifiers = _natural_sort(classifiers)

    assert sorted_classifiers == [
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ]
