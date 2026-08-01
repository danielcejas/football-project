import pandas as pd

from src.analytics.similarity import build_similarity_pairs


def _synthetic_players() -> pd.DataFrame:
    rows = [
        # dos "killers" de área con perfil casi idéntico por 90'
        {"player_id": 1, "season": "2025", "minutes": 2700, "goals": 20, "assists": 2, "xg": 18, "xa": 2, "npxg": 16, "key_passes": 10, "shots": 80, "position": "F"},
        {"player_id": 2, "season": "2025", "minutes": 1800, "goals": 13, "assists": 1, "xg": 12, "xa": 1, "npxg": 11, "key_passes": 7, "shots": 53, "position": "F"},
        # un creador puro, perfil opuesto
        {"player_id": 3, "season": "2025", "minutes": 2700, "goals": 2, "assists": 15, "xg": 2, "xa": 14, "npxg": 2, "key_passes": 70, "shots": 15, "position": "M"},
        # un defensa: aunque tenga stats parecidas a alguien, se descarta por posición
        {"player_id": 4, "season": "2025", "minutes": 2700, "goals": 20, "assists": 2, "xg": 18, "xa": 2, "npxg": 16, "key_passes": 10, "shots": 80, "position": "D"},
    ]
    return pd.DataFrame(rows)


def test_similar_players_share_the_same_production_profile():
    pairs = build_similarity_pairs(_synthetic_players(), top_k=2)

    top_match_for_1 = pairs[(pairs["player_id"] == 1) & (pairs["rank"] == 1)].iloc[0]
    assert top_match_for_1["similar_player_id"] == 2

    top_match_for_3 = pairs[(pairs["player_id"] == 3) & (pairs["rank"] == 1)].iloc[0]
    assert top_match_for_3["similar_player_id"] in (1, 2)  # únicos candidatos disponibles (F/M)


def test_defender_is_excluded_entirely():
    pairs = build_similarity_pairs(_synthetic_players(), top_k=2)
    assert 4 not in pairs["player_id"].values
    assert 4 not in pairs["similar_player_id"].values


def test_never_recommends_the_exact_same_row():
    pairs = build_similarity_pairs(_synthetic_players(), top_k=2)
    same_row = (pairs["player_id"] == pairs["similar_player_id"]) & (pairs["season"] == pairs["similar_season"])
    assert same_row.sum() == 0


def _synthetic_player_across_seasons() -> pd.DataFrame:
    """Un mismo jugador en dos temporadas con perfil casi idéntico, más un tercero con
    perfil claramente distinto -- para comprobar sin ambigüedad que SÍ puede recomendarse
    otra temporada de sí mismo cuando es, de hecho, lo más parecido que hay."""
    rows = [
        {"player_id": 1, "season": "2025", "minutes": 2700, "goals": 20, "assists": 2, "xg": 18, "xa": 2, "npxg": 16, "key_passes": 10, "shots": 80, "position": "F"},
        {"player_id": 1, "season": "2024", "minutes": 2700, "goals": 19, "assists": 2, "xg": 17, "xa": 2, "npxg": 15, "key_passes": 10, "shots": 78, "position": "F"},
        {"player_id": 2, "season": "2025", "minutes": 2700, "goals": 1, "assists": 18, "xg": 1, "xa": 16, "npxg": 1, "key_passes": 75, "shots": 5, "position": "M"},
    ]
    return pd.DataFrame(rows)


def test_cross_season_match_is_allowed():
    pairs = build_similarity_pairs(_synthetic_player_across_seasons(), top_k=1)
    top_match_for_1_2025 = pairs[(pairs["player_id"] == 1) & (pairs["season"] == "2025")].iloc[0]
    assert top_match_for_1_2025["similar_player_id"] == 1
    assert top_match_for_1_2025["similar_season"] == "2024"
