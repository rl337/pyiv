# pyiv-common

Ubiquitous-library integrations for [pyiv](https://pypi.org/project/pyiv/):
PyYAML (`YAMLSerDe`) and requests (`RequestsClient`). Core `pyiv` stays
stdlib-only.

**Docs:** [https://rl337.org/pyiv/](https://rl337.org/pyiv/guide/packages.html)

## Install

```bash
pip install pyiv-common
```

Or `pip install pyiv[common]`. Requires Python 3.8+. Unreleased `main`:

```bash
pip install "pyiv-common @ git+https://github.com/rl337/pyiv.git#subdirectory=extras/pyiv-common"
```

## Quick start

```python
from pyiv import Config, get_injector
from pyiv_common.serde import YAMLSerDe
from pyiv_common.network import RequestsClient

class MyConfig(Config):
    def configure(self):
        self.register(YAMLSerDe, YAMLSerDe)
        self.register(RequestsClient, RequestsClient)

injector = get_injector(MyConfig)
serde = injector.inject(YAMLSerDe)
client = injector.inject(RequestsClient)
```

## License

MIT — same as pyiv.
