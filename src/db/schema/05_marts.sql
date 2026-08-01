-- Tablas de salida consumidas por la app. Un historial por partido + una vista con el rating
-- vigente de cada equipo/jugador (el último por fecha).

CREATE TABLE IF NOT EXISTS marts.club_elo_history (
    id BIGSERIAL PRIMARY KEY,
    team_id BIGINT NOT NULL REFERENCES core.teams(id),
    match_id BIGINT NOT NULL REFERENCES core.matches(id),
    match_date DATE NOT NULL,
    elo_before NUMERIC NOT NULL,
    elo_after NUMERIC NOT NULL,
    delta NUMERIC NOT NULL,
    UNIQUE (team_id, match_id)
);

CREATE TABLE IF NOT EXISTS marts.player_elo_history (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES core.players(id),
    match_id BIGINT NOT NULL REFERENCES core.matches(id),
    match_date DATE NOT NULL,
    elo_before NUMERIC NOT NULL,
    elo_after NUMERIC NOT NULL,
    delta NUMERIC NOT NULL,
    UNIQUE (player_id, match_id)
);

CREATE OR REPLACE VIEW marts.club_rankings AS
SELECT DISTINCT ON (team_id)
    team_id, match_date, elo_after AS elo_rating
FROM marts.club_elo_history
ORDER BY team_id, match_date DESC, id DESC;

CREATE OR REPLACE VIEW marts.player_rankings AS
SELECT DISTINCT ON (player_id)
    player_id, match_date, elo_after AS elo_rating
FROM marts.player_elo_history
ORDER BY player_id, match_date DESC, id DESC;
