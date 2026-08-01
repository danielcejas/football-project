"""Parsea los payloads JSON de raw.understat_responses y los vuelca, tipados, en staging.*"""

from sqlalchemy import text

from src.db.connection import get_engine


def _to_int(value):
    return int(value) if value not in (None, "") else None


def _to_float(value):
    return float(value) if value not in (None, "") else None


def _ppda_ratio(ppda: dict) -> float | None:
    """ppda viene como {"att": pases_rival, "def": acciones_defensivas}; el ratio en sí
    (pases permitidos por acción defensiva) es la métrica de intensidad de presión."""
    att, defn = ppda.get("att"), ppda.get("def")
    if not att or not defn:
        return None
    return att / defn


def load_league_team_matches(raw_response_id: int, payload: dict, season: str) -> int:
    rows = []
    for team_data in payload["teams"].values():
        team_name = team_data["title"]
        for h in team_data["history"]:
            rows.append(
                {
                    "raw_response_id": raw_response_id,
                    "team": team_name,
                    "season": season,
                    "match_date": h["date"][:10],
                    "is_home": h["h_a"] == "h",
                    "goals_for": _to_int(h.get("scored")),
                    "goals_against": _to_int(h.get("missed")),
                    "xg": _to_float(h.get("xG")),
                    "xga": _to_float(h.get("xGA")),
                    "npxg": _to_float(h.get("npxG")),
                    "npxga": _to_float(h.get("npxGA")),
                    "ppda": _ppda_ratio(h.get("ppda", {})),
                    "ppda_allowed": _ppda_ratio(h.get("ppda_allowed", {})),
                    "deep": _to_int(h.get("deep")),
                    "deep_allowed": _to_int(h.get("deep_allowed")),
                    "result": h.get("result"),
                    "points": _to_int(h.get("pts")),
                }
            )
    if not rows:
        return 0

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO staging.understat_team_matches (
                    raw_response_id, team, season, match_date, is_home, goals_for,
                    goals_against, xg, xga, npxg, npxga, ppda, ppda_allowed, deep,
                    deep_allowed, result, points
                ) VALUES (
                    :raw_response_id, :team, :season, :match_date, :is_home, :goals_for,
                    :goals_against, :xg, :xga, :npxg, :npxga, :ppda, :ppda_allowed, :deep,
                    :deep_allowed, :result, :points
                )
                ON CONFLICT (team, match_date) DO UPDATE SET
                    raw_response_id = EXCLUDED.raw_response_id,
                    season = EXCLUDED.season,
                    is_home = EXCLUDED.is_home,
                    goals_for = EXCLUDED.goals_for,
                    goals_against = EXCLUDED.goals_against,
                    xg = EXCLUDED.xg,
                    xga = EXCLUDED.xga,
                    npxg = EXCLUDED.npxg,
                    npxga = EXCLUDED.npxga,
                    ppda = EXCLUDED.ppda,
                    ppda_allowed = EXCLUDED.ppda_allowed,
                    deep = EXCLUDED.deep,
                    deep_allowed = EXCLUDED.deep_allowed,
                    result = EXCLUDED.result,
                    points = EXCLUDED.points
                """
            ),
            rows,
        )
    return len(rows)


def load_players_season(raw_response_id: int, payload: dict, competition: str, season: str) -> int:
    rows = [
        {
            "raw_response_id": raw_response_id,
            "understat_player_id": p["id"],
            "player_name": p["player_name"],
            "team": p["team_title"],
            "competition": competition,
            "season": season,
            "position": p.get("position"),
            "games": _to_int(p.get("games")),
            "minutes": _to_int(p.get("time")),
            "goals": _to_int(p.get("goals")),
            "assists": _to_int(p.get("assists")),
            "xg": _to_float(p.get("xG")),
            "xa": _to_float(p.get("xA")),
            "shots": _to_int(p.get("shots")),
            "key_passes": _to_int(p.get("key_passes")),
            "yellow_cards": _to_int(p.get("yellow_cards")),
            "red_cards": _to_int(p.get("red_cards")),
            "npg": _to_int(p.get("npg")),
            "npxg": _to_float(p.get("npxG")),
        }
        for p in payload["players"]
    ]
    if not rows:
        return 0

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO staging.understat_players_season (
                    raw_response_id, understat_player_id, player_name, team, competition, season,
                    position, games, minutes, goals, assists, xg, xa, shots, key_passes,
                    yellow_cards, red_cards, npg, npxg
                ) VALUES (
                    :raw_response_id, :understat_player_id, :player_name, :team, :competition, :season,
                    :position, :games, :minutes, :goals, :assists, :xg, :xa, :shots, :key_passes,
                    :yellow_cards, :red_cards, :npg, :npxg
                )
                ON CONFLICT (understat_player_id, season) DO UPDATE SET
                    raw_response_id = EXCLUDED.raw_response_id,
                    player_name = EXCLUDED.player_name,
                    team = EXCLUDED.team,
                    position = EXCLUDED.position,
                    games = EXCLUDED.games,
                    minutes = EXCLUDED.minutes,
                    goals = EXCLUDED.goals,
                    assists = EXCLUDED.assists,
                    xg = EXCLUDED.xg,
                    xa = EXCLUDED.xa,
                    shots = EXCLUDED.shots,
                    key_passes = EXCLUDED.key_passes,
                    yellow_cards = EXCLUDED.yellow_cards,
                    red_cards = EXCLUDED.red_cards,
                    npg = EXCLUDED.npg,
                    npxg = EXCLUDED.npxg
                """
            ),
            rows,
        )
    return len(rows)


