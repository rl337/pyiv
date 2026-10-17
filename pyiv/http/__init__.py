"""Injectable HTTP clients for pyiv (stdlib urllib; zero third-party deps).

This module provides typed sync and async HTTP client interfaces, a urllib
implementation, and in-memory test doubles.

**What Problem Does This Solve?**

Hard-coding urllib or a third-party HTTP stack at every call site makes
testing and DI awkward. Apps need ``json=``, status handling, and optional
SSE-style streaming behind an injectable type — without pulling requests or
httpx into core.

**Real-World Use Cases:**
- Inject ``HttpClient`` / ``AsyncHttpClient`` into services and adapters
- Unit-test with ``MemoryHttpClient`` (no network)
- Stream SSE lines without buffering the whole body

Architecture:
 - ``HttpClient`` / ``AsyncHttpClient``: injectable ABCs
 - ``UrllibHttpClient`` / ``AsyncUrllibHttpClient``: stdlib production impls
 - ``MemoryHttpClient`` / ``MemoryAsyncHttpClient``: test doubles
 - ``HttpResponse`` / stream responses + ``HttpError`` hierarchy

Usage:

    >>> from pyiv import Config, get_injector
    >>> from pyiv.http import HttpClient, MemoryHttpClient
    >>> class ApiConfig(Config):
    ...     def configure(self):
    ...         self.register(HttpClient, MemoryHttpClient)
    >>> client = get_injector(ApiConfig).inject(HttpClient)
    >>> client.add("GET", "http://example.test/", body=b"hi")
    >>> client.get("http://example.test/").text
    'hi'
"""

from pyiv.http.base import AsyncHttpClient, HttpClient
from pyiv.http.clients import AsyncUrllibHttpClient, UrllibHttpClient
from pyiv.http.errors import HttpError, HttpStatusError, HttpTimeoutError
from pyiv.http.memory import MemoryAsyncHttpClient, MemoryHttpClient, RecordedRequest, StreamReply
from pyiv.http.response import AsyncStreamResponse, HttpResponse, StreamResponse

__all__ = [
    "HttpClient",
    "AsyncHttpClient",
    "HttpResponse",
    "StreamResponse",
    "AsyncStreamResponse",
    "HttpError",
    "HttpTimeoutError",
    "HttpStatusError",
    "UrllibHttpClient",
    "AsyncUrllibHttpClient",
    "MemoryHttpClient",
    "MemoryAsyncHttpClient",
    "RecordedRequest",
    "StreamReply",
]
