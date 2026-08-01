import pandas as pd

from src.analytics.team_style import build_team_similarity_pairs


def _synthetic_teams() -> pd.DataFrame:
    rows = [
        # dos equipos "presionadores verticales": ppda bajo, deep alto
        {"team_id": 1, "season": "2025", "xg": 1.8, "xga": 1.0, "ppda": 7.0, "ppda_allowed": 12.0, "deep": 12, "deep_allowed": 5},
        {"team_id": 2, "season": "2025", "xg": 1.6, "xga": 1.1, "ppda": 7.5, "ppda_allowed": 11.5, "deep": 11, "deep_allowed": 6},
        # un equipo "de bloque bajo": ppda alto, deep bajo (estilo opuesto)
        {"team_id": 3, "season": "2025", "xg": 0.9, "xga": 1.3, "ppda": 15.0, "ppda_allowed": 6.0, "deep": 4, "deep_allowed": 13},
    ]
    return pd.DataFrame(rows)


def test_most_similar_team_shares_the_style_profile():
    pairs = build_team_similarity_pairs(_synthetic_teams(), top_k=2)
    top_match_for_1 = pairs[(pairs["team_id"] == 1) & (pairs["rank"] == 1)].iloc[0]
    assert top_match_for_1["similar_team_id"] == 2


def test_never_recommends_the_exact_same_row():
    pairs = build_team_similarity_pairs(_synthetic_teams(), top_k=2)
    same_row = (pairs["team_id"] == pairs["similar_team_id"]) & (pairs["season"] == pairs["similar_season"])
    assert same_row.sum() == 0


def _synthetic_team_across_seasons() -> pd.DataFrame:
    """Un mismo equipo en dos temporadas con estilo casi identico, mas un tercero con
    estilo claramente distinto -- para comprobar sin ambiguedad que SI puede recomendarse
    otra temporada de si mismo cuando es, de hecho, lo mas parecido que hay."""
    rows = [
        {"team_id": 1, "season": "2025", "xg": 1.8, "xga": 1.0, "ppda": 7.0, "ppda_allowed": 12.0, "deep": 12, "deep_allowed": 5},
        {"team_id": 1, "season": "2024", "xg": 1.75, "xga": 1.05, "ppda": 7.2, "ppda_allowed": 11.8, "deep": 11, "deep_allowed": 6},
        {"team_id": 2, "season": "2025", "xg": 0.7, "xga": 1.6, "ppda": 16.0, "ppda_allowed": 5.0, "deep": 3, "deep_allowed": 14},
    ]
    return pd.DataFrame(rows)


def test_cross_season_match_is_allowed():
    pairs = build_team_similarity_pairs(_synthetic_team_across_seasons(), top_k=1)
    top_match_for_1_2025 = pairs[(pairs["team_id"] == 1) & (pairs["season"] == "2025")].iloc[0]
    assert top_match_for_1_2025["similar_team_id"] == 1
    assert top_match_for_1_2025["similar_season"] == "2024"
