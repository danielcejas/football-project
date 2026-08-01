import pytest

from src.analytics.ranking import club_elo_update, expected_score, player_elo_update


def test_expected_score_equal_ratings_no_adjustment():
    assert expected_score(1500, 1500) == pytest.approx(0.5)


def test_club_elo_draw_between_equal_teams_is_neutral():
    # sin ventaja de local, un empate entre iguales no debería mover el rating
    home_after, away_after, home_delta, away_delta = club_elo_update(
        1500, 1500, home_goals=1, away_goals=1, home_advantage=0
    )
    assert home_after == pytest.approx(1500)
    assert away_after == pytest.approx(1500)
    assert home_delta == pytest.approx(0)
    assert away_delta == pytest.approx(0)


def test_club_elo_is_zero_sum():
    home_after, away_after, home_delta, away_delta = club_elo_update(
        1600, 1400, home_goals=2, away_goals=0, home_advantage=100
    )
    assert home_delta + away_delta == pytest.approx(0)
    assert home_after - 1600 == pytest.approx(home_delta)
    assert away_after - 1400 == pytest.approx(away_delta)


def test_club_elo_bigger_win_moves_rating_more():
    _, _, delta_1_0, _ = club_elo_update(1500, 1500, home_goals=1, away_goals=0, home_advantage=0)
    _, _, delta_3_0, _ = club_elo_update(1500, 1500, home_goals=3, away_goals=0, home_advantage=0)
    assert delta_3_0 > delta_1_0 > 0


def test_club_elo_win_between_equal_teams_no_home_advantage():
    # expected=0.5, actual=1.0, multiplicador goal_diff=1 -> delta = k * 1 * 0.5
    home_after, away_after, home_delta, away_delta = club_elo_update(
        1500, 1500, home_goals=1, away_goals=0, k=20, home_advantage=0
    )
    assert home_delta == pytest.approx(10.0)
    assert away_delta == pytest.approx(-10.0)
    assert home_after == pytest.approx(1510.0)
    assert away_after == pytest.approx(1490.0)


def test_player_elo_full_match_outperforming_xg():
    rating_after, delta = player_elo_update(
        rating=1500,
        minutes=90,
        team_actual=1.0,
        team_expected=0.5,
        goal_contribution=1,
        expected_goal_contribution=0.5,
        k=16,
        bonus_weight=8,
    )
    # team_component = 16 * 1.0 * (1.0 - 0.5) = 8; performance_component = 8 * 0.5 = 4
    assert delta == pytest.approx(12.0)
    assert rating_after == pytest.approx(1512.0)


def test_player_elo_scales_team_component_by_minutes_played():
    _, delta_full = player_elo_update(
        rating=1500, minutes=90, team_actual=1.0, team_expected=0.5,
        goal_contribution=1, expected_goal_contribution=0.5,
    )
    _, delta_half = player_elo_update(
        rating=1500, minutes=45, team_actual=1.0, team_expected=0.5,
        goal_contribution=1, expected_goal_contribution=0.5,
    )
    # el componente de rendimiento (4.0) no se pondera por minutos, sólo el de equipo
    assert delta_full - delta_half == pytest.approx(4.0)


def test_player_elo_zero_minutes_has_no_team_component():
    _, delta = player_elo_update(
        rating=1500, minutes=0, team_actual=1.0, team_expected=0.5,
        goal_contribution=0, expected_goal_contribution=0,
    )
    assert delta == pytest.approx(0.0)
