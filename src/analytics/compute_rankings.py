"""Recorre core.matches en orden cronológico aplicando el Elo de clubes y jugadores,
y vuelca el historial en marts.club_elo_history / marts.player_elo_history.

Se recalcula desde cero cada vez (trunca el historial de marts y reprocesa todos los
partidos de la competición/temporada): con el volumen de una sola temporada esto es
barato, y evita tener que gestionar reanudación incremental en esta primera iteración.
"""

import sys
from collections import defaultdict

from sqlalchemy import text

from src.analytics.ranking import club_elo_update, expected_score, player_elo_update
from src.db.connection import get_engine

INITIAL_RATING = 1500.0


def compute_and_store(competition: str, season: str) -> None:
    engine = get_engine()

    with engine.connect() as conn:
        matches = conn.execute(
            text(
                """
                SELECT id, match_date, home_team_id, away_team_id, home_score, away_score
                FROM core.matches
                WHERE competition = :competition AND season = :season
                ORDER BY match_date, id
                """
            ),
            {"competition": competition, "season": season},
        ).fetchall()

        player_stats_by_match = defaultdict(list)
        rows = conn.execute(
            text(
                """
                SELECT match_id, player_id, team_id, minutes, goals, assists, xg, xa, npg, npxg
                FROM core.player_match_stats
                """
            )
        ).fetchall()
        for row in rows:
            player_stats_by_match[row.match_id].append(row)

    club_ratings: dict[int, float] = defaultdict(lambda: INITIAL_RATING)
    player_ratings: dict[int, float] = defaultdict(lambda: INITIAL_RATING)

    club_history_rows = []
    player_history_rows = []

    for m in matches:
        home_before = club_ratings[m.home_team_id]
        away_before = club_ratings[m.away_team_id]
        home_after, away_after, home_delta, away_delta = club_elo_update(
            home_before, away_before, m.home_score, m.away_score
        )
        club_ratings[m.home_team_id] = home_after
        club_ratings[m.away_team_id] = away_after

        club_history_rows.append(
            {
                "team_id": m.home_team_id, "match_id": m.id, "match_date": m.match_date,
                "elo_before": home_before, "elo_after": home_after, "delta": home_delta,
            }
        )
        club_history_rows.append(
            {
                "team_id": m.away_team_id, "match_id": m.id, "match_date": m.match_date,
                "elo_before": away_before, "elo_after": away_after, "delta": away_delta,
            }
        )

        team_actual = {
            m.home_team_id: 1.0 if m.home_score > m.away_score else (0.5 if m.home_score == m.away_score else 0.0),
            m.away_team_id: 1.0 if m.away_score > m.home_score else (0.5 if m.away_score == m.home_score else 0.0),
        }
        expected_home = expected_score(home_before, away_before, rating_a_adjustment=100.0)
        team_expected = {m.home_team_id: expected_home, m.away_team_id: 1 - expected_home}

        for ps in player_stats_by_match.get(m.id, []):
            rating_before = player_ratings[ps.player_id]
            goal_contribution = (ps.goals or 0) + (ps.assists or 0)
            expected_goal_contribution = float(ps.npxg or 0) + float(ps.xa or 0)
            rating_after, delta = player_elo_update(
                rating_before,
                minutes=ps.minutes or 0,
                team_actual=team_actual[ps.team_id],
                team_expected=team_expected[ps.team_id],
                goal_contribution=goal_contribution,
                expected_goal_contribution=expected_goal_contribution,
            )
            player_ratings[ps.player_id] = rating_after
            player_history_rows.append(
                {
                    "player_id": ps.player_id, "match_id": m.id, "match_date": m.match_date,
                    "elo_before": rating_before, "elo_after": rating_after, "delta": delta,
                }
            )

    with engine.begin() as conn:
        match_ids = [m.id for m in matches]
        if match_ids:
            conn.execute(
                text("DELETE FROM marts.club_elo_history WHERE match_id = ANY(:match_ids)"),
                {"match_ids": match_ids},
            )
            conn.execute(
                text("DELETE FROM marts.player_elo_history WHERE match_id = ANY(:match_ids)"),
                {"match_ids": match_ids},
            )
        if club_history_rows:
            conn.execute(
                text(
                    """
                    INSERT INTO marts.club_elo_history (team_id, match_id, match_date, elo_before, elo_after, delta)
                    VALUES (:team_id, :match_id, :match_date, :elo_before, :elo_after, :delta)
                    """
                ),
                club_history_rows,
            )
        if player_history_rows:
            conn.execute(
                text(
                    """
                    INSERT INTO marts.player_elo_history (player_id, match_id, match_date, elo_before, elo_after, delta)
                    VALUES (:player_id, :match_id, :match_date, :elo_before, :elo_after, :delta)
                    """
                ),
                player_history_rows,
            )

    print(f"Partidos procesados: {len(matches)}")
    print(f"Filas club_elo_history: {len(club_history_rows)}")
    print(f"Filas player_elo_history: {len(player_history_rows)}")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    compute_and_store(competition_arg, season_arg)
