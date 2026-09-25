"""Base NetworkClient interface for network operations.

This module defines the abstract base class for all NetworkClient implementations.
NetworkClient is a chain handler for the NETWORK_CLIENT chain type. All network
client implementations must inherit from NetworkClient and implement the request()
method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pyiv.chain import ChainHandler, ChainType


class NetworkClient(ChainHandler):
    """Abstract network client in the NETWORK_CLIENT chain.

    Use this as the injectable type for protocol-specific clients (HTTP, HTTPS,
    etc.). Register concrete clients in a chain so callers dispatch by URL
    scheme without hard-coding urllib. Subclasses must implement
    ``handler_type`` and ``request()``.

    **Why this exists:** Injectable HTTP-ish client so call sites do not hard-code urllib.


    Example:
        >>> from typing import Any, Dict, Optional, Union
        >>> from pyiv.network.base import NetworkClient
        >>> class StubHTTP(NetworkClient):
        ...     @property
        ...     def handler_type(self) -> str:
        ...         return "http"
        ...     def request(
        ...         self,
        ...         method: str,
        ...         url: str,
        ...         headers: Optional[Dict[str, str]] = None,
        ...         data: Optional[Union[str, bytes]] = None,
        ...         timeout: Optional[float] = None,
        ...     ) -> Dict[str, Any]:
        ...         return {"status": 200, "headers": {}, "body": b"ok", "url": url}
        >>> StubHTTP().request("GET", "http://example.test")["body"]
        b'ok'
    """

    @property
    def chain_type(self) -> ChainType:
        """Return the chain type (always NETWORK_CLIENT for NetworkClient).

        Returns:
            ChainType.NETWORK_CLIENT
        """
        return ChainType.NETWORK_CLIENT

    @property
    @abstractmethod
    def handler_type(self) -> str:
        """Return the protocol identifier (e.g., "http", "https").

        Returns:
            A string identifying the network protocol
        """
        pass

    def handle(self, request: Any, **kwargs) -> Any:
        """Handle a network request.

        This is the chain handler interface. For NetworkClient, requests can be:
        - A tuple of (method, url, headers, data, timeout) -> returns response
        - A dict with "method", "url", etc. keys -> processes accordingly
        - A direct URL string -> performs GET request

        Args:
            request: The request (can be tuple, dict, or URL string)
            **kwargs: Additional keyword arguments (method, url, headers, data, timeout)

        Returns:
            Response dictionary with status, headers, and body
        """
        if isinstance(request, tuple):
            # Tuple format: (method, url, headers, data, timeout)
            method = request[0] if len(request) > 0 else "GET"
            url = request[1] if len(request) > 1 else ""
            headers = request[2] if len(request) > 2 else None
            data = request[3] if len(request) > 3 else None
            timeout = request[4] if len(request) > 4 else None
            return self.request(method, url, headers=headers, data=data, timeout=timeout)
        elif isinstance(request, dict):
            # Dict format: {"method": "GET", "url": "...", ...}
            method = request.get("method", "GET")
            url = request.get("url", "")
            headers = request.get("headers")
            data = request.get("data")
            timeout = request.get("timeout")
            return self.request(method, url, headers=headers, data=data, timeout=timeout)
        elif isinstance(request, str):
            # Direct URL string -> GET request
            return self.request("GET", request, **kwargs)
        else:
            # Use kwargs directly
            method = kwargs.get("method", "GET")
            url = kwargs.get("url", str(request))
            headers = kwargs.get("headers")
            data = kwargs.get("data")
            timeout = kwargs.get("timeout")
            return self.request(method, url, headers=headers, data=data, timeout=timeout)

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make a network request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: The URL to request
            headers: Optional dictionary of HTTP headers
            data: Optional request body (string or bytes)
            timeout: Optional timeout in seconds

        Returns:
            Dictionary containing:
                - status: HTTP status code
                - headers: Response headers dictionary
                - body: Response body (bytes)
                - url: Final URL after redirects
        """
        pass
