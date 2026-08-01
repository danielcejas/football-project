"""Scrapea las plantillas de Transfermarkt para una liga/temporada y carga staging.*

Uso: python -m src.scraping.transfermarkt.run [league_slug] [competition_code] [season]
Por defecto: laliga, ES1, 2025 (temporada 2025/2026).
"""

import datetime
import sys

from src.etl.clean_transfermarkt import load_squad, parse_squad_page
from src.scraping.base import RateLimitedSession
from src.scraping.transfermarkt.client import fetch_league_clubs, fetch_squad


def _valued_at_for_season(season: str) -> str:
    """Transfermarkt SI muestra un valor de mercado distinto en la pagina de plantilla de
    una temporada pasada (verificado manualmente: un jugador con 28M en la pagina de
    2023/24 vs 15M en la actual), pero no expone la fecha exacta de esa valoracion. Se usa
    el 30 de junio del año siguiente (fin de temporada europea tipico) como fecha
    representativa de la temporada -- salvo que caiga en el futuro (temporada en curso),
    en cuyo caso se usa la fecha de scraping real, igual que antes. Esto evita que una
    temporada historica quede fechada con el dia de hoy y se confunda con la vigente."""
    season_end = datetime.date(int(season) + 1, 6, 30)
    today = datetime.date.today()
    return min(season_end, today).isoformat()


def run(league_slug: str = "laliga", competition_code: str = "ES1", season: str = "2025") -> None:
    session = RateLimitedSession(min_interval_seconds=2.0)
    valued_at = _valued_at_for_season(season)

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
