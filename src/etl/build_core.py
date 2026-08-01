"""Normaliza staging.understat_* en el modelo core.* para una competición/temporada dada.

Orden de ejecución: teams -> players -> matches -> player_match_stats (cada paso depende
del anterior). Todo se hace con upserts (ON CONFLICT) para poder re-ejecutarse sin duplicar.

Limitación conocida: el equipo de un jugador en cada partido se infiere comparando el
equipo de su roster de temporada (staging.understat_players_season.team) contra el
home_team/away_team del partido. Si el jugador cambió de equipo a mitad de temporada,
los partidos con su equipo anterior no se podrán resolver y se descartan (quedan sin
insertar en core.player_match_stats) en vez de fallar todo el batch.
"""

import sys
import unicodedata

from sqlalchemy import text

from src.db.connection import get_engine


def _normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.replace("-", " ").replace(".", " ").lower()
    return " ".join(name.split())


def build_teams(competition: str, season: str) -> int:
    """staging.understat_players_season.team viene como 'Equipo A,Equipo B' cuando un
    jugador cambió de equipo a mitad de temporada; hay que desagregarlo en clubes reales."""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO core.teams (canonical_name, understat_team_name)
                SELECT DISTINCT club, club
                FROM staging.understat_players_season, unnest(string_to_array(team, ',')) AS club
                WHERE competition = :competition AND season = :season
                ON CONFLICT (canonical_name) DO UPDATE SET
                    understat_team_name = EXCLUDED.understat_team_name
                """
            ),
            {"competition": competition, "season": season},
        )
    return result.rowcount


def build_players(competition: str, season: str) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO core.players (canonical_name, understat_player_id, position)
                SELECT player_name, understat_player_id, position
                FROM staging.understat_players_season
                WHERE competition = :competition AND season = :season
                ON CONFLICT (understat_player_id) DO UPDATE SET
                    canonical_name = EXCLUDED.canonical_name,
                    position = EXCLUDED.position
                """
            ),
            {"competition": competition, "season": season},
        )
    return result.rowcount


