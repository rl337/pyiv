---
name: maintain-docs
description: Keep pyiv's README, Sphinx site, and module doctests aligned. Use when editing pyiv public APIs, docs/, README.md, Sphinx pages, Key Features, or install instructions; when adding modules to the API nav; or when the user mentions the website, documentation, or doctests.
---

# Maintain pyiv docs

## Split

| Surface | Job |
| --- | --- |
| `README.md` | GitHub landing: one-paragraph what/why, honest install, short quick start, link to https://rl337.org/pyiv/. Not a second API manual. |
| `docs/` (Sphinx) | Product docs: features, install, examples, API from autodoc. |
| `pyiv/**/*.py` docstrings | Source of truth for API pages. Examples are doctests and run in CI. |

Do not claim `pip install pyiv` or link PyPI until the package is published. Install copy is `pip install git+https://github.com/rl337/pyiv.git`. Do not mention Poetry.

## After a public API change

1. Update the module docstring with a **runnable** doctest (self-contained stubs, no network, no real sleeps, no writing cwd files).
2. If you added a public module, add `docs/pyiv/pyiv.<module>.rst` and list it in the matching toctree on `docs/index.rst` (not only `modules.rst`). Do not put `binder_impl` in the sidebar.
3. Keep homepage **Key Features** as: type injection, scopes, keys/binder, reflection, test doubles, zero deps. Do not promote Factory as a headline feature.
4. Run `pytest --doctest-modules pyiv` and `sphinx-build -b html docs docs/_build/html`.

Production docs are https://rl337.org/pyiv/ (main only). PR previews publish to `https://rl337.org/pyiv/branch/<branch>/`.

## Sidebar UX

RTD only shows nested toctrees from **the current page**. Put grouped `.. toctree::` directives on `docs/index.rst` so Core DI / Bindings / Discovery / Test doubles / Integrations are populated on first visit. Keep `collapse_navigation: False` and `titles_only: True` in `docs/conf.py` so the homepage sidebar lists module pages without dumping every method.
