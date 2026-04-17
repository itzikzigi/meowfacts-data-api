from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import Settings
from ..models.api import ApiFactResponse, ApiOptionsResponse
from ..utils.logger import Logger


class MeowFactsClient:
    """Extract stage: thin HTTP wrapper around the meowfacts API.

    Only responsibility: talk to the API and return parsed wire shapes. It
    knows nothing about `FactRecord`, `Dataset`, or how output is written —
    shaping is the transformer's job, persisting is the writer's.
    """

    def __init__(self, settings: Settings):
        self.logger = Logger(__name__)
        self._settings = settings
        self._session = self._build_session()

    def _build_session(self) -> Session:
        session = Session()
        retry = Retry(
            total=self._settings.max_retries,
            backoff_factor=self._settings.backoff_factor,
            status_forcelist=self._settings.retry_on_statuses,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def get_options(self) -> ApiOptionsResponse:
        url = f"{self._settings.base_url}/options"
        response = self._session.get(url, timeout=self._settings.timeout_seconds)
        response.raise_for_status()
        return ApiOptionsResponse.model_validate(response.json())

    def get_facts(self, language: str, count: int) -> ApiFactResponse:
        params = {"lang": language, "count": count}
        response = self._session.get(
            self._settings.base_url, params=params, timeout=self._settings.timeout_seconds
        )
        response.raise_for_status()
        return ApiFactResponse.model_validate(response.json())
