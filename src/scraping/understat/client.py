"""Cliente para los endpoints JSON internos de Understat.

Understat no protege estos endpoints con Cloudflare (a diferencia de FBref), son los mismos
que usa su propio frontend vía AJAX. Se descubrieron inspeccionando las peticiones XHR que
dispara la página de liga (ver league.min.js / player.min.js).
"""

import json
from urllib.parse import quote

from sqlalchemy import text

from src.db.connection import get_engine
from src.scraping.base import RateLimitedSession

BASE_URL = "https://understat.com"


def _save_raw_response(endpoint: str, url: str, competition: str, season: str, payload: dict) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO raw.understat_responses (url, endpoint, competition, season, payload)
                VALUES (:url, :endpoint, :competition, :season, CAST(:payload AS JSONB))
                RETURNING id
                """
            ),
            {
                "url": url,
                "endpoint": endpoint,
                "competition": competition,
                "season": season,
                "payload": json.dumps(payload),
            },
        )
        return result.scalar_one()


def fetch_league_data(session: RateLimitedSession, competition: str, season: str) -> tuple[int, dict]:
    """competition con espacios, ej. 'La liga'. Devuelve (raw_response_id, payload)."""
    url = f"{BASE_URL}/getLeagueData/{quote(competition)}/{season}"
    response = session.get(
        url,
        headers={
            "Referer": f"{BASE_URL}/league/{competition.replace(' ', '_')}/{season}",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    payload = response.json()
    raw_id = _save_raw_response("league_data", url, competition, season, payload)
    return raw_id, payload


def fetch_players_stats(session: RateLimitedSession, competition: str, season: str) -> tuple[int, dict]:
    """competition con guion bajo, ej. 'La_liga'. Devuelve (raw_response_id, payload)."""
    url = f"{BASE_URL}/main/getPlayersStats/"
    response = session.post(
        url,
        data={"league": competition, "season": season},
        headers={
            "Referer": f"{BASE_URL}/league/{competition}/{season}",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    payload = response.json()
    raw_id = _save_raw_response("players_stats", url, competition, season, payload)
    return raw_id, payload


def has_player_data(player_id: str) -> bool:
    """True si ya existe una respuesta guardada de getPlayerData para este jugador.

    fetch_player_data trae la carrera COMPLETA del jugador sin importar la temporada
    pedida, así que si ya se descargó una vez (en cualquier temporada anterior) no hace
    falta volver a pedirla al scrapear otra temporada distinta."""
    url = f"{BASE_URL}/getPlayerData/{player_id}"
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM raw.understat_responses WHERE endpoint = 'player_data' AND url = :url LIMIT 1"),
            {"url": url},
        ).first()
    return row is not None


def fetch_player_data(session: RateLimitedSession, player_id: str, competition: str, season: str) -> tuple[int, dict]:
    url = f"{BASE_URL}/getPlayerData/{player_id}"
    response = session.get(
        url,
        headers={
            "Referer": f"{BASE_URL}/player/{player_id}",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    payload = response.json()
    raw_id = _save_raw_response("player_data", url, competition, season, payload)
    return raw_id, payload
