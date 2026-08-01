"""Calcula el top-K de jugadores más parecidos a cada jugador (src/analytics/similarity.py)
sobre datos reales y lo guarda en marts.player_similarity."""

import sys

import pandas as pd
from sqlalchemy import text

from src.analytics.similarity import build_similarity_pairs
from src.db.connection import get_engine

MIN_MINUTES = 450  # mismo umbral que la valoración: evita que muestras muy pequeñas metan ruido


def load_features(competition: str, season: str) -> pd.DataFrame:
    query = """
        SELECT
            p.id AS player_id, p.position,
            SUM(pms.minutes) AS minutes, SUM(pms.goals) AS goals, SUM(pms.assists) AS assists,
            SUM(pms.xg) AS xg, SUM(pms.xa) AS xa, SUM(pms.npxg) AS npxg,
            SUM(pms.key_passes) AS key_passes, SUM(pms.shots) AS shots
        FROM core.player_match_stats pms
        JOIN core.matches m ON m.id = pms.match_id
        JOIN core.players p ON p.id = pms.player_id
        WHERE m.competition = :competition AND m.season = :season
        GROUP BY p.id, p.position
        HAVING SUM(pms.minutes) >= :min_minutes
    """
    return pd.read_sql(
        text(query), get_engine(), params={"competition": competition, "season": season, "min_minutes": MIN_MINUTES}
    )


def store_similarity(pairs: pd.DataFrame, competition: str, season: str) -> None:
    """Reemplaza solo las filas de esta competicion/temporada, para no tocar otras
    temporadas ya calculadas (antes se hacia TRUNCATE de la tabla entera)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM marts.player_similarity WHERE competition = :competition AND season = :season"),
            {"competition": competition, "season": season},
        )
        if pairs.empty:
            return
        rows = pairs.assign(competition=competition, season=season).to_dict(orient="records")
        conn.execute(
            text(
                """
                INSERT INTO marts.player_similarity
                    (player_id, similar_player_id, rank, similarity, competition, season)
                VALUES (:player_id, :similar_player_id, :rank, :similarity, :competition, :season)
                """
            ),
            rows,
        )


def run(competition: str = "La_liga", season: str = "2025") -> None:
    df = load_features(competition, season)
    print(f"Jugadores con datos suficientes (>= {MIN_MINUTES} min): {len(df)}")
    pairs = build_similarity_pairs(df)
    store_similarity(pairs, competition, season)
    print(f"marts.player_similarity actualizado: {len(pairs)} filas")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    run(competition_arg, season_arg)
