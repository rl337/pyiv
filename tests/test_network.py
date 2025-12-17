"""Tests for NetworkClient interface and dependency injection integration."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyiv import ChainType, Config, get_injector
from pyiv.network import HTTPClient, HTTPSClient, NetworkClient


class TestNetworkClientInterface:
    """Tests for the NetworkClient base interface."""

    def test_network_client_is_abstract(self):
        """Test that NetworkClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            NetworkClient()  # type: ignore[abstract]

    def test_network_client_handler_type(self):
        """Test that NetworkClient implementations have handler_type property."""
        client = HTTPClient()
        assert client.handler_type == "http"
        assert client.chain_type == ChainType.NETWORK_CLIENT

        client = HTTPSClient()
        assert client.handler_type == "https"
        assert client.chain_type == ChainType.NETWORK_CLIENT

    def test_http_client_request_invalid_url(self):
        """Test HTTPClient raises ValueError for non-HTTP URLs."""
        client = HTTPClient()
        with pytest.raises(ValueError, match="HTTPClient only supports http:// and https:// URLs"):
            client.request("GET", "ftp://example.com")

    def test_https_client_request_invalid_url(self):
        """Test HTTPSClient raises ValueError for non-HTTPS URLs."""
        client = HTTPSClient()
        with pytest.raises(ValueError, match="HTTPSClient only supports https:// URLs"):
            client.request("GET", "http://example.com")

    @patch("pyiv.network.clients.urlopen")
    def test_http_client_request_success(self, mock_urlopen):
        """Test HTTPClient makes successful requests."""
        # Mock response
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {"Content-Type": "text/html", "Content-Length": "123"}
        mock_response.read.return_value = b"<html>Hello</html>"
        mock_response.geturl.return_value = "http://example.com"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = HTTPClient()
        response = client.request("GET", "http://example.com")

        assert response["status"] == 200
        assert response["headers"]["Content-Type"] == "text/html"
        assert response["body"] == b"<html>Hello</html>"
        assert response["url"] == "http://example.com"

        # Verify request was made correctly
        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args
        assert call_args[0][0].full_url == "http://example.com"
        assert call_args[0][0].method == "GET"

    @patch("pyiv.network.clients.urlopen")
    def test_https_client_request_success(self, mock_urlopen):
        """Test HTTPSClient makes successful requests."""
        # Mock response
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.read.return_value = b'{"key": "value"}'
        mock_response.geturl.return_value = "https://example.com"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = HTTPSClient()
        response = client.request("GET", "https://example.com")

        assert response["status"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["body"] == b'{"key": "value"}'
        assert response["url"] == "https://example.com"

    @patch("pyiv.network.clients.urlopen")
    def test_http_client_request_with_headers(self, mock_urlopen):
        """Test HTTPClient includes custom headers in requests."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"OK"
        mock_response.geturl.return_value = "http://example.com"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = HTTPClient()
        headers = {"Authorization": "Bearer token123", "User-Agent": "pyiv/1.0"}
        client.request("GET", "http://example.com", headers=headers)

        # Verify headers were added to request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        # Check headers using header_items() which returns all headers
        header_dict = dict(request.header_items())
        # urllib normalizes header names, so check case-insensitively
        assert "authorization" in [k.lower() for k in header_dict.keys()]
        assert "user-agent" in [k.lower() for k in header_dict.keys()]
        # Verify values (check case-insensitively)
        for key, value in header_dict.items():
            if key.lower() == "authorization":
                assert value == "Bearer token123"
            elif key.lower() == "user-agent":
                assert value == "pyiv/1.0"

    @patch("pyiv.network.clients.urlopen")
    def test_http_client_request_with_data(self, mock_urlopen):
        """Test HTTPClient sends request body data."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 201
        mock_response.headers = {}
        mock_response.read.return_value = b'{"id": 123}'
        mock_response.geturl.return_value = "http://example.com/api"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = HTTPClient()
        data = '{"name": "test"}'
        response = client.request("POST", "http://example.com/api", data=data)

        assert response["status"] == 201
        # Verify data was sent
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.data == b'{"name": "test"}'

    @patch("pyiv.network.clients.urlopen")
    def test_http_client_request_with_timeout(self, mock_urlopen):
        """Test HTTPClient respects timeout parameter."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"OK"
        mock_response.geturl.return_value = "http://example.com"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = HTTPClient()
        client.request("GET", "http://example.com", timeout=5.0)

        # Verify timeout was passed
        call_args = mock_urlopen.call_args
        assert call_args[1]["timeout"] == 5.0

    @patch("pyiv.network.clients.urlopen")
    def test_http_client_handles_http_error(self, mock_urlopen):
        """Test HTTPClient handles HTTP error responses."""
        from urllib.error import HTTPError

        # Mock HTTPError (4xx, 5xx)
        mock_error = HTTPError(
            "http://example.com",
            404,
            "Not Found",
            {"Content-Type": "text/html"},
            None,
        )
        mock_error.read = MagicMock(return_value=b"<html>Not Found</html>")
        mock_urlopen.side_effect = mock_error

        client = HTTPClient()
        response = client.request("GET", "http://example.com")

        assert response["status"] == 404
        assert response["headers"]["Content-Type"] == "text/html"
        assert response["body"] == b"<html>Not Found</html>"

    def test_network_client_handle_with_tuple(self):
        """Test NetworkClient.handle() accepts tuple format."""
        with patch("pyiv.network.clients.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.getcode.return_value = 200
            mock_response.headers = {}
            mock_response.read.return_value = b"OK"
            mock_response.geturl.return_value = "http://example.com"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            client = HTTPClient()
            response = client.handle(("GET", "http://example.com"))

            assert response["status"] == 200

    def test_network_client_handle_with_dict(self):
        """Test NetworkClient.handle() accepts dict format."""
        with patch("pyiv.network.clients.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.getcode.return_value = 200
            mock_response.headers = {}
            mock_response.read.return_value = b"OK"
            mock_response.geturl.return_value = "http://example.com"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            client = HTTPClient()
            request = {
                "method": "GET",
                "url": "http://example.com",
                "headers": {"X-Custom": "value"},
            }
            response = client.handle(request)

            assert response["status"] == 200

    def test_network_client_handle_with_string(self):
        """Test NetworkClient.handle() accepts URL string."""
        with patch("pyiv.network.clients.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.getcode.return_value = 200
            mock_response.headers = {}
            mock_response.read.return_value = b"OK"
            mock_response.geturl.return_value = "http://example.com"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            client = HTTPClient()
            response = client.handle("http://example.com")

            assert response["status"] == 200


class TestNetworkClientDI:
    """Tests for NetworkClient dependency injection integration."""

    def test_register_network_client_by_type(self):
        """Test registering network client by handler type."""
        from pyiv.network import HTTPClient

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler(ChainType.NETWORK_CLIENT, "http", HTTPClient)

        injector = get_injector(MyConfig)
        client = injector.inject_chain_handler(ChainType.NETWORK_CLIENT, "http")

        assert isinstance(client, HTTPClient)
        assert client.handler_type == "http"

    def test_register_network_client_by_name(self):
        """Test registering network client by name."""
        from pyiv.network import HTTPClient, HTTPSClient

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler_by_name(
                    ChainType.NETWORK_CLIENT, "api-client", HTTPClient, "http"
                )
                self.register_chain_handler_by_name(
                    ChainType.NETWORK_CLIENT, "secure-client", HTTPSClient, "https"
                )

        injector = get_injector(MyConfig)
        api_client = injector.inject_chain_handler_by_name(ChainType.NETWORK_CLIENT, "api-client")
        secure_client = injector.inject_chain_handler_by_name(
            ChainType.NETWORK_CLIENT, "secure-client"
        )

        assert isinstance(api_client, HTTPClient)
        assert api_client.handler_type == "http"
        assert isinstance(secure_client, HTTPSClient)
        assert secure_client.handler_type == "https"

    def test_register_network_client_instance(self):
        """Test registering pre-created network client instance."""
        client = HTTPClient()

        class MyConfig(Config):
            def configure(self):
                self.register_chain_handler_instance(ChainType.NETWORK_CLIENT, "http", client)

        injector = get_injector(MyConfig)
        injected_client = injector.inject_chain_handler(ChainType.NETWORK_CLIENT, "http")

        assert injected_client is client  # Same instance

    def test_multiple_network_clients_same_type(self):
        """Test registering multiple network clients with same handler type."""
        from pyiv.network import HTTPClient

        class CustomHTTPClient(HTTPClient):
            """Custom HTTP client with additional features."""

            pass

        class MyConfig(Config):
            def configure(self):
                # Register default HTTP client
                self.register_chain_handler(ChainType.NETWORK_CLIENT, "http", HTTPClient)
                # Register custom HTTP client by name
                self.register_chain_handler_by_name(
                    ChainType.NETWORK_CLIENT, "custom-http", CustomHTTPClient, "http"
                )

        injector = get_injector(MyConfig)
        default_client = injector.inject_chain_handler(ChainType.NETWORK_CLIENT, "http")
        custom_client = injector.inject_chain_handler_by_name(
            ChainType.NETWORK_CLIENT, "custom-http"
        )

        assert isinstance(default_client, HTTPClient)
        assert isinstance(custom_client, CustomHTTPClient)
        assert default_client.handler_type == "http"
        assert custom_client.handler_type == "http"

