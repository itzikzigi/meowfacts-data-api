from unittest.mock import MagicMock

import pytest

from meowfacts.config import Settings
from meowfacts.extract.client import MeowFactsClient
from meowfacts.models.api import ApiFactResponse, ApiOptionsResponse


def _client_with_fake_session(response_json: dict):
    client = MeowFactsClient(Settings())
    fake_response = MagicMock()
    fake_response.json.return_value = response_json
    fake_response.raise_for_status.return_value = None
    client._session = MagicMock()
    client._session.get.return_value = fake_response
    return client


def test_get_facts_parses_response_and_sends_expected_params():
    client = _client_with_fake_session({"data": ["one", "two", "three"]})
    result = client.get_facts("eng", 42)
    assert isinstance(result, ApiFactResponse)
    assert result.data == ["one", "two", "three"]
    _, kwargs = client._session.get.call_args
    assert kwargs["params"] == {"lang": "eng", "count": 42}
    assert kwargs["timeout"] == client._settings.timeout_seconds


def test_get_options_parses_and_exposes_language_codes():
    client = _client_with_fake_session({
        "lang": [
            {
                "locale_code": "en_US", "iso_code": "en", "full_code": "eng",
                "local_name": "English", "english_name": "English",
                "full_name": "English (US)", "fact_count": 91,
            },
            {
                "locale_code": "es_ES", "iso_code": "es", "full_code": "esp",
                "local_name": "Español", "english_name": "Spanish",
                "full_name": "Spanish (Spain)", "fact_count": 45,
            },
        ]
    })
    result = client.get_options()
    assert isinstance(result, ApiOptionsResponse)
    assert result.get_languages() == ["eng", "esp"]


def test_get_facts_raises_on_http_error():
    client = _client_with_fake_session({})
    client._session.get.return_value.raise_for_status.side_effect = RuntimeError("500")
    with pytest.raises(RuntimeError):
        client.get_facts("eng", 10)
