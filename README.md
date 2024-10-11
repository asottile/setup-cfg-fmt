[![build status](https://github.com/asottile/setup-cfg-fmt/actions/workflows/main.yml/badge.svg)](https://github.com/asottile/setup-cfg-fmt/actions/workflows/main.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/asottile/setup-cfg-fmt/main.svg)](https://results.pre-commit.ci/latest/github/asottile/setup-cfg-fmt/main)

setup-cfg-fmt
=============

apply a consistent format to `setup.cfg` files

## installation

```bash
pip install setup-cfg-fmt
```

## as a pre-commit hook

See [pre-commit](https://github.com/pre-commit/pre-commit) for instructions

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/asottile/setup-cfg-fmt
    rev: v2.6.0
    hooks:
    -   id: setup-cfg-fmt
```

## cli

Consult the help for the latest usage:

```console
$ setup-cfg-fmt --help
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

### normalizes dashes to underscores in keys

setuptools allows dashed names but does not document them.

```diff
 [metadata]
 name = pre-commit
-long-description = file: README.md
+long_description = file: README.md
```

### adds `long_description` if `README` is present

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

### set `python_requires`

A few sources are searched for guessing `python_requires`:

- the existing `python_requires` setting itself
- `envlist` in `tox.ini` if present
- python version `classifiers` that are already set
- the `--min-py-version` argument

### adds python version classifiers

classifiers are generated based on:

- the `python_requires` setting
- the `--max-py-version` argument
- `--include-version-classifiers` is specified

```diff
 name = pkg
 version = 1.0
+classifiers =
+    Programming Language :: Python :: 3
+    Programming Language :: Python :: 3.7
+    Programming Language :: Python :: 3.8
+    Programming Language :: Python :: 3.9
+    Programming Language :: Python :: 3.10
+    Programming Language :: Python :: 3.11
+    ...
```

without `--include-version-classifiers` only the major version will be included:

```diff
 name = pkg
 version = 1.0
+classifiers =
+    Programming Language :: Python :: 3
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

### removes empty options in any section

```diff
 [options]
-dependency_links =
 python_requires = >= 3.6.1
```

## related projects

- [setup-py-upgrade]: automatically migrate `setup.py` -> `setup.cfg`

[setup-py-upgrade]: https://github.com/asottile/setup-py-upgrade
