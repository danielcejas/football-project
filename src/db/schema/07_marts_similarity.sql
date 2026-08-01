-- Top-K jugadores más parecidos a cada jugador, por perfil de producción ofensiva por 90'
-- (ver src/analytics/similarity.py). Igual que la valoración, limitado a F/M: sin stats
-- defensivas de por medio, "parecido" entre defensas/porteros no sería un hallazgo real.

CREATE TABLE IF NOT EXISTS marts.player_similarity (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES core.players(id),
    similar_player_id BIGINT NOT NULL REFERENCES core.players(id),
    rank INT NOT NULL,
    similarity NUMERIC NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (player_id, rank)
);
