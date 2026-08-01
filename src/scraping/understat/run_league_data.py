"""Scrapea getLeagueData (historial por equipo y partido, con xG/ppda/deep) para una
competición/temporada y carga staging.understat_team_matches.

Uso: python -m src.scraping.understat.run_league_data [competition_espacio] [season]
Por defecto: 'La liga', 2025. Nota: este endpoint usa el nombre de la liga CON espacio
('La liga'), a diferencia de main/getPlayersStats que usa guion bajo ('La_liga').
"""

import sys

from src.etl.clean_understat import load_league_team_matches
from src.scraping.base import RateLimitedSession
from src.scraping.understat.client import fetch_league_data


def run(competition: str = "La liga", season: str = "2025") -> None:
    session = RateLimitedSession(min_interval_seconds=2.0)
    raw_id, payload = fetch_league_data(session, competition, season)
    n = load_league_team_matches(raw_id, payload, season)
    print(f"staging.understat_team_matches: {n} filas insertadas/actualizadas")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    run(competition_arg, season_arg)
