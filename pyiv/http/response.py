"""HTTP response types for pyiv clients."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Iterator, Mapping, Optional, Union

from pyiv.http.errors import HttpStatusError


class HttpResponse:
    """Buffered HTTP response (status, headers, body).

    **Why this exists:** Injectable clients need a typed response object with
    ``json()`` / ``text`` / ``raise_for_status()`` — not a bare dict — so
    streaming and status handling stay natural at call sites.

    Example:
        >>> from pyiv.http.response import HttpResponse
        >>> r = HttpResponse(200, {"Content-Type": "application/json"}, b'{"a": 1}', "http://x/")
        >>> r.json()
        {'a': 1}
        >>> r.raise_for_status()
    """

    def __init__(
        self,
        status_code: int,
        headers: Mapping[str, str],
        content: bytes,
        url: str,
    ) -> None:
        self._status_code = status_code
        self._headers = dict(headers)
        self._content = content
        self._url = url

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._status_code

    @property
    def headers(self) -> Dict[str, str]:
        """Response headers (single-valued map)."""
        return dict(self._headers)

    @property
    def content(self) -> bytes:
        """Raw response body."""
        return self._content

    @property
    def text(self) -> str:
        """Response body decoded as UTF-8 (replacement on errors)."""
        return self._content.decode("utf-8", errors="replace")

    @property
    def url(self) -> str:
        """Final request URL (after redirects when the transport reports it)."""
        return self._url

    def json(self) -> Any:
        """Parse the body as JSON.

        Returns:
            The decoded JSON value

        Raises:
            json.JSONDecodeError: If the body is not valid JSON
        """
        return json.loads(self._content.decode("utf-8"))

    def raise_for_status(self) -> None:
        """Raise ``HttpStatusError`` if ``status_code`` is 4xx or 5xx."""
        if 400 <= self._status_code < 600:
            raise HttpStatusError(
                f"HTTP {self._status_code} for {self._url}",
                status_code=self._status_code,
                response=self,
            )


class StreamResponse:
    """Streaming HTTP response (sync line/byte iteration).

    **Why this exists:** SSE and large downloads must not buffer the whole body.
    Use with ``HttpClient.stream`` as a context manager so the connection closes.

    Example:
        >>> from pyiv.http.response import StreamResponse
        >>> # Prefer MemoryHttpClient.stream in tests; see HttpClient docs.
        >>> isinstance(StreamResponse, type)
        True
    """

    def __init__(
        self,
        status_code: int,
        headers: Mapping[str, str],
        url: str,
        *,
        lines: Optional[Iterator[str]] = None,
        chunks: Optional[Iterator[bytes]] = None,
        close_fn: Optional[Any] = None,
    ) -> None:
        self._status_code = status_code
        self._headers = dict(headers)
        self._url = url
        self._lines = lines
        self._chunks = chunks
        self._close_fn = close_fn
        self._closed = False

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> Dict[str, str]:
        return dict(self._headers)

    @property
    def url(self) -> str:
        return self._url

    def raise_for_status(self) -> None:
        if 400 <= self._status_code < 600:
            # No buffered body for stream errors; empty content placeholder.
            buffered = HttpResponse(self._status_code, self._headers, b"", self._url)
            raise HttpStatusError(
                f"HTTP {self._status_code} for {self._url}",
                status_code=self._status_code,
                response=buffered,
            )

    def iter_lines(self) -> Iterator[str]:
        """Yield decoded text lines (without trailing newlines)."""
        if self._lines is None:
            raise RuntimeError("This stream does not support line iteration")
        for line in self._lines:
            yield line

    def iter_bytes(self, chunk_size: int = 65536) -> Iterator[bytes]:
        """Yield raw body chunks."""
        if self._chunks is None:
            raise RuntimeError("This stream does not support byte iteration")
        for chunk in self._chunks:
            yield chunk

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            if self._close_fn is not None:
                self._close_fn()

    def __enter__(self) -> "StreamResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncStreamResponse:
    """Streaming HTTP response (async line/byte iteration).

    **Why this exists:** Async call sites (SSE, long polls) need ``aiter_lines``
    without pulling in httpx. Pair with ``AsyncHttpClient.stream``.

    Example:
        >>> from pyiv.http.response import AsyncStreamResponse
        >>> isinstance(AsyncStreamResponse, type)
        True
    """

    def __init__(
        self,
        status_code: int,
        headers: Mapping[str, str],
        url: str,
        *,
        lines: Optional[AsyncIterator[str]] = None,
        chunks: Optional[AsyncIterator[bytes]] = None,
        close_fn: Optional[Any] = None,
    ) -> None:
        self._status_code = status_code
        self._headers = dict(headers)
        self._url = url
        self._lines = lines
        self._chunks = chunks
        self._close_fn = close_fn
        self._closed = False

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> Dict[str, str]:
        return dict(self._headers)

    @property
    def url(self) -> str:
        return self._url

    def raise_for_status(self) -> None:
        if 400 <= self._status_code < 600:
            buffered = HttpResponse(self._status_code, self._headers, b"", self._url)
            raise HttpStatusError(
                f"HTTP {self._status_code} for {self._url}",
                status_code=self._status_code,
                response=buffered,
            )

    async def aiter_lines(self) -> AsyncIterator[str]:
        if self._lines is None:
            raise RuntimeError("This stream does not support line iteration")
        async for line in self._lines:
            yield line

    async def aiter_bytes(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        if self._chunks is None:
            raise RuntimeError("This stream does not support byte iteration")
        async for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            if self._close_fn is not None:
                result = self._close_fn()
                if hasattr(result, "__await__"):
                    await result

    async def __aenter__(self) -> "AsyncStreamResponse":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
