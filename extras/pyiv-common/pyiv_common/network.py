"""requests-backed NetworkClient for pyiv.

This module provides ``RequestsClient``, a ``pyiv.network.NetworkClient``
that uses the requests library. urllib HTTP/HTTPS clients stay in core.

**What Problem Does This Solve?**

Many apps already depend on requests (sessions, adapters, timeouts).
Core pyiv cannot import it. This extra implements the same
``request(method, url, headers, data, timeout)`` shape as core clients.

**Real-World Use Cases:**
- Inject an HTTP client that uses the requests stack
- Swap urllib ``HTTPClient`` for ``RequestsClient`` in Config

Example:

    >>> from pyiv_common.network import RequestsClient
    >>> client = RequestsClient()
    >>> client.handler_type
    'http'
    >>> client.request("GET", "ftp://example.com")
    Traceback (most recent call last):
        ...
    ValueError: RequestsClient only supports http:// and https:// URLs, got: ftp://example.com
"""

from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]

from pyiv.network.base import NetworkClient


class RequestsClient(NetworkClient):
    """HTTP(S) client using the requests library.

    ``handler_type`` is ``"http"`` so it can replace urllib ``HTTPClient``
    on the NETWORK_CLIENT chain. Both ``http://`` and ``https://`` URLs
    are accepted.

    Example:
        >>> from pyiv import ChainType, Config, get_injector
        >>> from pyiv_common.network import RequestsClient
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register_chain_handler(
        ...             ChainType.NETWORK_CLIENT, "http", RequestsClient
        ...         )
        >>> injector = get_injector(MyConfig)
        >>> client = injector.inject_chain_handler(ChainType.NETWORK_CLIENT, "http")
        >>> isinstance(client, RequestsClient)
        True
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier ("http")."""
        return "http"

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with requests.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: The URL to request (must be http:// or https://)
            headers: Optional dictionary of HTTP headers
            data: Optional request body (string or bytes)
            timeout: Optional timeout in seconds

        Returns:
            Dictionary containing:
                - status: HTTP status code
                - headers: Response headers dictionary
                - body: Response body (bytes)
                - url: Final URL after redirects

        Raises:
            ValueError: If URL is not http:// or https://
            requests.RequestException: If the request fails
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"RequestsClient only supports http:// and https:// URLs, got: {url}")

        if data is not None and isinstance(data, str):
            data = data.encode("utf-8")

        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            data=data,
            timeout=timeout,
        )
        return {
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": response.content,
            "url": response.url,
        }
