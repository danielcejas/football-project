"""Scrapea las plantillas de Transfermarkt para una liga/temporada y carga staging.*

Uso: python -m src.scraping.transfermarkt.run [league_slug] [competition_code] [season]
Por defecto: laliga, ES1, 2025 (temporada 2025/2026).
"""

import datetime
import sys

from src.etl.clean_transfermarkt import load_squad, parse_squad_page
from src.scraping.base import RateLimitedSession
from src.scraping.transfermarkt.client import fetch_league_clubs, fetch_squad


def run(league_slug: str = "laliga", competition_code: str = "ES1", season: str = "2025") -> None:
    session = RateLimitedSession(min_interval_seconds=2.0)
    valued_at = datetime.date.today().isoformat()

    _, clubs = fetch_league_clubs(session, league_slug, competition_code, season)
    print(f"Encontrados {len(clubs)} clubes")

    total_players = 0
    for i, (slug, tm_team_id) in enumerate(clubs, start=1):
        raw_id, html = fetch_squad(session, slug, tm_team_id, competition_code, season)
        team_name = slug.replace("-", " ").title()
        players = parse_squad_page(html, team_name)
        n = load_squad(raw_id, players, valued_at)
        total_players += n
        print(f"[{i}/{len(clubs)}] {slug}: {n} jugadores")

    print(f"Total jugadores cargados en staging.transfermarkt_players: {total_players}")


if __name__ == "__main__":
    league_slug_arg = sys.argv[1] if len(sys.argv) > 1 else "laliga"
    competition_code_arg = sys.argv[2] if len(sys.argv) > 2 else "ES1"
    season_arg = sys.argv[3] if len(sys.argv) > 3 else "2025"
    run(league_slug_arg, competition_code_arg, season_arg)
