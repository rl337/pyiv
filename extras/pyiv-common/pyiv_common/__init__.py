"""Ubiquitous-library integrations for pyiv.

pyiv-common is the ``#include <stdlib.h>`` extra for pyiv: PyYAML and
requests. Core ``pyiv`` stays stdlib-only (including urllib HTTP clients).

**What Problem Does This Solve?**

Libraries such as PyYAML and requests are everywhere in Python, but they
are not the standard library. Putting them in core would break pyiv's
zero-runtime-dependency guarantee. A dedicated package per library would
proliferate wheels. ``pyiv-common`` is that middle tier.

**Real-World Use Cases:**
- YAML config files via ``YAMLSerDe``
- HTTP with the requests stack via ``RequestsHttpClient``
- Injecting those types through a pyiv ``Config``

Usage:

    >>> from pyiv_common.serde import YAMLSerDe
    >>> YAMLSerDe().handler_type
    'yaml'
    >>> from pyiv_common.network import RequestsHttpClient
    >>> client = RequestsHttpClient()
    >>> client.request("GET", "ftp://example.com/")
    Traceback (most recent call last):
        ...
    ValueError: Only http:// and https:// URLs are allowed, got: ftp://example.com/
"""

from pyiv_common.network import RequestsClient, RequestsHttpClient
from pyiv_common.serde import YAMLSerDe

__version__ = "0.2.0"
__all__ = [
    "YAMLSerDe",
    "RequestsHttpClient",
    "RequestsClient",
]
