from unittest.mock import MagicMock

from schema import _get_auth_headers


class TestGetAuthHeaders:
    def test_returns_none_when_no_request(self):
        info = MagicMock()
        info.context = {}
        assert _get_auth_headers(info) is None

    def test_returns_none_when_no_auth_header(self):
        request = MagicMock()
        request.headers = {}
        info = MagicMock()
        info.context = {"request": request}
        assert _get_auth_headers(info) is None

    def test_returns_auth_header(self):
        request = MagicMock()
        request.headers = {"authorization": "Bearer abc123"}
        info = MagicMock()
        info.context = {"request": request}
        result = _get_auth_headers(info)
        assert result == {"authorization": "Bearer abc123"}

    def test_returns_none_when_empty_auth(self):
        request = MagicMock()
        request.headers = MagicMock()
        request.headers.get.return_value = ""
        info = MagicMock()
        info.context = {"request": request}
        assert _get_auth_headers(info) is None
