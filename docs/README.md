# PyIV Documentation

Sphinx sources for https://rl337.org/pyiv/.

The site is the product manual. Module pages are generated from `pyiv` docstrings.
The GitHub [README](../README.md) is a short landing page and should not duplicate the API.

## Building locally

```bash
pip install -e ".[dev,docs]"
cd docs
sphinx-build -b html . _build/html
```

Open `docs/_build/html/index.html`.

## Layout

- `conf.py` — Sphinx config (RTD theme, autodoc)
- `index.rst` — homepage, install, quick start, sidebar toctrees
- `pyiv/` — per-module autodoc pages
- `_static/` — custom CSS

## Publishing

GitHub Actions builds Sphinx on docs changes.

- **main** deploys production: https://rl337.org/pyiv/
- **pull requests** deploy a preview at `https://rl337.org/pyiv/branch/<branch>/` and comment the URL on the PR. Closing the PR removes that folder.
- Production is never replaced by a PR; previews live only under `/branch/`.
