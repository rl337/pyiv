"""HTTP client errors for pyiv.

Library-neutral exceptions so call sites and adapters can map timeouts and
status failures without depending on urllib, requests, or httpx exception types.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyiv.http.response import HttpResponse


class HttpError(Exception):
    """Base error for injectable HTTP clients.

    **Why this exists:** Call sites should catch one hierarchy whether the
    transport is urllib, requests, or a test double — not library-specific
    exception types.

    Example:
        >>> from pyiv.http.errors import HttpError, HttpTimeoutError
        >>> isinstance(HttpTimeoutError("late"), HttpError)
        True
    """


class HttpTimeoutError(HttpError):
    """The request exceeded its timeout.

    **Why this exists:** Judge / inference callers often map timeouts to a
    distinct domain error (unavailable vs malformed response).

    Example:
        >>> from pyiv.http.errors import HttpTimeoutError
        >>> raise HttpTimeoutError("timed out")
        Traceback (most recent call last):
            ...
        pyiv.http.errors.HttpTimeoutError: timed out
    """


class HttpStatusError(HttpError):
    """The response status indicated failure (``raise_for_status``).

    **Why this exists:** Callers need the status code and response body after
    a failed request without re-parsing opaque exception strings.

    Example:
        >>> from pyiv.http.errors import HttpStatusError
        >>> from pyiv.http.response import HttpResponse
        >>> resp = HttpResponse(404, {}, b"missing", "http://x/y")
        >>> err = HttpStatusError("not found", status_code=404, response=resp)
        >>> err.status_code
        404
        >>> err.response.content
        b'missing'
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response: "HttpResponse",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response
