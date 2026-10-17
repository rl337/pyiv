"""Internal helpers for HTTP clients (not part of the public API)."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional, Tuple, Union
from urllib.parse import urlencode, urljoin, urlparse


def join_url(base_url: Optional[str], url: str) -> str:
    """Resolve ``url`` against optional ``base_url`` (absolute urls win)."""
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        return url
    if not base_url:
        return url
    base = base_url if base_url.endswith("/") else base_url + "/"
    return urljoin(base, url.lstrip("/"))


def apply_params(url: str, params: Optional[Mapping[str, Any]]) -> str:
    if not params:
        return url
    query = urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
    if not query:
        return url
    sep = "&" if ("?" in url) else "?"
    return f"{url}{sep}{query}"


def merge_headers(
    default_headers: Optional[Mapping[str, str]],
    headers: Optional[Mapping[str, str]],
) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    if default_headers:
        merged.update(default_headers)
    if headers:
        merged.update(headers)
    return merged


def encode_body(
    data: Optional[Union[str, bytes]],
    json_body: Any,
    headers: Dict[str, str],
) -> Tuple[Optional[bytes], Dict[str, str]]:
    """Return ``(body_bytes, headers)``; sets Content-Type for JSON when needed."""
    if json_body is not None and data is not None:
        raise ValueError("Pass only one of data= or json=")
    out_headers = dict(headers)
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        out_headers.setdefault("Content-Type", "application/json")
        return body, out_headers
    if data is None:
        return None, out_headers
    if isinstance(data, str):
        return data.encode("utf-8"), out_headers
    return data, out_headers


def require_http_scheme(url: str, *, https_only: bool = False) -> None:
    scheme = urlparse(url).scheme
    if https_only:
        if scheme != "https":
            raise ValueError(f"Only https:// URLs are allowed, got: {url}")
    elif scheme not in ("http", "https"):
        raise ValueError(f"Only http:// and https:// URLs are allowed, got: {url}")
