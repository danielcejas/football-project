"""Re-parsea raw.understat_responses -> staging.* sin volver a golpear la web.
Útil cuando cambia la lógica de limpieza (ej. se añade una columna nueva)."""

from sqlalchemy import text

from src.db.connection import get_engine
from src.etl.clean_understat import load_player_matches, load_players_season


def reprocess(competition: str, season: str) -> None:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, endpoint, payload
                FROM raw.understat_responses
                WHERE competition = :competition AND season = :season
                ORDER BY id
                """
            ),
            {"competition": competition, "season": season},
        ).fetchall()

    total_players = 0
    total_matches = 0
    for raw_id, endpoint, payload in rows:
        if endpoint == "players_stats":
            total_players += load_players_season(raw_id, payload, competition, season)
        elif endpoint == "player_data":
            player_id = payload["player"]["id"]
            total_matches += load_player_matches(raw_id, payload, player_id)

    print(f"Reprocesados: {total_players} filas de roster, {total_matches} filas de partidos")


if __name__ == "__main__":
    import sys

    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    reprocess(competition_arg, season_arg)
