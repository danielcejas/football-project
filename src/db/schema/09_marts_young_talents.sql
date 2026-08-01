-- Futuras promesas: jugadores U21 cuyo rendimiento (según el mismo modelo de
-- src/analytics/valuation.py) ya justificaría un valor de mercado bastante más alto del
-- que tienen hoy. Reutiliza marts.player_valuation en vez de un modelo nuevo: "promesa" es
-- justo la intersección de "joven" + "el mercado todavía no le paga por lo que rinde".

CREATE OR REPLACE VIEW marts.young_talents AS
SELECT player_id, competition, season, age, minutes, market_value_eur,
       predicted_value_eur, value_gap_eur, value_gap_pct
FROM marts.player_valuation
WHERE age <= 21
ORDER BY value_gap_pct DESC;
