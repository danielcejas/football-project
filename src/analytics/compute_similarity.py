"""Calcula el top-K de jugadores más parecidos a cada jugador (src/analytics/similarity.py)
sobre datos reales y lo guarda en marts.player_similarity."""

import sys

import pandas as pd
from sqlalchemy import text

from src.analytics.similarity import build_similarity_pairs
from src.db.connection import get_engine

MIN_MINUTES = 450  # mismo umbral que la valoración: evita que muestras muy pequeñas metan ruido


def load_features(competition: str) -> pd.DataFrame:
    """Una fila por jugador-temporada (todas las temporadas disponibles de la competición
    en una sola pasada), para poder comparar entre temporadas y no solo dentro de una."""
    query = """
        SELECT
            p.id AS player_id, m.season, p.position,
            SUM(pms.minutes) AS minutes, SUM(pms.goals) AS goals, SUM(pms.assists) AS assists,
            SUM(pms.xg) AS xg, SUM(pms.xa) AS xa, SUM(pms.npxg) AS npxg,
            SUM(pms.key_passes) AS key_passes, SUM(pms.shots) AS shots
        FROM core.player_match_stats pms
        JOIN core.matches m ON m.id = pms.match_id
        JOIN core.players p ON p.id = pms.player_id
        WHERE m.competition = :competition
        GROUP BY p.id, m.season, p.position
        HAVING SUM(pms.minutes) >= :min_minutes
    """
    return pd.read_sql(text(query), get_engine(), params={"competition": competition, "min_minutes": MIN_MINUTES})


def store_similarity(pairs: pd.DataFrame, competition: str) -> None:
    """Reemplaza todas las filas de esta competición (todas las temporadas se recalculan
    juntas cada vez, no hay dependencia de orden entre ellas a diferencia del Elo)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM marts.player_similarity WHERE competition = :competition"),
            {"competition": competition},
        )
        if pairs.empty:
            return
        rows = pairs.assign(competition=competition).to_dict(orient="records")
        conn.execute(
            text(
                """
                INSERT INTO marts.player_similarity
                    (player_id, season, similar_player_id, similar_season, rank, similarity, competition)
                VALUES (:player_id, :season, :similar_player_id, :similar_season, :rank, :similarity, :competition)
                """
            ),
            rows,
        )


def run(competition: str = "La_liga") -> None:
    df = load_features(competition)
    print(f"Jugador-temporadas con datos suficientes (>= {MIN_MINUTES} min): {len(df)}")
    pairs = build_similarity_pairs(df)
    store_similarity(pairs, competition)
    print(f"marts.player_similarity actualizado: {len(pairs)} filas")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    run(competition_arg)
