"""Calcula el top-K de equipos con estilo más parecido (src/analytics/team_style.py)
sobre datos reales y lo guarda en marts.team_similarity."""

import sys

import pandas as pd
from sqlalchemy import text

from src.analytics.team_style import build_team_similarity_pairs
from src.db.connection import get_engine


def load_features(competition: str) -> pd.DataFrame:
    """Una fila por equipo-temporada (todas las temporadas disponibles de la competición
    en una sola pasada), para poder comparar entre temporadas y no solo dentro de una."""
    query = """
        SELECT
            tms.team_id, m.season,
            AVG(tms.xg) AS xg, AVG(tms.xga) AS xga,
            AVG(tms.ppda) AS ppda, AVG(tms.ppda_allowed) AS ppda_allowed,
            AVG(tms.deep) AS deep, AVG(tms.deep_allowed) AS deep_allowed
        FROM core.team_match_stats tms
        JOIN core.matches m ON m.id = tms.match_id
        WHERE m.competition = :competition
        GROUP BY tms.team_id, m.season
    """
    return pd.read_sql(text(query), get_engine(), params={"competition": competition})


def store_similarity(pairs: pd.DataFrame, competition: str) -> None:
    """Reemplaza todas las filas de esta competición (todas las temporadas se recalculan
    juntas cada vez, no hay dependencia de orden entre ellas a diferencia del Elo)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM marts.team_similarity WHERE competition = :competition"),
            {"competition": competition},
        )
        if pairs.empty:
            return
        rows = pairs.assign(competition=competition).to_dict(orient="records")
        conn.execute(
            text(
                """
                INSERT INTO marts.team_similarity
                    (team_id, season, similar_team_id, similar_season, rank, similarity, competition)
                VALUES (:team_id, :season, :similar_team_id, :similar_season, :rank, :similarity, :competition)
                """
            ),
            rows,
        )


def run(competition: str = "La_liga") -> None:
    df = load_features(competition)
    print(f"Equipo-temporadas con datos de estilo: {len(df)}")
    pairs = build_team_similarity_pairs(df)
    store_similarity(pairs, competition)
    print(f"marts.team_similarity actualizado: {len(pairs)} filas")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    run(competition_arg)