def load_player_matches(raw_response_id: int, payload: dict, understat_player_id: str) -> int:
    rows = [
        {
            "raw_response_id": raw_response_id,
            "understat_player_id": understat_player_id,
            "understat_match_id": m["id"],
            "season": m.get("season"),
            "match_date": m["date"],
            "home_team": m["h_team"],
            "away_team": m["a_team"],
            "home_goals": _to_int(m["h_goals"]),
            "away_goals": _to_int(m["a_goals"]),
            "position": m.get("position"),
            "minutes": _to_int(m.get("time")),
            "goals": _to_int(m.get("goals")),
            "assists": _to_int(m.get("assists")),
            "shots": _to_int(m.get("shots")),
            "key_passes": _to_int(m.get("key_passes")),
            "xg": _to_float(m.get("xG")),
            "xa": _to_float(m.get("xA")),
            "npg": _to_int(m.get("npg")),
            "npxg": _to_float(m.get("npxG")),
        }
        for m in payload["matches"]
    ]
    if not rows:
        return 0

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO staging.understat_player_matches (
                    raw_response_id, understat_player_id, understat_match_id, season, match_date,
                    home_team, away_team, home_goals, away_goals, position, minutes, goals,
                    assists, shots, key_passes, xg, xa, npg, npxg
                ) VALUES (
                    :raw_response_id, :understat_player_id, :understat_match_id, :season, :match_date,
                    :home_team, :away_team, :home_goals, :away_goals, :position, :minutes, :goals,
                    :assists, :shots, :key_passes, :xg, :xa, :npg, :npxg
                )
                ON CONFLICT (understat_player_id, understat_match_id) DO UPDATE SET
                    raw_response_id = EXCLUDED.raw_response_id,
                    season = EXCLUDED.season,
                    match_date = EXCLUDED.match_date,
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals,
                    position = EXCLUDED.position,
                    minutes = EXCLUDED.minutes,
                    goals = EXCLUDED.goals,
                    assists = EXCLUDED.assists,
                    shots = EXCLUDED.shots,
                    key_passes = EXCLUDED.key_passes,
                    xg = EXCLUDED.xg,
                    xa = EXCLUDED.xa,
                    npg = EXCLUDED.npg,
                    npxg = EXCLUDED.npxg
                """
            ),
            rows,
        )
    return len(rows)
