-- Modelo normalizado que cruza Understat y Transfermarkt en entidades únicas.

CREATE TABLE IF NOT EXISTS core.teams (
    id BIGSERIAL PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    understat_team_name TEXT,
    tm_team_name TEXT
);

CREATE TABLE IF NOT EXISTS core.players (
    id BIGSERIAL PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    understat_player_id TEXT UNIQUE,
    tm_player_id TEXT UNIQUE,
    birth_date DATE,
    nationality TEXT,
    position TEXT
);

CREATE TABLE IF NOT EXISTS core.matches (
    id BIGSERIAL PRIMARY KEY,
    understat_match_id TEXT NOT NULL UNIQUE,
    match_date DATE NOT NULL,
    competition TEXT NOT NULL,
    season TEXT NOT NULL,
    home_team_id BIGINT NOT NULL REFERENCES core.teams(id),
    away_team_id BIGINT NOT NULL REFERENCES core.teams(id),
    home_score INT NOT NULL,
    away_score INT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.player_match_stats (
    id BIGSERIAL PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES core.matches(id),
    player_id BIGINT NOT NULL REFERENCES core.players(id),
    team_id BIGINT NOT NULL REFERENCES core.teams(id),
    position TEXT,
    minutes INT,
    goals INT,
    assists INT,
    shots INT,
    key_passes INT,
    xg NUMERIC,
    xa NUMERIC,
    npg INT,
    npxg NUMERIC,
    UNIQUE (match_id, player_id)
);

CREATE TABLE IF NOT EXISTS core.market_values (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES core.players(id),
    valued_at DATE NOT NULL,
    market_value_eur NUMERIC NOT NULL,
    UNIQUE (player_id, valued_at)
);
