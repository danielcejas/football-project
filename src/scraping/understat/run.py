"""Scrapea Understat para una competición/temporada y carga staging.*.

Uso: python -m src.scraping.understat.run [competition] [season]
Por defecto: La_liga, 2025 (temporada 2025/2026).
"""

import sys

from src.etl.clean_understat import load_player_matches, load_players_season
from src.scraping.base import RateLimitedSession
from src.scraping.understat.client import fetch_player_data, fetch_players_stats


def run(competition: str = "La_liga", season: str = "2025", limit: int | None = None) -> None:
    session = RateLimitedSession(min_interval_seconds=2.0)

    raw_id, players_payload = fetch_players_stats(session, competition, season)
    n_players = load_players_season(raw_id, players_payload, competition, season)
    print(f"players_stats: {n_players} jugadores cargados en staging.understat_players_season")

    players = players_payload["players"]
    if limit is not None:
        players = players[:limit]
    total_matches = 0
    for i, player in enumerate(players, start=1):
        player_id = player["id"]
        raw_id, player_payload = fetch_player_data(session, player_id, competition, season)
        n_matches = load_player_matches(raw_id, player_payload, player_id)
        total_matches += n_matches
        print(f"[{i}/{len(players)}] player {player_id} ({player['player_name']}): {n_matches} partidos")

    print(f"Total filas en staging.understat_player_matches insertadas/actualizadas: {total_matches}")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    limit_arg = int(sys.argv[3]) if len(sys.argv) > 3 else None
    run(competition_arg, season_arg, limit_arg)
