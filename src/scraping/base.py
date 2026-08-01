import time

import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Errores del lado del servidor (o de red) que valen la pena reintentar: son fallos
# transitorios de la web fuente, no un bloqueo ni un error nuestro. 4xx no se reintenta
# porque no se va a arreglar solo (URL mal formada, recurso que no existe, etc.).
RETRYABLE_STATUS_CODES = {502, 503, 504}
RETRY_BACKOFF_SECONDS = (2.0, 4.0, 8.0)


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

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        last_exc: Exception | None = None
        for attempt, backoff in enumerate((0.0, *RETRY_BACKOFF_SECONDS)):
            if backoff:
                time.sleep(backoff)
            self._throttle()
            try:
                response = getattr(self.session, method)(url, timeout=30, **kwargs)
                self._last_request_at = time.monotonic()
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < len(RETRY_BACKOFF_SECONDS):
                    continue
                response.raise_for_status()
                return response
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                self._last_request_at = time.monotonic()
                last_exc = exc
                if attempt >= len(RETRY_BACKOFF_SECONDS):
                    raise
        raise last_exc  # pragma: no cover - solo si se agotan los reintentos por timeout

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._request_with_retry("get", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._request_with_retry("post", url, **kwargs)
