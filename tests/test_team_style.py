import pandas as pd

from src.analytics.team_style import build_team_similarity_pairs


def _synthetic_teams() -> pd.DataFrame:
    rows = [
        # dos equipos "presionadores verticales": ppda bajo, deep alto
        {"team_id": 1, "xg": 1.8, "xga": 1.0, "ppda": 7.0, "ppda_allowed": 12.0, "deep": 12, "deep_allowed": 5},
        {"team_id": 2, "xg": 1.6, "xga": 1.1, "ppda": 7.5, "ppda_allowed": 11.5, "deep": 11, "deep_allowed": 6},
        # un equipo "de bloque bajo": ppda alto, deep bajo (estilo opuesto)
        {"team_id": 3, "xg": 0.9, "xga": 1.3, "ppda": 15.0, "ppda_allowed": 6.0, "deep": 4, "deep_allowed": 13},
    ]
    return pd.DataFrame(rows)


def test_most_similar_team_shares_the_style_profile():
    pairs = build_team_similarity_pairs(_synthetic_teams(), top_k=2)
    top_match_for_1 = pairs[(pairs["team_id"] == 1) & (pairs["rank"] == 1)].iloc[0]
    assert top_match_for_1["similar_team_id"] == 2


def test_never_recommends_self():
    pairs = build_team_similarity_pairs(_synthetic_teams(), top_k=2)
    assert (pairs["team_id"] == pairs["similar_team_id"]).sum() == 0
