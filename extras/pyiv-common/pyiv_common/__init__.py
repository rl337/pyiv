"""Ubiquitous-library integrations for pyiv.

pyiv-common is the ``#include <stdlib.h>`` extra for pyiv: PyYAML and
requests only. Core ``pyiv`` stays stdlib-only.

**What Problem Does This Solve?**

Libraries such as PyYAML and requests are everywhere in Python, but they
are not the standard library. Putting them in core would break pyiv's
zero-runtime-dependency guarantee. A dedicated package per library would
proliferate wheels. ``pyiv-common`` is that middle tier.

**Real-World Use Cases:**
- YAML config files via ``YAMLSerDe``
- HTTP with the requests stack via ``RequestsClient``
- Injecting those types through a pyiv ``Config``

Usage:

    >>> from pyiv_common.serde import YAMLSerDe
    >>> YAMLSerDe().handler_type
    'yaml'
    >>> from pyiv_common.network import RequestsClient
    >>> RequestsClient().handler_type
    'http'
"""

from pyiv_common.network import RequestsClient
from pyiv_common.serde import YAMLSerDe

__version__ = "0.1.0"
__all__ = [
    "YAMLSerDe",
    "RequestsClient",
]
