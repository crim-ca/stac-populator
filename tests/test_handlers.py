"""Tests for authentication handlers."""

from __future__ import annotations

from unittest.mock import patch

import requests

from STACpopulator.auth.handlers import (
    AuthHandler,
    BasicAuthHandler,
    BearerAuthHandler,
    CookieAuthHandler,
    DigestAuthHandler,
    ProxyAuthHandler,
)

API_AUTH_URI = "https://api.example.com/auth"
API_RESOURCE_URI = "https://api.example.com/protected/resource"


class TestBasicAuthHandler:
    """Tests for BasicAuthHandler as requests auth."""

    def test_adds_authorization_header(self, requests_mock):
        requests_mock.get(API_RESOURCE_URI)

        handler = BasicAuthHandler(username="user", password="pass")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert requests_mock.called
        # Basic auth is base64("user:pass") = "dXNlcjpwYXNz"
        assert requests_mock.last_request.headers["Authorization"] == "Basic dXNlcjpwYXNz"


class TestDigestAuthHandler:
    """Tests for DigestAuthHandler as requests auth."""

    def test_handles_digest_challenge(self, requests_mock):
        # Digest auth requires a 401 challenge first
        requests_mock.get(
            API_RESOURCE_URI,
            [
                {
                    "status_code": 401,
                    "headers": {"WWW-Authenticate": 'Digest realm="test", nonce="abc123", qop="auth"'},
                },
                {"status_code": 200, "text": "OK"},
            ],
        )

        handler = DigestAuthHandler(username="user", password="pass")
        response = requests.get(API_RESOURCE_URI, auth=handler)

        assert response.status_code == 200
        assert requests_mock.call_count == 2
        # Second request should have Digest auth header
        assert "Digest" in requests_mock.last_request.headers["Authorization"]


class TestProxyAuthHandler:
    """Tests for ProxyAuthHandler as requests auth."""

    def test_adds_proxy_authorization_header(self, requests_mock):
        requests_mock.get(API_RESOURCE_URI)

        handler = ProxyAuthHandler(username="proxy_user", password="proxy_pass")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert requests_mock.called
        assert "Basic" in requests_mock.last_request.headers["Proxy-Authorization"]


class TestBearerAuthHandler:
    """Tests for BearerAuthHandler as requests auth."""

    def test_with_direct_token(self, requests_mock):
        requests_mock.get(API_RESOURCE_URI)

        handler = BearerAuthHandler(token="access-token")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert requests_mock.called
        assert requests_mock.last_request.headers["Authorization"] == "Bearer access-token"

    def test_authenticates_from_url(self, requests_mock, mock_auth_response):
        requests_mock.get(API_RESOURCE_URI)

        with patch("STACpopulator.auth.handlers.make_request") as mock_make_request:
            mock_make_request.return_value = mock_auth_response({"access_token": "access-token"})

            handler = BearerAuthHandler(url=API_AUTH_URI, method="POST")
            requests.get(API_RESOURCE_URI, auth=handler)

            assert requests_mock.last_request.headers["Authorization"] == "Bearer access-token"
            mock_make_request.assert_called_once()

    def test_no_header_on_auth_failure(self, requests_mock, mock_auth_response):
        requests_mock.get(API_RESOURCE_URI)

        with patch("STACpopulator.auth.handlers.make_request") as mock_make_request:
            mock_make_request.return_value = mock_auth_response(status_code=401)

            handler = BearerAuthHandler(url=API_AUTH_URI, method="GET")
            requests.get(API_RESOURCE_URI, auth=handler)

            assert "Authorization" not in requests_mock.last_request.headers


class TestCookieAuthHandler:
    """Tests for CookieAuthHandler as requests auth."""

    def test_with_string_token(self, requests_mock):
        requests_mock.get(API_RESOURCE_URI)

        handler = CookieAuthHandler(token="session_id=abc123")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert requests_mock.last_request.headers["Cookie"] == "session_id=abc123"

    def test_with_dict_token(self, requests_mock):
        requests_mock.get(API_RESOURCE_URI)

        handler = CookieAuthHandler(token={"session_id": "abc123", "user": "john"})
        requests.get(API_RESOURCE_URI, auth=handler)

        cookie_header = requests_mock.last_request.headers["Cookie"]
        assert "session_id=abc123" in cookie_header
        assert "user=john" in cookie_header

    def test_authenticates_from_url(self, requests_mock, mock_auth_response):
        requests_mock.get(API_RESOURCE_URI)

        with patch("STACpopulator.auth.handlers.make_request") as mock_make_request:
            mock_make_request.return_value = mock_auth_response({"token": "session-cookie"})

            handler = CookieAuthHandler(url=API_AUTH_URI, method="POST")
            requests.get(API_RESOURCE_URI, auth=handler)

            assert requests_mock.last_request.headers["Cookie"] == "session-cookie"


class TestAuthHandlerFromData:
    """Tests for AuthHandler.from_data factory method."""

    def test_returns_none_without_handler(self):
        assert AuthHandler.from_data(kwargs={"other_param": "value"}) is None
        assert AuthHandler.from_data(kwargs={"auth_handler": str}) is None

    def test_creates_basic_auth_handler(self):
        kwargs = {
            "auth_handler": BasicAuthHandler,
            "auth_identity": "user:pass",
        }
        handler = AuthHandler.from_data(kwargs)
        assert isinstance(handler, BasicAuthHandler)

    def test_creates_bearer_handler(self):
        kwargs = {
            "auth_handler": BearerAuthHandler,
            "auth_token": "access-token",
        }
        handler = AuthHandler.from_data(kwargs)
        assert isinstance(handler, BearerAuthHandler)

    def test_creates_cookie_handler(self):
        kwargs = {
            "auth_handler": CookieAuthHandler,
            "auth_token": "session=xyz789",
        }
        handler = AuthHandler.from_data(kwargs)
        assert isinstance(handler, CookieAuthHandler)

    def test_parses_params(self):
        kwargs = {
            "auth_handler": BearerAuthHandler,
            "auth_token": "access-token",
            "auth_url": API_AUTH_URI,
            "auth_headers": {"Custom-Header": "custom-value"},
        }
        handler = AuthHandler.from_data(kwargs)

        assert handler.token == "access-token"
        assert handler.url == API_AUTH_URI
        assert handler.headers["Custom-Header"] == "custom-value"
