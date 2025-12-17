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
    """HTTP client using Python's standard library urllib.

    This client uses urllib.request for HTTP requests. It supports all standard
    HTTP methods and provides a simple interface for making requests.

    Example:
        >>> client = HTTPClient()
        >>> response = client.request("GET", "http://example.com")
        >>> print(response["status"])
        200
        >>> print(response["body"].decode("utf-8"))
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
    """HTTPS client using Python's standard library urllib.

    This client uses urllib.request for HTTPS requests with SSL/TLS support.
    It supports all standard HTTP methods over HTTPS.

    Example:
        >>> client = HTTPSClient()
        >>> response = client.request("GET", "https://example.com")
        >>> print(response["status"])
        200
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
