"""Valoración estilo Moneyball: entrena una regresión lineal de
log(valor_de_mercado) ~ stats por 90' + edad + posición sobre los propios jugadores de
la competición/temporada, y usa el residuo (valor predicho vs. valor real) como señal de
jugadores infra/sobrevalorados.

Es una lectura descriptiva (in-sample) de qué tan bien el valor de mercado actual se
explica por el rendimiento, no un modelo predictivo evaluado con hold-out: para esta
funcionalidad ("¿quién rinde más de lo que cuesta?") es exactamente lo que se necesita.

Limitado a delanteros y centrocampistas (VALUATION_POSITIONS): Understat sólo da stats
de producción ofensiva (goles, asistencias, xG, xA, pases clave), sin nada defensivo
(entradas, intercepciones, despejes, paradas). Mezclar defensas/porteros en el mismo
modelo no los infravalora "de verdad" — sólo refleja que no tenemos ninguna variable que
explique su valor, y esos residuos gigantes además distorsionan el ajuste para el resto.
Valorar defensas/porteros con seriedad necesitaría otra fuente de datos.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

PER90_STAT_COLS = ["goals", "assists", "xg", "xa", "npxg", "key_passes"]
VALUATION_POSITIONS = ("F", "M")
RIDGE_ALPHA = 5.0


def position_bucket(position: str | None) -> str:
    """Understat da posiciones tipo 'D F M S' (varias, la primera es la principal).
    'S' a solas (jugador casi siempre suplente sin posición clara) -> desconocida."""
    if not position:
        return "U"
    primary = position.split()[0]
    return primary if primary in ("GK", "D", "M", "F") else "U"


def add_per90_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in PER90_STAT_COLS:
        df[f"{col}_p90"] = df[col] * 90 / df["minutes"]
    df["position_bucket"] = df["position"].map(position_bucket)
    return df


def fit_valuation_model(df: pd.DataFrame) -> pd.DataFrame:
    """df debe traer: minutes, goals, assists, xg, xa, npxg, key_passes, age, position,
    market_value_eur. Devuelve una copia (sólo delanteros/centrocampistas, ver
    VALUATION_POSITIONS) con predicted_value_eur, value_gap_eur, value_gap_pct añadidos."""
    df = add_per90_features(df)
    df = df[df["position_bucket"].isin(VALUATION_POSITIONS)].reset_index(drop=True)

    feature_cols = [f"{c}_p90" for c in PER90_STAT_COLS] + ["age"]
    x_numeric = df[feature_cols]
    x_position = pd.get_dummies(df["position_bucket"], prefix="pos")
    x = pd.concat([x_numeric, x_position], axis=1)
    y = np.log(df["market_value_eur"])

    # con ~200 jugadores y variables muy correlacionadas entre sí (goles~xG~npxG,
    # asistencias~xA), una regresión lineal sin regularizar da coeficientes inestables;
    # Ridge (con las variables estandarizadas para que la penalización sea comparable
    # entre ellas) lo estabiliza a costa de un sesgo pequeño y conocido.
    x_scaled = StandardScaler().fit_transform(x)
    model = Ridge(alpha=RIDGE_ALPHA)
    model.fit(x_scaled, y)

    df["predicted_value_eur"] = np.exp(model.predict(x_scaled))
    df["value_gap_eur"] = df["predicted_value_eur"] - df["market_value_eur"]
    df["value_gap_pct"] = df["value_gap_eur"] / df["market_value_eur"] * 100
    return df