def build_matches(competition: str, season: str) -> int:
    """Sólo entran partidos donde ambos equipos están en core.teams para esta competición/
    temporada (el join actúa de filtro: descarta partidos de otras ligas/temporadas que
    puedan aparecer en el historial completo de un jugador)."""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO core.matches (
                    understat_match_id, match_date, competition, season,
                    home_team_id, away_team_id, home_score, away_score
                )
                SELECT DISTINCT ON (pm.understat_match_id)
                    pm.understat_match_id, pm.match_date, :competition, pm.season,
                    ht.id, at.id, pm.home_goals, pm.away_goals
                FROM staging.understat_player_matches pm
                JOIN core.teams ht ON ht.canonical_name = pm.home_team
                JOIN core.teams at ON at.canonical_name = pm.away_team
                WHERE pm.season = :season
                ON CONFLICT (understat_match_id) DO UPDATE SET
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score
                """
            ),
            {"competition": competition, "season": season},
        )
    return result.rowcount


def build_player_match_stats(competition: str, season: str) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO core.player_match_stats (
                    match_id, player_id, team_id, position, minutes, goals, assists, shots,
                    key_passes, xg, xa, npg, npxg
                )
                SELECT
                    m.id, p.id,
                    CASE WHEN pm.home_team = ANY(string_to_array(ps.team, ',')) THEN m.home_team_id
                         WHEN pm.away_team = ANY(string_to_array(ps.team, ',')) THEN m.away_team_id
                    END,
                    pm.position, pm.minutes, pm.goals, pm.assists, pm.shots, pm.key_passes,
                    pm.xg, pm.xa, pm.npg, pm.npxg
                FROM staging.understat_player_matches pm
                JOIN core.matches m ON m.understat_match_id = pm.understat_match_id
                JOIN core.players p ON p.understat_player_id = pm.understat_player_id
                JOIN staging.understat_players_season ps
                    ON ps.understat_player_id = pm.understat_player_id
                    AND ps.competition = :competition AND ps.season = :season
                WHERE pm.season = :season
                    AND (pm.home_team = ANY(string_to_array(ps.team, ','))
                         OR pm.away_team = ANY(string_to_array(ps.team, ',')))
                ON CONFLICT (match_id, player_id) DO UPDATE SET
                    team_id = EXCLUDED.team_id,
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
            {"competition": competition, "season": season},
        )
    return result.rowcount


def build_market_values() -> tuple[int, int]:
    """Cruza core.players (poblado desde Understat) con la última foto de
    staging.transfermarkt_players por nombre normalizado (sin acentos/guiones). Primero
    intenta match exacto; si no es único, cae a contención de substring en cualquier
    sentido (ej. 'Kylian Mbappe' encaja con 'Kylian Mbappe Lottin'), pero sólo si hay
    EXACTAMENTE un candidato sin reclamar todavía — si hay 0 o varios candidatos posibles,
    se descarta en vez de arriesgar un cruce incorrecto (core.players.tm_player_id es
    UNIQUE, así que un mismo tm_player_id no puede asignarse a dos jugadores).

    Nombres que no casan quedan sin valor de mercado en esta iteración; matching más
    robusto (fecha de nacimiento, fuzzy matching) queda como mejora futura.

    Devuelve (jugadores_con_match, valores_insertados).
    """
    engine = get_engine()
    with engine.connect() as conn:
        players = conn.execute(text("SELECT id, canonical_name FROM core.players")).fetchall()
        tm_players = conn.execute(
            text(
                """
                SELECT DISTINCT ON (tm_player_id)
                    tm_player_id, name, nationality, market_value_eur, valued_at
                FROM staging.transfermarkt_players
                WHERE market_value_eur IS NOT NULL
                ORDER BY tm_player_id, valued_at DESC
                """
            )
        ).fetchall()

    normalized_players = [(p.id, _normalize_name(p.canonical_name)) for p in players]

    claimed_player_ids: set[int] = set()
    market_value_rows = []
    player_update_rows = []

    exact_matches = []
    substring_candidates = []
    for tm in tm_players:
        tm_norm = _normalize_name(tm.name)
        exact = [pid for pid, norm in normalized_players if norm == tm_norm]
        if len(exact) == 1:
            exact_matches.append((tm, exact[0]))
        else:
            substring_candidates.append((tm, tm_norm))

    for tm, player_id in exact_matches:
        if player_id in claimed_player_ids:
            continue
        claimed_player_ids.add(player_id)
        market_value_rows.append(
            {"player_id": player_id, "valued_at": tm.valued_at, "market_value_eur": tm.market_value_eur}
        )
        player_update_rows.append(
            {"player_id": player_id, "tm_player_id": tm.tm_player_id, "nationality": tm.nationality}
        )

    for tm, tm_norm in substring_candidates:
        candidates = [
            pid
            for pid, norm in normalized_players
            if pid not in claimed_player_ids and (norm in tm_norm or tm_norm in norm)
        ]
        if len(candidates) != 1:
            continue
        player_id = candidates[0]
        claimed_player_ids.add(player_id)
        market_value_rows.append(
            {"player_id": player_id, "valued_at": tm.valued_at, "market_value_eur": tm.market_value_eur}
        )
        player_update_rows.append(
            {"player_id": player_id, "tm_player_id": tm.tm_player_id, "nationality": tm.nationality}
        )

    matched = len(claimed_player_ids)

    engine = get_engine()
    with engine.begin() as conn:
        # se resetea antes de re-aplicar para que el resultado sea determinista en cada
        # ejecución y no arrastre asignaciones de una corrida anterior con otros datos
        conn.execute(text("UPDATE core.players SET tm_player_id = NULL"))
        if market_value_rows:
            conn.execute(
                text(
                    """
                    INSERT INTO core.market_values (player_id, valued_at, market_value_eur)
                    VALUES (:player_id, :valued_at, :market_value_eur)
                    ON CONFLICT (player_id, valued_at) DO UPDATE SET
                        market_value_eur = EXCLUDED.market_value_eur
                    """
                ),
                market_value_rows,
            )
        if player_update_rows:
            conn.execute(
                text(
                    """
                    UPDATE core.players
                    SET tm_player_id = :tm_player_id, nationality = COALESCE(nationality, :nationality)
                    WHERE id = :player_id
                    """
                ),
                player_update_rows,
            )

    return matched, len(market_value_rows)


def build_team_match_stats(season: str) -> int:
    """Cruza staging.understat_team_matches (por nombre de equipo + fecha) con
    core.matches, que ya tiene el match_id real. Requiere que build_matches ya se haya
    ejecutado para esta temporada."""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO core.team_match_stats (
                    match_id, team_id, is_home, goals_for, goals_against, xg, xga,
                    npxg, npxga, ppda, ppda_allowed, deep, deep_allowed
                )
                SELECT m.id, t.id, stm.is_home, stm.goals_for, stm.goals_against, stm.xg,
                       stm.xga, stm.npxg, stm.npxga, stm.ppda, stm.ppda_allowed, stm.deep,
                       stm.deep_allowed
                FROM staging.understat_team_matches stm
                JOIN core.teams t ON t.canonical_name = stm.team
                JOIN core.matches m ON m.match_date = stm.match_date
                    AND (m.home_team_id = t.id OR m.away_team_id = t.id)
                WHERE stm.season = :season
                ON CONFLICT (match_id, team_id) DO UPDATE SET
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
                    deep_allowed = EXCLUDED.deep_allowed
                """
            ),
            {"season": season},
        )
    return result.rowcount


def run(competition: str = "La_liga", season: str = "2025") -> None:
    print(f"teams: {build_teams(competition, season)}")
    print(f"players: {build_players(competition, season)}")
    print(f"matches: {build_matches(competition, season)}")
    print(f"player_match_stats: {build_player_match_stats(competition, season)}")
    matched, n_values = build_market_values()
    print(f"market_values: {matched} jugadores cruzados con Transfermarkt, {n_values} valores insertados")
    print(f"team_match_stats: {build_team_match_stats(season)}")


if __name__ == "__main__":
    competition_arg = sys.argv[1] if len(sys.argv) > 1 else "La_liga"
    season_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    run(competition_arg, season_arg)
