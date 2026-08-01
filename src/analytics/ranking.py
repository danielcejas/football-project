"""Ranking Elo de clubes y jugadores. Funciones puras, sin dependencia de la base de datos,
para poder testear la fórmula con datos sintéticos antes de aplicarla a datos reales."""

DEFAULT_K = 20.0
DEFAULT_HOME_ADVANTAGE = 100.0
DEFAULT_PLAYER_K = 16.0
DEFAULT_PLAYER_BONUS_WEIGHT = 8.0


def expected_score(rating_a: float, rating_b: float, rating_a_adjustment: float = 0.0) -> float:
    """Probabilidad esperada de que 'a' gane (un empate cuenta como 0.5), Elo clásico."""
    return 1 / (1 + 10 ** (-((rating_a + rating_a_adjustment) - rating_b) / 400))


def _goal_diff_multiplier(goal_diff: int) -> float:
    """Multiplicador por diferencia de goles, como en el World Football Elo Ratings:
    una goleada mueve más el rating que una victoria mínima."""
    goal_diff = abs(goal_diff)
    if goal_diff <= 1:
        return 1.0
    if goal_diff == 2:
        return 1.5
    return (11 + goal_diff) / 8


def club_elo_update(
    home_rating: float,
    away_rating: float,
    home_goals: int,
    away_goals: int,
    k: float = DEFAULT_K,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE,
) -> tuple[float, float, float, float]:
    """Devuelve (home_rating_after, away_rating_after, home_delta, away_delta)."""
    expected_home = expected_score(home_rating, away_rating, rating_a_adjustment=home_advantage)

    if home_goals > away_goals:
        actual_home = 1.0
    elif home_goals == away_goals:
        actual_home = 0.5
    else:
        actual_home = 0.0

    multiplier = _goal_diff_multiplier(home_goals - away_goals)
    home_delta = k * multiplier * (actual_home - expected_home)
    away_delta = -home_delta

    return home_rating + home_delta, away_rating + away_delta, home_delta, away_delta


def player_elo_update(
    rating: float,
    minutes: float,
    team_actual: float,
    team_expected: float,
    goal_contribution: float,
    expected_goal_contribution: float,
    k: float = DEFAULT_PLAYER_K,
    bonus_weight: float = DEFAULT_PLAYER_BONUS_WEIGHT,
) -> tuple[float, float]:
    """Devuelve (rating_after, delta).

    Dos componentes:
    - team_component: recompensa formar parte de un resultado mejor de lo esperado
      (mismos team_actual/team_expected que en club_elo_update), ponderado por minutos
      jugados para que un suplente que entra 10' no se mueva igual que un titular.
    - performance_component: recompensa rendir por encima de las métricas subyacentes
      (goles+asistencias por encima de npxG+xA), no se pondera por minutos porque ya es
      un total del partido.
    """
    minutes_weight = min(minutes / 90, 1.0) if minutes else 0.0
    team_component = k * minutes_weight * (team_actual - team_expected)
    performance_component = bonus_weight * (goal_contribution - expected_goal_contribution)
    delta = team_component + performance_component
    return rating + delta, delta
