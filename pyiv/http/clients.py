"""Stdlib urllib HTTP client implementations (sync and async)."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Dict, Iterator, Mapping, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pyiv.http._util import apply_params, encode_body, join_url, merge_headers, require_http_scheme
from pyiv.http.base import AsyncHttpClient, HttpClient
from pyiv.http.errors import HttpError, HttpTimeoutError
from pyiv.http.response import AsyncStreamResponse, HttpResponse, StreamResponse


def _run_sync(func, *args, **kwargs):
    """Run ``func`` in a thread pool (Python 3.8-compatible ``to_thread``)."""
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, lambda: func(*args, **kwargs))


def _headers_from_urllib(response: Any) -> Dict[str, str]:
    if response.headers is None:
        return {}
    return dict(response.headers.items())


class UrllibHttpClient(HttpClient):
    """HTTP(S) client using stdlib ``urllib``.

    **Why this exists:** Core pyiv stays zero-dependency. This is the default
    production ``HttpClient`` when you do not want requests/httpx.

    Example:
        >>> client = UrllibHttpClient()
        >>> client.request("GET", "ftp://example.com/")
        Traceback (most recent call last):
            ...
        ValueError: Only http:// and https:// URLs are allowed, got: ftp://example.com/
    """

    def __init__(self, base_url=None, headers=None, timeout=None, https_only=False) -> None:
        # Untyped optionals so Config can ``register(HttpClient, UrllibHttpClient)``.
        self._base_url = base_url.rstrip("/") if base_url else None
        self._headers = dict(headers) if headers else {}
        self._timeout = timeout
        self._https_only = bool(https_only)

    def _prepare(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]],
        params: Optional[Mapping[str, Any]],
        data: Optional[Union[str, bytes]],
        json: Any,
        timeout: Optional[float],
    ) -> tuple:
        full = apply_params(join_url(self._base_url, url), params)
        require_http_scheme(full, https_only=self._https_only)
        hdrs = merge_headers(self._headers, headers)
        body, hdrs = encode_body(data, json, hdrs)
        to = self._timeout if timeout is None else timeout
        req = Request(full, data=body, method=method.upper())
        for key, value in hdrs.items():
            req.add_header(key, value)
        return req, full, to

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
        req, full, to = self._prepare(
            method, url, headers=headers, params=params, data=data, json=json, timeout=timeout
        )
        try:
            with urlopen(req, timeout=to) as response:
                return HttpResponse(
                    response.getcode(),
                    _headers_from_urllib(response),
                    response.read(),
                    response.geturl(),
                )
        except HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            return HttpResponse(
                exc.code,
                dict(exc.headers.items()) if exc.headers else {},
                body,
                full,
            )
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise HttpTimeoutError(f"Timed out requesting {full}") from exc
            raise HttpError(f"Request to {full} failed: {exc}") from exc
        except TimeoutError as exc:
            raise HttpTimeoutError(f"Timed out requesting {full}") from exc

    @contextmanager
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
    ) -> Iterator[StreamResponse]:
        req, full, to = self._prepare(
            method, url, headers=headers, params=params, data=data, json=json, timeout=timeout
        )
        try:
            response = urlopen(req, timeout=to)
        except HTTPError as exc:
            # HTTPError is also a file-like response
            response = exc
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise HttpTimeoutError(f"Timed out requesting {full}") from exc
            raise HttpError(f"Request to {full} failed: {exc}") from exc

        status = (
            response.getcode() if hasattr(response, "getcode") else getattr(response, "code", 0)
        )
        resp_headers = _headers_from_urllib(response)
        final_url = response.geturl() if hasattr(response, "geturl") else full

        def _lines() -> Iterator[str]:
            while True:
                raw = response.readline()
                if not raw:
                    break
                if isinstance(raw, bytes):
                    yield raw.decode("utf-8", errors="replace").rstrip("\r\n")
                else:
                    yield str(raw).rstrip("\r\n")

        def _chunks(chunk_size: int = 65536) -> Iterator[bytes]:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                yield chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")

        stream = StreamResponse(
            status,
            resp_headers,
            final_url,
            lines=_lines(),
            chunks=_chunks(),
            close_fn=response.close,
        )
        try:
            yield stream
        finally:
            stream.close()


class AsyncUrllibHttpClient(AsyncHttpClient):
    """Async HTTP client that runs ``UrllibHttpClient`` in a thread pool.

    **Why this exists:** Async apps can inject an HTTP client without httpx.
    Blocking urllib I/O runs via ``run_in_executor`` so the event loop stays free.

    Example:
        >>> client = AsyncUrllibHttpClient()
        >>> # Invalid schemes fail before any network I/O:
        >>> import asyncio
        >>> async def _bad():
        ...     await client.get("ftp://example.com/")
        >>> asyncio.run(_bad())
        Traceback (most recent call last):
            ...
        ValueError: Only http:// and https:// URLs are allowed, got: ftp://example.com/
    """

    def __init__(
        self, base_url=None, headers=None, timeout=None, https_only=False, sync_client=None
    ) -> None:
        self._sync = sync_client or UrllibHttpClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            https_only=https_only,
        )

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
        return await _run_sync(
            self._sync.request,
            method,
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        json: Any = None,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[AsyncStreamResponse]:
        # Open the urllib stream in a worker thread; iterate lines via executor.
        cm = self._sync.stream(
            method,
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )
        sync_stream = await _run_sync(cm.__enter__)

        def _next_or_sentinel(iterator: Iterator[Any], sentinel: object) -> Any:
            try:
                return next(iterator)
            except StopIteration:
                return sentinel

        async def _lines() -> AsyncIterator[str]:
            it = sync_stream.iter_lines()
            sentinel = object()
            while True:
                line = await _run_sync(_next_or_sentinel, it, sentinel)
                if line is sentinel:
                    break
                yield line

        async def _chunks(chunk_size: int = 65536) -> AsyncIterator[bytes]:
            it = sync_stream.iter_bytes(chunk_size)
            sentinel = object()
            while True:
                chunk = await _run_sync(_next_or_sentinel, it, sentinel)
                if chunk is sentinel:
                    break
                yield chunk

        async def _close() -> None:
            await _run_sync(cm.__exit__, None, None, None)

        async_stream = AsyncStreamResponse(
            sync_stream.status_code,
            sync_stream.headers,
            sync_stream.url,
            lines=_lines(),
            chunks=_chunks(),
            close_fn=_close,
        )
        try:
            yield async_stream
        finally:
            await async_stream.aclose()

    async def aclose(self) -> None:
        self._sync.close()
