# PyIV Documentation

This directory contains the Sphinx documentation source for PyIV.

## Building Documentation Locally

To build the documentation locally:

1. Install dependencies:
   ```bash
   pip install -e ".[dev,docs]"
   # Or with Poetry:
   poetry install --extras "dev docs"
   ```

2. Build the HTML documentation:
   ```bash
   cd docs
   sphinx-build -b html . _build/html
   ```

3. View the documentation:
   Open `docs/_build/html/index.html` in your browser.

## Documentation Structure

- `conf.py` - Sphinx configuration
- `index.rst` - Main documentation page
- `modules.rst` - API documentation for all modules
- `_static/` - Custom CSS and static files

## Publishing

Documentation is automatically built and published to GitHub Pages via GitHub Actions when changes are pushed to the `main` branch.

