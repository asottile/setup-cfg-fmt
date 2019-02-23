import pytest

from setup_cfg_fmt import main


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

    assert main((str(setup_cfg),)) == 0

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
            '    Programming Language :: Python :: 3.6\n',

            '[metadata]\n'
            'name = pkg\n'
            'version = 1.0\n'
            'classifiers =\n'
            '    License :: OSI Approved :: MIT License\n'
            '    Programming Language :: Python :: 3\n'
            '    Programming Language :: Python :: 3.6\n',

            id='sorts classifiers',
        ),
    ),
)
def test_rewrite(input_s, expected, tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(input_s)

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == expected


def test_adds_long_description_with_readme(tmpdir):
    tmpdir.join('README.md').write('my project!')
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
        'long_description = file: README.md\n'
        'long_description_content_type = text/markdown\n'
    )


def test_sets_license_file_if_license_exists(tmpdir):
    tmpdir.join('LICENSE').write('COPYRIGHT (C) 2019 ME')
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
        'license_file = LICENSE\n'
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
