"""Calcula la valoración Moneyball sobre datos reales y la guarda en
marts.player_valuation. Requiere que core.matches/player_match_stats/market_values ya
estén poblados (src.etl.build_core) para la competición/temporada dada.
"""

import sys

import pandas as pd
from sqlalchemy import text

from src.analytics.valuation import fit_valuation_model
from src.db.connection import get_engine

MIN_MINUTES = 450  # ~5 partidos completos: evita que muestras muy pequeñas metan ruido


def load_features(competition: str, season: str) -> pd.DataFrame:
    query = """
        WITH latest_value AS (
            SELECT DISTINCT ON (player_id) player_id, market_value_eur
            FROM core.market_values
            ORDER BY player_id, valued_at DESC
        ),
        latest_age AS (
            SELECT DISTINCT ON (tm_player_id) tm_player_id, age
            FROM staging.transfermarkt_players
            WHERE age IS NOT NULL
            ORDER BY tm_player_id, valued_at DESC
        ),
        season_stats AS (
            SELECT
                pms.player_id,
                SUM(pms.minutes) AS minutes,
                SUM(pms.goals) AS goals,
                SUM(pms.assists) AS assists,
                SUM(pms.xg) AS xg,
                SUM(pms.xa) AS xa,
                SUM(pms.npxg) AS npxg,
                SUM(pms.key_passes) AS key_passes
            FROM core.player_match_stats pms
            JOIN core.matches m ON m.id = pms.match_id
            WHERE m.competition = :competition AND m.season = :season
            GROUP BY pms.player_id
        )
        SELECT
            p.id AS player_id, p.canonical_name, p.position,
            ss.minutes, ss.goals, ss.assists, ss.xg, ss.xa, ss.npxg, ss.key_passes,
            la.age, lv.market_value_eur
        FROM season_stats ss
        JOIN core.players p ON p.id = ss.player_id
        JOIN latest_value lv ON lv.player_id = ss.player_id
        JOIN latest_age la ON la.tm_player_id = p.tm_player_id
        WHERE ss.minutes >= :min_minutes
    """
    return pd.read_sql(
        text(query), get_engine(), params={"competition": competition, "season": season, "min_minutes": MIN_MINUTES}
    )


def store_valuation(df: pd.DataFrame, competition: str, season: str) -> None:
    rows = [
        {
            "player_id": row.player_id,
            "competition": competition,
            "season": season,
            "age": int(row.age),
            "minutes": int(row.minutes),
            "market_value_eur": row.market_value_eur,
            "predicted_value_eur": row.predicted_value_eur,
            "value_gap_eur": row.value_gap_eur,
            "value_gap_pct": row.value_gap_pct,
        }
        for row in df.itertuples()
    ]
    if not rows:
        return

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO marts.player_valuation (
                    player_id, competition, season, age, minutes, market_value_eur,
                    predicted_value_eur, value_gap_eur, value_gap_pct
                ) VALUES (
                    :player_id, :competition, :season, :age, :minutes, :market_value_eur,
                    :predicted_value_eur, :value_gap_eur, :value_gap_pct
                )
                ON CONFLICT (player_id, season) DO UPDATE SET
                    competition = EXCLUDED.competition,
                    age = EXCLUDED.age,
                    minutes = EXCLUDED.minutes,
                    market_value_eur = EXCLUDED.market_value_eur,
                    predicted_value_eur = EXCLUDED.predicted_value_eur,
                    value_gap_eur = EXCLUDED.value_gap_eur,
                    value_gap_pct = EXCLUDED.value_gap_pct,
                    computed_at = now()
                """
            ),
            rows,
        )


def run(competition: str = "La_liga", season: str = "2025") -> None:
    df = load_features(competition, season)
    print(f"Jugadores con datos suficientes (>= {MIN_MINUTES} min y edad conocida): {len(df)}")
    df = fit_valuation_model(df)
    store_valuation(df, competition, season)
    print(f"marts.player_valuation actualizado: {len(df)} filas")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    run(competition_arg, season_arg)
