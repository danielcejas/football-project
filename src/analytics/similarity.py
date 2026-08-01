"""Comparador de jugadores parecidos: perfil de producción ofensiva por 90' (estandarizado)
+ similitud coseno. Dos jugadores "se parecen" si generan el mismo tipo de output por
minuto jugado (mismo perfil de goles/asistencias/xG/xA/tiros/pases clave), sin importar el
volumen total (por eso todo se normaliza por 90' antes de comparar).

Limitado a delanteros y centrocampistas (ver valuation.VALUATION_POSITIONS): sin stats
defensivas de Understat, comparar defensas/porteros por estas columnas no sería un
parecido real, sólo ruido cercano a cero para todos.
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from src.analytics.valuation import VALUATION_POSITIONS, position_bucket

SIMILARITY_STAT_COLS = ["goals", "assists", "xg", "xa", "npxg", "key_passes", "shots"]
TOP_K = 10


def build_similarity_pairs(df: pd.DataFrame, top_k: int = TOP_K) -> pd.DataFrame:
    """df debe traer: player_id, season, minutes, position, y las columnas de
    SIMILARITY_STAT_COLS (totales de la temporada, no por 90'). Una fila = un jugador EN UNA
    TEMPORADA concreta, así que el mismo jugador con varias temporadas aparece varias veces;
    sus temporadas más parecidas pueden ser las de otros jugadores o las suyas propias (eso
    es información válida, muestra su evolución) -- solo se excluye la fila idéntica
    (mismo jugador y misma temporada), vía la diagonal de la matriz de similitud.

    Devuelve (player_id, season, similar_player_id, similar_season, rank, similarity) por
    cada jugador-temporada y cada uno de sus top_k más parecidos."""
    df = df.copy()
    for col in SIMILARITY_STAT_COLS:
        df[f"{col}_p90"] = df[col] * 90 / df["minutes"]
    df["position_bucket"] = df["position"].map(position_bucket)
    df = df[df["position_bucket"].isin(VALUATION_POSITIONS)].reset_index(drop=True)

    feature_cols = [f"{c}_p90" for c in SIMILARITY_STAT_COLS]
    x = StandardScaler().fit_transform(df[feature_cols])
    similarity_matrix = cosine_similarity(x)
    np.fill_diagonal(similarity_matrix, -1.0)  # nunca recomendarse la misma fila a sí misma

    player_ids = df["player_id"].to_numpy()
    seasons = df["season"].to_numpy()
    k = min(top_k, len(df) - 1) if len(df) > 1 else 0

    rows = []
    for i, player_id in enumerate(player_ids):
        top_idx = np.argsort(-similarity_matrix[i])[:k]
        for rank, j in enumerate(top_idx, start=1):
            rows.append(
                {
                    "player_id": int(player_id),
                    "season": str(seasons[i]),
                    "similar_player_id": int(player_ids[j]),
                    "similar_season": str(seasons[j]),
                    "rank": rank,
                    "similarity": float(similarity_matrix[i, j]),
                }
            )
    return pd.DataFrame(
        rows, columns=["player_id", "season", "similar_player_id", "similar_season", "rank", "similarity"]
    )
