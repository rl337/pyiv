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

GitHub Actions builds and deploys to GitHub Pages on pushes to `main` that touch `pyiv/` or `docs/`.
The custom domain https://rl337.org/pyiv/ sits in front of that deploy.
