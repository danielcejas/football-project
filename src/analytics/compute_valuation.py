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
    """El valor de mercado y la edad se toman "a fecha de" ESTA temporada, no el snapshot
    más reciente de todos -- si no, una temporada histórica se valoraría con el valor de
    mercado o la edad ACTUAL del jugador en vez de la de esa época (bug real:
    Bellingham/Lewandowski salían con el mismo valor de mercado en sus 3 temporadas).

    El corte se calcula a partir de datos reales (fecha del primer partido de la
    temporada SIGUIENTE), no de la fecha de "hoy" -- una versión anterior de este fix
    usaba _valued_at_for_season(season), pero esa función depende de "hoy" en el momento
    de EJECUTAR el script, no de cuando se scrapeó cada temporada, así que dejaba de
    funcionar en cuanto pasaba la fecha de cierre nominal de la temporada vigente. Si no
    existe una temporada siguiente ya cargada (es la vigente), no se aplica corte y se
    toma el snapshot más reciente disponible, como antes.
    """
    next_season = str(int(season) + 1)
    query = """
        WITH next_season_start AS (
            SELECT MIN(match_date) AS start_date
            FROM core.matches
            WHERE competition = :competition AND season = :next_season
        ),
        latest_value AS (
            SELECT DISTINCT ON (mv.player_id) mv.player_id, mv.market_value_eur
            FROM core.market_values mv, next_season_start nss
            WHERE nss.start_date IS NULL OR mv.valued_at < nss.start_date
            ORDER BY mv.player_id, mv.valued_at DESC
        ),
        latest_age AS (
            SELECT DISTINCT ON (tp.tm_player_id) tp.tm_player_id, tp.age
            FROM staging.transfermarkt_players tp, next_season_start nss
            WHERE tp.age IS NOT NULL AND (nss.start_date IS NULL OR tp.valued_at < nss.start_date)
            ORDER BY tp.tm_player_id, tp.valued_at DESC
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
        text(query),
        get_engine(),
        params={
            "competition": competition,
            "season": season,
            "next_season": next_season,
            "min_minutes": MIN_MINUTES,
        },
    )


def store_valuation(df: pd.DataFrame, competition: str, season: str) -> None:
    """El ON CONFLICT (player_id, season) sobreescribe jugadores que siguen calificando,
    pero no limpia una fila de una corrida anterior de un jugador que YA NO califica en
    esta ejecucion (ej. cayo por debajo de MIN_MINUTES tras recalcular) -- por eso se
    borra primero todo lo de esta competicion/temporada antes de insertar el resultado
    completo, igual que ya hacen compute_similarity/compute_team_style."""
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

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM marts.player_valuation WHERE competition = :competition AND season = :season"),
            {"competition": competition, "season": season},
        )
        if not rows:
            return
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
