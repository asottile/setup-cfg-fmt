[![Build Status](https://travis-ci.org/asottile/setup-cfg-fmt.svg?branch=master)](https://travis-ci.org/asottile/setup-cfg-fmt)
[![Coverage Status](https://coveralls.io/repos/github/asottile/setup-cfg-fmt/badge.svg?branch=master)](https://coveralls.io/github/asottile/setup-cfg-fmt?branch=master)

setup-cfg-fmt
=============

apply a consistent format to `setup.cfg` files

## installation

`pip install setup-cfg-fmt`

## cli

Consult the help for the latest usage:

```console
$ setup-cfg-fmt --help
usage: setup-cfg-fmt [-h] [filenames [filenames ...]]

positional arguments:
  filenames

optional arguments:
  -h, --help  show this help message and exit
```

## what does it do?

### sets a consistent ordering for attributes

For example, `name` and `version` (the most important metadata) will always
appear at the top.

```diff
 [metadata]
-version = 1.14.4
-name = pre_commit
+name = pre_commit
+version = 1.14.4
```

### normalizes dashes to underscores in project name

- `pip` will normalize names to dashes `foo_bar` => `foo-bar`
- `python setup.py sdist` produces a filename with the name verbatim
- `pip wheel .` produces a filename with an underscore-normalized name

```console
$ # with dashed name
$ python setup.py sdist && pip wheel -w dist .
...
$ ls dist/ | cat
setup_cfg_fmt-0.0.0-py2.py3-none-any.whl
setup-cfg-fmt-0.0.0.tar.gz
$ # with underscore name
$ python setup.py sdist && pip wheel -w dist .
...
$ ls dist/ | cat
setup_cfg_fmt-0.0.0-py2.py3-none-any.whl
setup_cfg_fmt-0.0.0.tar.gz
```

This makes it easier to upload packages to pypi since they end up with the
same filename prefix.

```diff
 [metadata]
-name = pre-commit
+name = pre_commit
```

### adds `long_description` if `README.md` is present

This will show up on the pypi project page

```diff
 [metadata]
 name = pre_commit
 version = 1.14.5
+long_description = file: README.md
+long_description_content_type = text/markdown
```

### adds `license_file` / `license` / license classifier if `LICENSE` exists

```diff
 [metadata]
 name = pre_commit
 version = 1.14.5
+license = MIT
+license_file = LICENSE
+classifiers =
+    License :: OSI Approved :: MIT License
```

### sorts classifiers

```diff
 [metadata]
 name = pre_commit
 version = 1.14.5
 classifiers =
-    Programming Language :: Python :: 3
-    License :: OSI Approved :: MIT License
+    License :: OSI Approved :: MIT License
+    Programming Language :: Python :: 3
     Programming Language :: Python :: 3.6
```

## related projects

- [setup-py-upgrade]: automatically migrate `setup.py` -> `setup.cfg`

[setup-py-upgrade]: https://github.com/asottile/setup-py-upgrade
