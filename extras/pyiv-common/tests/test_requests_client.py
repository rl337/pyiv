"""Tests for pyiv-common RequestsHttpClient. Mocks requests; no live network."""

from unittest.mock import MagicMock, patch

import pytest

from pyiv import Config, get_injector
from pyiv.http import HttpClient
from pyiv_common.network import RequestsHttpClient


class TestRequestsHttpClient:
    def test_rejects_non_http(self):
        client = RequestsHttpClient()
        with pytest.raises(ValueError, match="Only http:// and https://"):
            client.get("ftp://example.com/")

    @patch("pyiv_common.network.requests.Session.request")
    def test_get_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.content = b"ok"
        mock_response.url = "http://example.com/"
        mock_request.return_value = mock_response

        client = RequestsHttpClient(headers={"X-App": "pyiv"})
        resp = client.get("http://example.com/")
        assert resp.status_code == 200
        assert resp.content == b"ok"
        kwargs = mock_request.call_args.kwargs
        assert kwargs["headers"]["X-App"] == "pyiv"

    @patch("pyiv_common.network.requests.Session.request")
    def test_json_post(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.content = b'{"id":1}'
        mock_response.url = "http://example.com/items"
        mock_request.return_value = mock_response

        resp = RequestsHttpClient().post("http://example.com/items", json={"name": "a"})
        assert resp.json() == {"id": 1}
        kwargs = mock_request.call_args.kwargs
        assert kwargs["data"] == b'{"name": "a"}'
        assert kwargs["headers"]["Content-Type"] == "application/json"

    def test_di_binding(self):
        class C(Config):
            def configure(self):
                self.register(HttpClient, RequestsHttpClient)

        client = get_injector(C).inject(HttpClient)
        assert isinstance(client, RequestsHttpClient)
