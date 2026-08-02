import pandas as pd
import pytest

from src.analytics.valuation import fit_valuation_model, position_bucket


def test_position_bucket_takes_primary_token():
    assert position_bucket("F M S") == "F"
    assert position_bucket("GK S") == "GK"
    assert position_bucket("S") == "U"
    assert position_bucket(None) == "U"


def _synthetic_players() -> pd.DataFrame:
    # dos delanteros con las mismas stats por 90' y edad, pero valor de mercado distinto;
    # el resto del grupo ancla el modelo para que el patrón "misma pinta, distinto precio"
    # se note en el residuo.
    rows = [
        {"player_id": 1, "minutes": 2700, "goals": 20, "assists": 5, "xg": 18, "xa": 4, "npxg": 16, "key_passes": 40, "age": 25, "position": "F", "market_value_eur": 40_000_000},
        {"player_id": 2, "minutes": 2700, "goals": 20, "assists": 5, "xg": 18, "xa": 4, "npxg": 16, "key_passes": 40, "age": 25, "position": "F", "market_value_eur": 10_000_000},
        {"player_id": 3, "minutes": 2700, "goals": 2, "assists": 1, "xg": 2, "xa": 1, "npxg": 2, "key_passes": 10, "age": 25, "position": "F", "market_value_eur": 5_000_000},
        {"player_id": 4, "minutes": 2700, "goals": 5, "assists": 5, "xg": 4, "xa": 4, "npxg": 4, "key_passes": 60, "age": 28, "position": "M", "market_value_eur": 15_000_000},
        {"player_id": 5, "minutes": 2700, "goals": 1, "assists": 1, "xg": 1, "xa": 1, "npxg": 1, "key_passes": 5, "age": 30, "position": "D", "market_value_eur": 8_000_000},
    ]
    return pd.DataFrame(rows)


def test_fit_valuation_model_flags_underpriced_player_as_positive_gap():
    df = fit_valuation_model(_synthetic_players())

    player_1 = df[df["player_id"] == 1].iloc[0]
    player_2 = df[df["player_id"] == 2].iloc[0]

    # mismas stats y edad, pero el jugador 2 vale 4x menos -> debería salir con un
    # value_gap más alto (más "infravalorado") que el jugador 1
    assert player_2["value_gap_eur"] > player_1["value_gap_eur"]


def test_fit_valuation_model_output_columns():
    df = fit_valuation_model(_synthetic_players())
    for col in ("predicted_value_eur", "value_gap_eur", "value_gap_pct"):
        assert col in df.columns
    assert df["predicted_value_eur"].gt(0).all()


def test_smearing_correction_raises_predictions_above_naive_exponential():
    # exp(prediccion) a secas subestima sistematicamente (estima la mediana, no la
    # media, de una distribucion sesgada a la derecha) -- la correccion de Duan debe
    # dejar las predicciones por encima de esa version sin corregir.
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    from src.analytics.valuation import PER90_STAT_COLS, RIDGE_ALPHA, VALUATION_POSITIONS, add_per90_features

    raw = _synthetic_players()
    corrected = fit_valuation_model(raw.copy())

    prepared = add_per90_features(raw)
    prepared = prepared[prepared["position_bucket"].isin(VALUATION_POSITIONS)].reset_index(drop=True)
    feature_cols = [f"{c}_p90" for c in PER90_STAT_COLS] + ["age"]
    x = pd.concat([prepared[feature_cols], pd.get_dummies(prepared["position_bucket"], prefix="pos")], axis=1)
    y = np.log(prepared["market_value_eur"])
    x_scaled = StandardScaler().fit_transform(x)
    model = Ridge(alpha=RIDGE_ALPHA).fit(x_scaled, y)
    naive_predicted = np.exp(model.predict(x_scaled))

    assert corrected["predicted_value_eur"].sum() > naive_predicted.sum()
