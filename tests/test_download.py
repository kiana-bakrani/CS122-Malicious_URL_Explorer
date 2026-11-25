
"""Test URLhaus download handling without making live API requests."""

from unittest.mock import Mock
import traceback

import pytest
import requests

from backend.urlhaus_api import download_recent_export


def test_download_uses_key_and_timeout(monkeypatch):
    monkeypatch.setenv("URLHAUS_AUTH_KEY", " test-key ")
    response = Mock(text="id,dateadded\n")
    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    assert download_recent_export() == "id,dateadded\n"
    get.assert_called_once_with(
        "https://urlhaus-api.abuse.ch/v2/files/exports/test-key/recent.csv", timeout=60
    )
    response.raise_for_status.assert_called_once()


def test_missing_key_does_not_make_request(monkeypatch):
    monkeypatch.setenv("URLHAUS_AUTH_KEY", " ")
    get = Mock()
    monkeypatch.setattr(requests, "get", get)
    with pytest.raises(ValueError, match="Missing URLHAUS_AUTH_KEY"):
        download_recent_export()
    get.assert_not_called()


@pytest.mark.parametrize("error", [requests.Timeout, requests.HTTPError])
def test_download_failure_does_not_expose_key_in_traceback(monkeypatch, error):
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-secret-key")
    monkeypatch.setattr(requests, "get", Mock(side_effect=error("URL contains test-secret-key")))
    with pytest.raises(RuntimeError, match="Failed to download URLhaus data") as caught:
        download_recent_export()
    formatted = "".join(traceback.format_exception(caught.value))
    assert "test-secret-key" not in formatted
