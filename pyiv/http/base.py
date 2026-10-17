"""Injectable HTTP client interfaces (sync and async)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any, Dict, Mapping, Optional, Union

from pyiv.http.response import AsyncStreamResponse, HttpResponse, StreamResponse


class HttpClient(ABC):
    """Sync injectable HTTP client.

    **Why this exists:** Apps should depend on a typed client (JSON bodies,
    status handling, optional streaming) instead of hard-coding urllib or a
    third-party stack. Bind ``UrllibHttpClient`` in production and
    ``MemoryHttpClient`` in tests.

    Example:
        >>> from pyiv.http import HttpResponse, MemoryHttpClient
        >>> client: HttpClient = MemoryHttpClient()
        >>> client.add("GET", "http://example.test/x", body=b"ok")
        >>> client.get("http://example.test/x").text
        'ok'
    """

    def get(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """HTTP GET. See ``request``."""
        return self.request("GET", url, headers=headers, params=params, timeout=timeout)

    def post(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """HTTP POST. See ``request``."""
        return self.request(
            "POST",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )

    def put(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """HTTP PUT. See ``request``."""
        return self.request(
            "PUT",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )

    def patch(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """HTTP PATCH. See ``request``."""
        return self.request(
            "PATCH",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )

    def delete(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """HTTP DELETE. See ``request``."""
        return self.request("DELETE", url, headers=headers, params=params, timeout=timeout)

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """Send an HTTP request and return a buffered response."""

    @abstractmethod
    def stream(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> AbstractContextManager[StreamResponse]:
        """Open a streaming response (context manager)."""

    def close(self) -> None:
        """Release transport resources (no-op by default)."""


class AsyncHttpClient(ABC):
    """Async injectable HTTP client.

    **Why this exists:** Async apps (inference adapters, SSE) need the same
    injectable contract as sync code without requiring httpx in core. Bind
    ``AsyncUrllibHttpClient`` or ``MemoryAsyncHttpClient``.

    Example:
        >>> import asyncio
        >>> from pyiv.http import MemoryAsyncHttpClient
        >>> async def _demo():
        ...     client = MemoryAsyncHttpClient()
        ...     client.add("GET", "http://example.test/", body=b"hi")
        ...     r = await client.get("http://example.test/")
        ...     return r.text
        >>> asyncio.run(_demo())
        'hi'
    """

    async def get(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        return await self.request("GET", url, headers=headers, params=params, timeout=timeout)

    async def post(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        return await self.request(
            "POST",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )

    async def put(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        return await self.request(
            "PUT",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )

    async def patch(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        return await self.request(
            "PATCH",
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        return await self.request("DELETE", url, headers=headers, params=params, timeout=timeout)

    @abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        """Send an HTTP request and return a buffered response."""

    @abstractmethod
    def stream(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> AbstractAsyncContextManager[AsyncStreamResponse]:
        """Open an async streaming response (async context manager)."""

    async def aclose(self) -> None:
        """Release transport resources (no-op by default)."""
