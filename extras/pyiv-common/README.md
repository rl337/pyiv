# pyiv-common

Ubiquitous-library integrations for [pyiv](https://github.com/rl337/pyiv):
PyYAML (`YAMLSerDe`) and requests (`RequestsHttpClient`). Core `pyiv` stays
stdlib-only (including urllib HTTP clients).

## Install

```bash
pip install pyiv-common
# or
pip install pyiv[common]
```

Unreleased from git:

```bash
pip install "pyiv-common @ git+https://github.com/rl337/pyiv.git#subdirectory=extras/pyiv-common"
```

Requires `pyiv>=1.0`.

## Quick start

```python
from pyiv import Config, get_injector
from pyiv.http import HttpClient
from pyiv_common.network import RequestsHttpClient

class MyConfig(Config):
    def configure(self):
        self.register(HttpClient, RequestsHttpClient)

injector = get_injector(MyConfig)
client = injector.inject(HttpClient)
```

Docs: https://rl337.org/pyiv/
