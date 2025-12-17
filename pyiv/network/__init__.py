"""Network client abstractions for pyiv.

This module provides network client abstractions following the chain of responsibility
pattern. It supports various network protocols built into Python's standard library,
such as HTTP, HTTPS, and others.

Example:
    >>> from pyiv.network import HTTPClient
    >>> client = HTTPClient()
    >>> response = client.request("GET", "https://example.com")
"""

from pyiv.network.base import NetworkClient
from pyiv.network.clients import (
    HTTPClient,
    HTTPSClient,
)

__all__ = [
    "NetworkClient",
    "HTTPClient",
    "HTTPSClient",
]
