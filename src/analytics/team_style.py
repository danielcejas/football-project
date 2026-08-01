"""Equipos que juegan parecido: perfil de estilo por partido (xG/xGA a favor, presión
—ppda, cuanto más bajo más agresiva— y directness —deep, pases cerca del área rival—),
promediado por temporada, estandarizado, y comparado por similitud coseno.

A diferencia de la valoración/similitud de jugadores, aquí sí tiene sentido comparar
cualquier equipo contra cualquier otro (no hay una restricción de posición): el estilo de
un equipo entero mezcla fases ofensivas y defensivas por diseño.
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

STYLE_COLS = ["xg", "xga", "ppda", "ppda_allowed", "deep", "deep_allowed"]
TOP_K = 5


def build_team_similarity_pairs(df: pd.DataFrame, top_k: int = TOP_K) -> pd.DataFrame:
    """df debe traer: team_id, season, y las medias por partido de STYLE_COLS (una fila
    por equipo-temporada). Un equipo con varias temporadas aparece varias veces; sus
    temporadas más parecidas pueden ser las de otros equipos o las suyas propias (muestra
    su evolución de estilo) -- solo se excluye la fila idéntica (mismo equipo y misma
    temporada), vía la diagonal de la matriz de similitud.

    Devuelve (team_id, season, similar_team_id, similar_season, rank, similarity)."""
    df = df.reset_index(drop=True)
    x = StandardScaler().fit_transform(df[STYLE_COLS])
    similarity_matrix = cosine_similarity(x)
    np.fill_diagonal(similarity_matrix, -1.0)

    team_ids = df["team_id"].to_numpy()
    seasons = df["season"].to_numpy()
    k = min(top_k, len(df) - 1) if len(df) > 1 else 0

    rows = []
    for i, team_id in enumerate(team_ids):
        top_idx = np.argsort(-similarity_matrix[i])[:k]
        for rank, j in enumerate(top_idx, start=1):
            rows.append(
                {
                    "team_id": int(team_id),
                    "season": str(seasons[i]),
                    "similar_team_id": int(team_ids[j]),
                    "similar_season": str(seasons[j]),
                    "rank": rank,
                    "similarity": float(similarity_matrix[i, j]),
                }
            )
    return pd.DataFrame(
        rows, columns=["team_id", "season", "similar_team_id", "similar_season", "rank", "similarity"]
    )
