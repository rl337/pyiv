"""Tests for pyiv-common RequestsClient. Mocks requests; no live network."""

from unittest.mock import MagicMock, patch

import pytest

from pyiv import ChainType, Config, get_injector
from pyiv_common.network import RequestsClient


class TestRequestsClient:
    def test_handler_type(self):
        client = RequestsClient()
        assert client.handler_type == "http"
        assert client.chain_type == ChainType.NETWORK_CLIENT

    def test_rejects_non_http_url(self):
        client = RequestsClient()
        with pytest.raises(ValueError, match="RequestsClient only supports http:// and https://"):
            client.request("GET", "ftp://example.com")

    @patch("pyiv_common.network.requests.request")
    def test_get_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = b"<html>Hello</html>"
        mock_response.url = "http://example.com"
        mock_request.return_value = mock_response

        client = RequestsClient()
        response = client.request("GET", "http://example.com")

        assert response["status"] == 200
        assert response["headers"]["Content-Type"] == "text/html"
        assert response["body"] == b"<html>Hello</html>"
        assert response["url"] == "http://example.com"
        mock_request.assert_called_once()
        kwargs = mock_request.call_args.kwargs
        assert kwargs["method"] == "GET"
        assert kwargs["url"] == "http://example.com"

    @patch("pyiv_common.network.requests.request")
    def test_https_and_headers_and_timeout(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.url = "https://example.com/api"
        mock_request.return_value = mock_response

        client = RequestsClient()
        client.request(
            "POST",
            "https://example.com/api",
            headers={"X-Test": "1"},
            data="payload",
            timeout=5.0,
        )

        kwargs = mock_request.call_args.kwargs
        assert kwargs["method"] == "POST"
        assert kwargs["headers"] == {"X-Test": "1"}
        assert kwargs["data"] == b"payload"
        assert kwargs["timeout"] == 5.0

    @patch("pyiv_common.network.requests.request")
    def test_inject_chain_handler(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b"ok"
        mock_response.url = "http://example.com"
        mock_request.return_value = mock_response

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.NETWORK_CLIENT, "http", RequestsClient)

        injector = get_injector(MyConfig)
        client = injector.inject_chain_handler(ChainType.NETWORK_CLIENT, "http")
        assert isinstance(client, RequestsClient)
        result = client.request("GET", "http://example.com")
        assert result["status"] == 200
