"""Tests for authentication handlers."""

from __future__ import annotations

import requests
import responses

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

    @responses.activate
    def test_adds_authorization_header(self):
        responses.get(API_RESOURCE_URI)

        handler = BasicAuthHandler(username="user", password="pass")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert len(responses.calls) == 1
        # Basic auth is base64("user:pass") = "dXNlcjpwYXNz"
        assert responses.calls[0].request.headers["Authorization"] == "Basic dXNlcjpwYXNz"


class TestDigestAuthHandler:
    """Tests for DigestAuthHandler as requests auth."""

    @responses.activate
    def test_handles_digest_challenge(self):
        # Digest auth requires a 401 challenge first
        responses.get(
            API_RESOURCE_URI,
            status=401,
            headers={"WWW-Authenticate": 'Digest realm="test", nonce="abc123", qop="auth"'},
        )
        responses.get(API_RESOURCE_URI, status=200, body="OK")

        handler = DigestAuthHandler(username="user", password="pass")
        response = requests.get(API_RESOURCE_URI, auth=handler)

        assert response.status_code == 200
        assert len(responses.calls) == 2
        # Second request should have Digest auth header
        assert "Digest" in responses.calls[1].request.headers["Authorization"]


class TestProxyAuthHandler:
    """Tests for ProxyAuthHandler as requests auth."""

    @responses.activate
    def test_adds_proxy_authorization_header(self):
        responses.get(API_RESOURCE_URI)

        handler = ProxyAuthHandler(username="proxy_user", password="proxy_pass")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert len(responses.calls) == 1
        assert "Basic" in responses.calls[0].request.headers["Proxy-Authorization"]


class TestBearerAuthHandler:
    """Tests for BearerAuthHandler as requests auth."""

    @responses.activate
    def test_with_direct_token(self):
        responses.get(API_RESOURCE_URI)

        handler = BearerAuthHandler(token="access-token")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["Authorization"] == "Bearer access-token"

    @responses.activate
    def test_authenticates_from_url(self):
        responses.post(API_AUTH_URI, json={"access_token": "access-token"})
        responses.get(API_RESOURCE_URI)

        handler = BearerAuthHandler(url=API_AUTH_URI, method="POST")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert responses.calls[1].request.headers["Authorization"] == "Bearer access-token"

    @responses.activate
    def test_no_header_on_auth_failure(self):
        responses.get(API_AUTH_URI, status=401)
        responses.get(API_RESOURCE_URI)

        handler = BearerAuthHandler(url=API_AUTH_URI, method="GET")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert "Authorization" not in responses.calls[1].request.headers


class TestCookieAuthHandler:
    """Tests for CookieAuthHandler as requests auth."""

    @responses.activate
    def test_with_string_token(self):
        responses.get(API_RESOURCE_URI)

        handler = CookieAuthHandler(token="session_id=abc123")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert responses.calls[0].request.headers["Cookie"] == "session_id=abc123"

    @responses.activate
    def test_with_dict_token(self):
        responses.get(API_RESOURCE_URI)

        handler = CookieAuthHandler(token={"session_id": "abc123", "user": "john"})
        requests.get(API_RESOURCE_URI, auth=handler)

        cookie_header = responses.calls[0].request.headers["Cookie"]
        assert "session_id=abc123" in cookie_header
        assert "user=john" in cookie_header

    @responses.activate
    def test_authenticates_from_url(self):
        responses.post(API_AUTH_URI, json={"token": "session-cookie"})
        responses.get(API_RESOURCE_URI)

        handler = CookieAuthHandler(url=API_AUTH_URI, method="POST")
        requests.get(API_RESOURCE_URI, auth=handler)

        assert responses.calls[1].request.headers["Cookie"] == "session-cookie"


class TestAuthHandlerFromData:
    """Tests for AuthHandler.from_data factory method."""

    def test_returns_none_without_handler(self):
        assert AuthHandler.from_data() is None
        assert AuthHandler.from_data(auth_handler=str) is None

    def test_creates_basic_auth_handler(self):
        handler = AuthHandler.from_data(
            auth_handler=BasicAuthHandler,
            auth_identity="user:pass",
        )
        assert isinstance(handler, BasicAuthHandler)

    def test_creates_bearer_handler(self):
        handler = AuthHandler.from_data(
            auth_handler=BearerAuthHandler,
            auth_token="access-token",
        )
        assert isinstance(handler, BearerAuthHandler)

    def test_creates_cookie_handler(self):
        handler = AuthHandler.from_data(
            auth_handler=CookieAuthHandler,
            auth_token="session=xyz789",
        )
        assert isinstance(handler, CookieAuthHandler)

    def test_parses_params(self):
        handler = AuthHandler.from_data(
            auth_handler=BearerAuthHandler,
            auth_token="access-token",
            auth_url=API_AUTH_URI,
            auth_headers={"Custom-Header": "custom-value"},
        )

        assert handler.token == "access-token"
        assert handler.url == API_AUTH_URI
        assert handler.headers["Custom-Header"] == "custom-value"
