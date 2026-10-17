"""Tests for pyiv.http clients (memory + urllib; no live network)."""

from __future__ import annotations

import asyncio
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from pyiv import Config, get_injector
from pyiv.http import (
    AsyncUrllibHttpClient,
    HttpClient,
    HttpError,
    HttpResponse,
    HttpStatusError,
    HttpTimeoutError,
    MemoryAsyncHttpClient,
    MemoryHttpClient,
    UrllibHttpClient,
)


class TestHttpResponse:
    def test_json_and_raise_ok(self):
        r = HttpResponse(200, {"Content-Type": "application/json"}, b'{"a": 1}', "http://x/")
        assert r.json() == {"a": 1}
        r.raise_for_status()

    def test_raise_for_status_error(self):
        r = HttpResponse(404, {}, b"missing", "http://x/y")
        with pytest.raises(HttpStatusError) as exc:
            r.raise_for_status()
        assert exc.value.status_code == 404
        assert exc.value.response.content == b"missing"


class TestMemoryHttpClient:
    def test_get_post_json_and_record(self):
        client = MemoryHttpClient()
        client.add("POST", "http://api.test/v1", json={"ok": True})
        resp = client.post("http://api.test/v1", json={"n": 1})
        assert resp.json() == {"ok": True}
        assert client.requests[0].method == "POST"
        assert b'"n": 1' in (client.requests[0].body or b"")

    def test_base_url_and_params(self):
        client = MemoryHttpClient(base_url="http://api.test")
        client.add("GET", "http://api.test/items?q=1", body=b"[]")
        assert client.get("/items", params={"q": 1}).text == "[]"

    def test_stream_lines(self):
        client = MemoryHttpClient()
        client.add(
            "POST",
            "http://api.test/stream",
            stream_lines=["data: hi", "data: [DONE]"],
        )
        with client.stream("POST", "http://api.test/stream") as stream:
            assert list(stream.iter_lines()) == ["data: hi", "data: [DONE]"]

    def test_di_binding(self):
        class C(Config):
            def configure(self):
                self.register(HttpClient, MemoryHttpClient)

        client = get_injector(C).inject(HttpClient)
        assert isinstance(client, MemoryHttpClient)
        client.add("GET", "http://t/", body=b"x")
        assert client.get("http://t/").content == b"x"


class TestMemoryAsyncHttpClient:
    def test_async_get_and_stream(self):
        client = MemoryAsyncHttpClient()
        client.add("GET", "http://t/", body=b"hi")
        client.add("POST", "http://t/s", stream_lines=["a", "b"])

        async def run():
            assert (await client.get("http://t/")).text == "hi"
            async with client.stream("POST", "http://t/s") as stream:
                lines = []
                async for line in stream.aiter_lines():
                    lines.append(line)
                assert lines == ["a", "b"]

        asyncio.run(run())


class TestUrllibHttpClient:
    def test_rejects_non_http(self):
        client = UrllibHttpClient()
        with pytest.raises(ValueError, match="Only http:// and https://"):
            client.get("ftp://example.com/")

    def test_https_only(self):
        client = UrllibHttpClient(https_only=True)
        with pytest.raises(ValueError, match="Only https://"):
            client.get("http://example.com/")

    @patch("pyiv.http.clients.urlopen")
    def test_successful_get(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.read.return_value = b"ok"
        mock_response.geturl.return_value = "http://example.com/"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = UrllibHttpClient(headers={"X-App": "pyiv"})
        resp = client.get("http://example.com/", headers={"Accept": "text/plain"})
        assert resp.status_code == 200
        assert resp.content == b"ok"
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("X-app") == "pyiv" or req.headers.get("X-App") == "pyiv"

    @patch("pyiv.http.clients.urlopen")
    def test_http_error_returns_response(self, mock_urlopen):
        err = HTTPError("http://example.com/x", 404, "Not Found", hdrs={}, fp=BytesIO(b"missing"))
        mock_urlopen.side_effect = err
        resp = UrllibHttpClient().get("http://example.com/x")
        assert resp.status_code == 404
        assert resp.content == b"missing"

    @patch("pyiv.http.clients.urlopen")
    def test_timeout_maps_to_http_timeout(self, mock_urlopen):
        mock_urlopen.side_effect = URLError(TimeoutError("timed out"))
        with pytest.raises(HttpTimeoutError):
            UrllibHttpClient().get("http://example.com/")

    @patch("pyiv.http.clients.urlopen")
    def test_url_error_maps_to_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("boom")
        with pytest.raises(HttpError, match="boom"):
            UrllibHttpClient().get("http://example.com/")

    @patch("pyiv.http.clients.urlopen")
    def test_json_post(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 201
        mock_response.headers = {}
        mock_response.read.return_value = b'{"id":1}'
        mock_response.geturl.return_value = "http://example.com/items"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        resp = UrllibHttpClient().post("http://example.com/items", json={"name": "a"})
        assert resp.json() == {"id": 1}
        req = mock_urlopen.call_args[0][0]
        assert req.data == b'{"name": "a"}'
        assert req.get_header("Content-type") == "application/json"

    @patch("pyiv.http.clients.urlopen")
    def test_stream_lines(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {}
        mock_response.geturl.return_value = "http://example.com/s"
        mock_response.readline.side_effect = [b"data: 1\n", b"data: 2\n", b""]
        mock_response.close = MagicMock()
        mock_urlopen.return_value = mock_response

        with UrllibHttpClient().stream("POST", "http://example.com/s", json={}) as stream:
            assert list(stream.iter_lines()) == ["data: 1", "data: 2"]
        mock_response.close.assert_called()


class TestAsyncUrllibHttpClient:
    def test_rejects_non_http(self):
        client = AsyncUrllibHttpClient()

        async def run():
            await client.get("ftp://example.com/")

        with pytest.raises(ValueError, match="Only http:// and https://"):
            asyncio.run(run())

    @patch("pyiv.http.clients.urlopen")
    def test_async_get(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"ok"
        mock_response.geturl.return_value = "http://example.com/"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        async def run():
            client = AsyncUrllibHttpClient()
            return await client.get("http://example.com/")

        assert asyncio.run(run()).content == b"ok"
