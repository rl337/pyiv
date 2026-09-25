"""Standard library network client implementations.

This module provides network client implementations using Python's standard library,
including HTTP and HTTPS clients using urllib.
"""

from typing import Any, Dict, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pyiv.network.base import NetworkClient


class HTTPClient(NetworkClient):
    """HTTP(S) client using stdlib ``urllib``.

    Use this for plain HTTP or HTTPS URLs when you want a zero-dependency
    client bound into the NETWORK_CLIENT chain. Prefer invalid-URL Traceback
    examples in docs/tests — do not hit the network from doctests.

    Example:
        >>> client = HTTPClient()
        >>> client.handler_type
        'http'
        >>> client.request("GET", "ftp://example.com")
        Traceback (most recent call last):
            ...
        ValueError: HTTPClient only supports http:// and https:// URLs, got: ftp://example.com
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier.

        Returns:
            The handler type identifier ("http")
        """
        return "http"

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: The URL to request (must start with http://)
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
            ValueError: If URL does not start with http://
            URLError: If the request fails
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"HTTPClient only supports http:// and https:// URLs, got: {url}")

        # Convert data to bytes if provided
        if data is not None and isinstance(data, str):
            data = data.encode("utf-8")

        # Create request
        req = Request(url, data=data, method=method.upper())
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)

        try:
            with urlopen(req, timeout=timeout) as response:
                status = response.getcode()
                response_headers = dict(response.headers.items())
                body = response.read()
                final_url = response.geturl()

                return {
                    "status": status,
                    "headers": response_headers,
                    "body": body,
                    "url": final_url,
                }
        except HTTPError as e:
            # HTTPError includes response body even for error status codes
            status = e.code
            response_headers = dict(e.headers.items()) if e.headers else {}
            body = e.read() if hasattr(e, "read") else b""
            return {
                "status": status,
                "headers": response_headers,
                "body": body,
                "url": url,
            }
        except URLError as e:
            raise URLError(f"Failed to make HTTP request to {url}: {e}") from e


class HTTPSClient(NetworkClient):
    """HTTPS-only client using stdlib ``urllib``.

    Use this when you want to reject non-HTTPS URLs at the client boundary
    (scheme must be ``https://``). Like ``HTTPClient``, doctests should use
    Traceback examples for invalid schemes rather than live network calls.

    Example:
        >>> client = HTTPSClient()
        >>> client.handler_type
        'https'
        >>> client.request("GET", "http://example.com")
        Traceback (most recent call last):
            ...
        ValueError: HTTPSClient only supports https:// URLs, got: http://example.com
    """

    @property
    def handler_type(self) -> str:
        """Return the handler type identifier.

        Returns:
            The handler type identifier ("https")
        """
        return "https"

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make an HTTPS request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: The URL to request (must start with https://)
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
            ValueError: If URL does not start with https://
            URLError: If the request fails
        """
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"HTTPSClient only supports https:// URLs, got: {url}")

        # Convert data to bytes if provided
        if data is not None and isinstance(data, str):
            data = data.encode("utf-8")

        # Create request
        req = Request(url, data=data, method=method.upper())
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)

        try:
            with urlopen(req, timeout=timeout) as response:
                status = response.getcode()
                response_headers = dict(response.headers.items())
                body = response.read()
                final_url = response.geturl()

                return {
                    "status": status,
                    "headers": response_headers,
                    "body": body,
                    "url": final_url,
                }
        except HTTPError as e:
            # HTTPError includes response body even for error status codes
            status = e.code
            response_headers = dict(e.headers.items()) if e.headers else {}
            body = e.read() if hasattr(e, "read") else b""
            return {
                "status": status,
                "headers": response_headers,
                "body": body,
                "url": url,
            }
        except URLError as e:
            raise URLError(f"Failed to make HTTPS request to {url}: {e}") from e
