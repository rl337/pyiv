---
name: maintain-docs
description: Keep pyiv's PyPI listing, Sphinx site, and release notes in sync. Use when editing README.md, docs/, pyproject.toml metadata or URLs, CHANGELOG, GitHub releases, install instructions, Key Features, public APIs, or doctests; when adding modules to the API nav; or when the user mentions the website, PyPI, documentation, or changelog.
---

# Maintain pyiv docs

Three public surfaces must agree. Docstrings feed the site; they are not a fourth landing page.

| Pillar | Files | Job |
| --- | --- | --- |
| PyPI listing | `README.md`, `[project]` in `pyproject.toml` | README is GitHub **and** Warehouse long_description. Metadata (author, URLs, description) is the sidebar. Not a second API manual. |
| Website | `docs/`, `pyiv/**/*.py` docstrings | Product manual at https://rl337.org/pyiv/. Features, install, guide, autodoc. Production is `main` only; PRs go to `/branch/<name>/`. |
| Release notes | `CHANGELOG.md` (when present), GitHub Releases, `RELEASE.md`, `.github/workflows/release.yml` | Why this version shipped. Same install command as README. Not a squash-commit dump that tells people to `pip install` a version that is not on PyPI. |

## Install story (must match all three)

Until a production PyPI upload exists:

- Install: `pip install git+https://github.com/rl337/pyiv.git`
- Do not write `pip install pyiv`, do not link https://pypi.org/project/pyiv/, do not mention Poetry.
- First public version is **0.3.0**, not a 0.2.x tag.

After that upload, flip README, `docs/index.rst`, changelog/release templates, and `project.urls` together in the same change.

Canonical URLs (also `[project.urls]`): Homepage/Repository `https://github.com/rl337/pyiv`, Documentation `https://rl337.org/pyiv/`. No `yourusername` placeholders.

## After a public API change

1. Runnable module doctest (self-contained; no network, real sleeps, or cwd writes).
2. New public module: `docs/pyiv/pyiv.<module>.rst` **and** the matching toctree on `docs/index.rst`. Omit `binder_impl`.
3. Homepage Key Features stay: type injection, scopes, keys/binder, reflection, test doubles, zero deps. Not Factory-first.
4. If the change is user-visible, add a changelog bullet the release notes can use.
5. `pytest --doctest-modules pyiv` and `sphinx-build -b html docs docs/_build/html`.

## Sidebar UX

RTD only expands nested toctrees from the current page. Grouped `.. toctree::` directives live on `docs/index.rst` (User guide in `docs/guide/`, then API groups). Keep `collapse_navigation: False` and `titles_only: True` in `docs/conf.py`.
