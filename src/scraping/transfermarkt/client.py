"""Cliente de Transfermarkt. A diferencia de FBref, responde 200 a peticiones normales de
requests (sin Cloudflare ni bloqueo por JS), así que no hace falta navegador headless."""

import re

from sqlalchemy import text

from src.db.connection import get_engine
from src.scraping.base import RateLimitedSession

BASE_URL = "https://www.transfermarkt.com"

CLUB_LINK_RE = re.compile(r'href="/([a-z0-9-]+)/startseite/verein/(\d+)')


def _save_raw_page(entity_type: str, url: str, competition: str, season: str, html: str) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO raw.transfermarkt_pages (url, entity_type, competition, season, html)
                VALUES (:url, :entity_type, :competition, :season, :html)
                RETURNING id
                """
            ),
            {"url": url, "entity_type": entity_type, "competition": competition, "season": season, "html": html},
        )
        return result.scalar_one()


def fetch_league_clubs(
    session: RateLimitedSession, league_slug: str, competition_code: str, season: str
) -> tuple[int, list[tuple[str, str]]]:
    """Devuelve (raw_page_id, [(club_slug, tm_team_id), ...]) para la temporada dada."""
    url = f"{BASE_URL}/{league_slug}/startseite/wettbewerb/{competition_code}/saison_id/{season}"
    response = session.get(url)
    raw_id = _save_raw_page("league_clubs", url, competition_code, season, response.text)
    clubs = sorted(set(CLUB_LINK_RE.findall(response.text)), key=lambda c: c[0])
    return raw_id, clubs


def fetch_squad(
    session: RateLimitedSession, club_slug: str, tm_team_id: str, competition_code: str, season: str
) -> tuple[int, str]:
    """Devuelve (raw_page_id, html) de la página de plantilla del club para la temporada dada."""
    url = f"{BASE_URL}/{club_slug}/kader/verein/{tm_team_id}/saison_id/{season}"
    response = session.get(url)
    raw_id = _save_raw_page("squad", url, competition_code, season, response.text)
    return raw_id, response.text
