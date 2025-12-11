"""Sphinx configuration for pyiv documentation."""

import os
import sys
from datetime import datetime

# Add the project root to the path so autodoc can find pyiv
sys.path.insert(0, os.path.abspath(".."))

# Project information
project = "pyiv"
copyright = f"{datetime.now().year}, pyiv contributors"
author = "pyiv contributors"

# Get version from pyiv package
try:
    import pyiv

    release = pyiv.__version__
    version = ".".join(release.split(".")[:2])  # Major.minor
except ImportError:
    release = "0.2.10"
    version = "0.2"

# Make version available to templates
html_context["version"] = release

# Sphinx extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",  # Support for Google/NumPy style docstrings
]

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__init__",
}

autodoc_mock_imports = []

# Autosummary settings
autosummary_generate = True

# Napoleon settings (for docstring parsing)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# HTML theme
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "display_version": True,
    "style_nav_header_background": "#0066cc",
}

# HTML output options
html_static_path = ["_static"]
html_css_files = ["custom.css"]

# HTML context
html_context = {
    "display_github": True,
    "github_user": "rl337",
    "github_repo": "pyiv",
    "github_version": "main",
    "conf_py_path": "/docs/",
    "version": release,  # Make version available to templates
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Output file base name for HTML help builder
htmlhelp_basename = "pyivdoc"

# Exclude patterns
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Master document
master_doc = "index"

