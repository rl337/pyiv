# pyiv

Guice-style dependency injection for Python: type-based constructor injection,
scopes, qualified keys, and built-in test doubles. Zero runtime dependencies.
Python 3.8+.

**Docs:** [https://rl337.org/pyiv/](https://rl337.org/pyiv/) ·
**Changelog:** [https://rl337.org/pyiv/changelog.html](https://rl337.org/pyiv/changelog.html)

## Install

pyiv is not on PyPI yet. Install from GitHub:

```bash
pip install git+https://github.com/rl337/pyiv.git
```

## Quick start

```python
from pyiv import Config, get_injector

class Database:
    pass

class PostgreSQL(Database):
    pass

class MyConfig(Config):
    def configure(self):
        self.register(Database, PostgreSQL)

injector = get_injector(MyConfig)
db = injector.inject(Database)  # PostgreSQL
```

The [user guide](https://rl337.org/pyiv/) covers Binder, Keys, scopes,
and the Clock / Filesystem / Console / DateTimeService test doubles.

## Development

```bash
pip install -e ".[dev,docs]"
./run_checks.sh
```

`run_checks.sh` formats (black/isort), runs pytest (including doctests in
`pyiv/`), mypy, bandit, and a Sphinx build.

Version numbers are bumped by GitHub Actions on `main`. Do not edit
`pyproject.toml` / `pyiv/__init__.py` versions except for a manual major bump.

## License

MIT — see [LICENSE](LICENSE).
