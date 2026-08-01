-- Valoración estilo Moneyball: valor de mercado real vs. valor "predicho" por un modelo
-- que sólo mira rendimiento (stats por 90', edad, posición). Un value_gap positivo
-- significa que el modelo cree que el jugador debería valer más de lo que vale en el
-- mercado (posible ganga); negativo, que el mercado le paga más de lo que su rendimiento
-- sugiere. Se recalcula desde cero en cada ejecución (no es una serie temporal como el Elo).

CREATE TABLE IF NOT EXISTS marts.player_valuation (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL UNIQUE REFERENCES core.players(id),
    competition TEXT NOT NULL,
    season TEXT NOT NULL,
    age INT,
    minutes INT NOT NULL,
    market_value_eur NUMERIC NOT NULL,
    predicted_value_eur NUMERIC NOT NULL,
    value_gap_eur NUMERIC NOT NULL,
    value_gap_pct NUMERIC NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
