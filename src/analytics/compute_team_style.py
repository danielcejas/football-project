"""Calcula el top-K de equipos con estilo más parecido (src/analytics/team_style.py)
sobre datos reales y lo guarda en marts.team_similarity."""

import sys

import pandas as pd
from sqlalchemy import text

from src.analytics.team_style import build_team_similarity_pairs
from src.db.connection import get_engine


def load_features(competition: str, season: str) -> pd.DataFrame:
    query = """
        SELECT
            tms.team_id,
            AVG(tms.xg) AS xg, AVG(tms.xga) AS xga,
            AVG(tms.ppda) AS ppda, AVG(tms.ppda_allowed) AS ppda_allowed,
            AVG(tms.deep) AS deep, AVG(tms.deep_allowed) AS deep_allowed
        FROM core.team_match_stats tms
        JOIN core.matches m ON m.id = tms.match_id
        WHERE m.competition = :competition AND m.season = :season
        GROUP BY tms.team_id
    """
    return pd.read_sql(text(query), get_engine(), params={"competition": competition, "season": season})


def store_similarity(pairs: pd.DataFrame, competition: str, season: str) -> None:
    """Reemplaza solo las filas de esta competicion/temporada, para no tocar otras
    temporadas ya calculadas (antes se hacia TRUNCATE de la tabla entera)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM marts.team_similarity WHERE competition = :competition AND season = :season"),
            {"competition": competition, "season": season},
        )
        if pairs.empty:
            return
        rows = pairs.assign(competition=competition, season=season).to_dict(orient="records")
        conn.execute(
            text(
                """
                INSERT INTO marts.team_similarity
                    (team_id, similar_team_id, rank, similarity, competition, season)
                VALUES (:team_id, :similar_team_id, :rank, :similarity, :competition, :season)
                """
            ),
            rows,
        )


def run(competition: str = "La_liga", season: str = "2025") -> None:
    df = load_features(competition, season)
    print(f"Equipos con datos de estilo: {len(df)}")
    pairs = build_team_similarity_pairs(df)
    store_similarity(pairs, competition, season)
    print(f"marts.team_similarity actualizado: {len(pairs)} filas")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    run(competition_arg, season_arg)
