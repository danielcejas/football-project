import time

import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class RateLimitedSession:
    """Sesión HTTP compartida que respeta un intervalo mínimo entre peticiones,
    para no golpear las webs fuente más rápido de lo razonable."""

    def __init__(self, min_interval_seconds: float = 2.0, headers: dict | None = None):
        self.session = requests.Session()
        self.session.headers.update(headers or {"User-Agent": DEFAULT_USER_AGENT})
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = self.min_interval_seconds - elapsed
        if wait > 0:
            time.sleep(wait)

    def get(self, url: str, **kwargs) -> requests.Response:
        self._throttle()
        response = self.session.get(url, timeout=30, **kwargs)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response

    def post(self, url: str, **kwargs) -> requests.Response:
        self._throttle()
        response = self.session.post(url, timeout=30, **kwargs)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response
