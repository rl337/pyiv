"""In-memory HTTP clients for tests (no network)."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from pyiv.http._util import apply_params, encode_body, join_url, merge_headers
from pyiv.http.base import AsyncHttpClient, HttpClient
from pyiv.http.response import AsyncStreamResponse, HttpResponse, StreamResponse

RouteHandler = Callable[["RecordedRequest"], Union[HttpResponse, "StreamReply"]]


@dataclass
class RecordedRequest:
    """A request captured by ``MemoryHttpClient`` / ``MemoryAsyncHttpClient``."""

    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None


@dataclass
class StreamReply:
    """Canned streaming body for memory clients."""

    status_code: int = 200
    headers: Mapping[str, str] = field(default_factory=dict)
    lines: Optional[List[str]] = None
    chunks: Optional[List[bytes]] = None
    url: str = ""


class _MemoryStore:
    """Shared route table / request log for sync and async memory clients."""

    def __init__(
        self, *, base_url: Optional[str] = None, headers: Optional[Mapping[str, str]] = None
    ):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.default_headers = dict(headers) if headers else {}
        self.requests: List[RecordedRequest] = []
        self._exact: Dict[Tuple[str, str], RouteHandler] = {}
        self._default: Optional[RouteHandler] = None

    def add(
        self,
        method: str,
        url: str,
        *,
        status_code: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        body: bytes = b"",
        json: Any = None,
        stream_lines: Optional[List[str]] = None,
        stream_chunks: Optional[List[bytes]] = None,
    ) -> None:
        """Register a canned response for ``METHOD`` + URL."""
        if json is not None:
            import json as json_mod

            body = json_mod.dumps(json).encode("utf-8")
            headers = dict(headers or {})
            headers.setdefault("Content-Type", "application/json")

        resp_headers = dict(headers or {})
        use_stream = stream_lines is not None or stream_chunks is not None

        def handler(req: RecordedRequest) -> Union[HttpResponse, StreamReply]:
            if use_stream:
                return StreamReply(
                    status_code=status_code,
                    headers=resp_headers,
                    lines=stream_lines,
                    chunks=stream_chunks,
                    url=req.url,
                )
            return HttpResponse(status_code, resp_headers, body, req.url)

        self._exact[(method.upper(), url)] = handler

    def set_default(self, handler: RouteHandler) -> None:
        self._default = handler

    def prepare(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]],
        params: Optional[Mapping[str, Any]],
        data: Optional[Union[str, bytes]],
        json: Any,
    ) -> RecordedRequest:
        full = apply_params(join_url(self.base_url, url), params)
        hdrs = merge_headers(self.default_headers, headers)
        body, hdrs = encode_body(data, json, hdrs)
        recorded = RecordedRequest(method.upper(), full, hdrs, body)
        self.requests.append(recorded)
        return recorded

    def resolve(self, recorded: RecordedRequest) -> Union[HttpResponse, StreamReply]:
        handler = self._exact.get((recorded.method, recorded.url))
        if handler is None and self.base_url:
            # Also try relative form if caller registered without base
            for (m, u), h in self._exact.items():
                if m == recorded.method and recorded.url.endswith(u):
                    handler = h
                    break
        if handler is None:
            handler = self._default
        if handler is None:
            return HttpResponse(404, {}, b"not found", recorded.url)
        return handler(recorded)


class MemoryHttpClient(HttpClient):
    """Sync HTTP client that returns canned responses (no network).

    **Why this exists:** Doctests and unit tests must not hit the network.
    Recorded requests make assertions easy.

    Example:
        >>> client = MemoryHttpClient()
        >>> client.add("POST", "http://api.test/v1", json={"ok": True})
        >>> client.post("http://api.test/v1", json={"n": 1}).json()
        {'ok': True}
        >>> client.requests[0].method
        'POST'
    """

    def __init__(self, base_url=None, headers=None) -> None:
        # Untyped optionals: Mapping/Dict annotations are not DI-injectable.
        self._store = _MemoryStore(base_url=base_url, headers=headers)

    @property
    def requests(self) -> List[RecordedRequest]:
        return self._store.requests

    def add(self, method: str, url: str, **kwargs: Any) -> None:
        """Register a canned response. See ``_MemoryStore.add``."""
        self._store.add(method, url, **kwargs)

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
        recorded = self._store.prepare(
            method, url, headers=headers, params=params, data=data, json=json
        )
        result = self._store.resolve(recorded)
        if isinstance(result, StreamReply):
            # Buffer stream reply for non-stream request API
            if result.lines is not None:
                content = ("\n".join(result.lines) + "\n").encode("utf-8")
            elif result.chunks is not None:
                content = b"".join(result.chunks)
            else:
                content = b""
            return HttpResponse(result.status_code, result.headers, content, recorded.url)
        return result

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
        recorded = self._store.prepare(
            method, url, headers=headers, params=params, data=data, json=json
        )
        result = self._store.resolve(recorded)
        if isinstance(result, HttpResponse):
            text = result.text
            lines = text.splitlines()
            chunks = [result.content] if result.content else []
            stream = StreamResponse(
                result.status_code,
                result.headers,
                result.url,
                lines=iter(lines),
                chunks=iter(chunks),
            )
        else:
            stream = StreamResponse(
                result.status_code,
                result.headers,
                result.url or recorded.url,
                lines=iter(result.lines or []),
                chunks=iter(result.chunks or []),
            )
        try:
            yield stream
        finally:
            stream.close()


class MemoryAsyncHttpClient(AsyncHttpClient):
    """Async memory HTTP client (same canned routes as ``MemoryHttpClient``).

    **Why this exists:** Async unit tests need the same fake without a live
    event-loop network stack.

    Example:
        >>> import asyncio
        >>> client = MemoryAsyncHttpClient()
        >>> client.add("GET", "http://t/", body=b"x")
        >>> asyncio.run(client.get("http://t/")).content
        b'x'
    """

    def __init__(self, base_url=None, headers=None, sync_client=None) -> None:
        self._sync = sync_client or MemoryHttpClient(base_url=base_url, headers=headers)

    @property
    def requests(self) -> List[RecordedRequest]:
        return self._sync.requests

    def add(self, method: str, url: str, **kwargs: Any) -> None:
        self._sync.add(method, url, **kwargs)

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
        return self._sync.request(
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
        with self._sync.stream(
            method,
            url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        ) as sync_stream:
            lines = list(sync_stream.iter_lines())
            chunks = list(sync_stream.iter_bytes())

            async def _lines() -> AsyncIterator[str]:
                for line in lines:
                    yield line

            async def _chunks() -> AsyncIterator[bytes]:
                for chunk in chunks:
                    yield chunk

            stream = AsyncStreamResponse(
                sync_stream.status_code,
                sync_stream.headers,
                sync_stream.url,
                lines=_lines(),
                chunks=_chunks(),
            )
            try:
                yield stream
            finally:
                await stream.aclose()
