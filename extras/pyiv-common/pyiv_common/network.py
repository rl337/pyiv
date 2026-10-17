"""requests-backed HttpClient for pyiv.

This module provides ``RequestsHttpClient``, a ``pyiv.http.HttpClient`` that
uses the requests library and an optional ``Session``. Stdlib urllib clients
stay in core.

**What Problem Does This Solve?**

Many apps already depend on requests (sessions, adapters, timeouts). Core
pyiv cannot import it. This extra implements the same ``HttpClient`` shape
as ``UrllibHttpClient`` so you can swap transports in Config.

**Real-World Use Cases:**
- Inject an HTTP client that reuses a ``requests.Session``
- Prefer requests connection pooling while keeping call sites on ``HttpClient``

Example:

    >>> from pyiv_common.network import RequestsHttpClient
    >>> client = RequestsHttpClient()
    >>> client.request("GET", "ftp://example.com/")
    Traceback (most recent call last):
        ...
    ValueError: Only http:// and https:// URLs are allowed, got: ftp://example.com/
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional, Union

import requests  # type: ignore[import-untyped]

from pyiv.http._util import apply_params, encode_body, join_url, merge_headers, require_http_scheme
from pyiv.http.base import HttpClient
from pyiv.http.errors import HttpError, HttpTimeoutError
from pyiv.http.response import HttpResponse, StreamResponse


class RequestsHttpClient(HttpClient):
    """HTTP(S) client using the requests library.

    **Why this exists:** Teams that already standardize on requests can bind
    this implementation to ``HttpClient`` without changing call sites that
    expect ``json=``, ``raise_for_status``, or streaming lines.

    Example:
        >>> from pyiv import Config, get_injector
        >>> from pyiv.http import HttpClient
        >>> from pyiv_common.network import RequestsHttpClient
        >>> class MyConfig(Config):
        ...     def configure(self):
        ...         self.register(HttpClient, RequestsHttpClient)
        >>> injector = get_injector(MyConfig)
        >>> isinstance(injector.inject(HttpClient), RequestsHttpClient)
        True
    """

    def __init__(
        self, base_url=None, headers=None, timeout=None, https_only=False, session=None
    ) -> None:
        # Untyped optionals so Config can ``register(HttpClient, RequestsHttpClient)``.
        self._base_url = base_url.rstrip("/") if base_url else None
        self._headers = dict(headers) if headers else {}
        self._timeout = timeout
        self._https_only = bool(https_only)
        self._session = session or requests.Session()
        self._owns_session = session is None

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
    ):
        full = apply_params(join_url(self._base_url, url), params)
        require_http_scheme(full, https_only=self._https_only)
        hdrs = merge_headers(self._headers, headers)
        body, hdrs = encode_body(data, json, hdrs)
        to = self._timeout if timeout is None else timeout
        return method.upper(), full, hdrs, body, to

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
        method_u, full, hdrs, body, to = self._prepare(
            method, url, headers=headers, params=params, data=data, json=json, timeout=timeout
        )
        try:
            response = self._session.request(
                method=method_u,
                url=full,
                headers=hdrs,
                data=body,
                timeout=to,
            )
        except requests.Timeout as exc:
            raise HttpTimeoutError(f"Timed out requesting {full}") from exc
        except requests.RequestException as exc:
            raise HttpError(f"Request to {full} failed: {exc}") from exc
        return HttpResponse(
            response.status_code,
            dict(response.headers),
            response.content,
            response.url,
        )

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
        method_u, full, hdrs, body, to = self._prepare(
            method, url, headers=headers, params=params, data=data, json=json, timeout=timeout
        )
        try:
            response = self._session.request(
                method=method_u,
                url=full,
                headers=hdrs,
                data=body,
                timeout=to,
                stream=True,
            )
        except requests.Timeout as exc:
            raise HttpTimeoutError(f"Timed out requesting {full}") from exc
        except requests.RequestException as exc:
            raise HttpError(f"Request to {full} failed: {exc}") from exc

        def _lines() -> Iterator[str]:
            for line in response.iter_lines(decode_unicode=True):
                if line is None:
                    continue
                yield line if isinstance(line, str) else line.decode("utf-8", errors="replace")

        def _chunks(chunk_size: int = 65536) -> Iterator[bytes]:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    yield chunk

        stream = StreamResponse(
            response.status_code,
            dict(response.headers),
            response.url,
            lines=_lines(),
            chunks=_chunks(),
            close_fn=response.close,
        )
        try:
            yield stream
        finally:
            stream.close()

    def close(self) -> None:
        if self._owns_session:
            self._session.close()


# Backward-facing alias used in older pyiv-common docs snippets.
RequestsClient = RequestsHttpClient
