-- Estilo de equipo: usa el endpoint getLeagueData de Understat (historial por partido y
-- por equipo, con xG/xGA y dos proxies tácticos que FBref no habría dado tampoco: ppda
-- —pases del rival permitidos por acción defensiva antes de recuperar, cuanto más bajo más
-- presión— y deep —pases completados cerca del área rival, proxy de directness/verticalidad—.

CREATE TABLE IF NOT EXISTS staging.understat_team_matches (
    id BIGSERIAL PRIMARY KEY,
    raw_response_id BIGINT REFERENCES raw.understat_responses(id),
    team TEXT NOT NULL,
    season TEXT NOT NULL,
    match_date DATE NOT NULL,
    is_home BOOLEAN NOT NULL,
    goals_for INT,
    goals_against INT,
    xg NUMERIC,
    xga NUMERIC,
    npxg NUMERIC,
    npxga NUMERIC,
    ppda NUMERIC,
    ppda_allowed NUMERIC,
    deep INT,
    deep_allowed INT,
    result TEXT,
    points INT,
    UNIQUE (team, match_date)
);

CREATE TABLE IF NOT EXISTS core.team_match_stats (
    id BIGSERIAL PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES core.matches(id),
    team_id BIGINT NOT NULL REFERENCES core.teams(id),
    is_home BOOLEAN NOT NULL,
    goals_for INT,
    goals_against INT,
    xg NUMERIC,
    xga NUMERIC,
    npxg NUMERIC,
    npxga NUMERIC,
    ppda NUMERIC,
    ppda_allowed NUMERIC,
    deep INT,
    deep_allowed INT,
    UNIQUE (match_id, team_id)
);

CREATE TABLE IF NOT EXISTS marts.team_similarity (
    id BIGSERIAL PRIMARY KEY,
    team_id BIGINT NOT NULL REFERENCES core.teams(id),
    similar_team_id BIGINT NOT NULL REFERENCES core.teams(id),
    rank INT NOT NULL,
    similarity NUMERIC NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (team_id, rank)
);
