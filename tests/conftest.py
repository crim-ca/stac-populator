import pytest
import requests_mock as rm


@pytest.fixture
def requests_mock():
    with rm.Mocker() as m:
        yield m


@pytest.fixture
def mock_auth_response():
    """Factory fixture to create mock responses for authentication requests."""

    def _make_response(json_data=None, status_code=200, content_type="application/json"):
        from unittest.mock import MagicMock

        response = MagicMock()
        response.ok = status_code < 400
        response.status_code = status_code
        response.headers = {"Content-Type": content_type}
        response.json.return_value = json_data or {}
        return response

    return _make_response
