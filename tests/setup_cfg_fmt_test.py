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

    assert not main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        '\n'
        '[bdist_wheel]\n'
        'universal = true\n'
    )


def test_sorts_fields_and_sections(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[bdist_wheel]\n'
        'universal = true\n'
        '\n'
        '[metadata]\n'
        'version = 1.0\n'
        'name = pkg\n',
    )

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        '\n'
        '[bdist_wheel]\n'
        'universal = true\n'
    )


def test_normalizes_name_to_underscores(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg-name\n'
        'version = 1.0\n',
    )

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg_name\n'
        'version = 1.0\n'
    )


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


def test_sorts_classifiers(tmpdir):
    setup_cfg = tmpdir.join('setup.cfg')
    setup_cfg.write(
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    Programming Language :: Python :: 3\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3.6\n',
    )

    assert main((str(setup_cfg),))

    assert setup_cfg.read() == (
        '[metadata]\n'
        'name = pkg\n'
        'version = 1.0\n'
        'classifiers =\n'
        '    License :: OSI Approved :: MIT License\n'
        '    Programming Language :: Python :: 3\n'
        '    Programming Language :: Python :: 3.6\n'
    )
