-- Datos ya parseados desde raw.*, tipados pero todavía 1:1 con la estructura de cada fuente
-- (sin cruzar Understat con Transfermarkt todavía; eso ocurre en core.*).

-- Roster de una temporada (de main/getPlayersStats): sirve como lista maestra de qué
-- jugadores existen y a qué equipo pertenecen, para luego pedir su match log individual.
CREATE TABLE IF NOT EXISTS staging.understat_players_season (
    id BIGSERIAL PRIMARY KEY,
    raw_response_id BIGINT REFERENCES raw.understat_responses(id),
    understat_player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    competition TEXT NOT NULL,
    season TEXT NOT NULL,
    position TEXT,
    games INT,
    minutes INT,
    goals INT,
    assists INT,
    xg NUMERIC,
    xa NUMERIC,
    shots INT,
    key_passes INT,
    yellow_cards INT,
    red_cards INT,
    npg INT,
    npxg NUMERIC,
    UNIQUE (understat_player_id, season)
);

-- Match log por jugador (de getPlayerData/{id}): una fila por partido jugado. Trae también
-- fecha, equipos y marcador, así que es la fuente principal para reconstruir los partidos.
CREATE TABLE IF NOT EXISTS staging.understat_player_matches (
    id BIGSERIAL PRIMARY KEY,
    raw_response_id BIGINT REFERENCES raw.understat_responses(id),
    understat_player_id TEXT NOT NULL,
    understat_match_id TEXT NOT NULL,
    season TEXT,                      -- temporada tal como la reporta Understat para ese partido
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_goals INT NOT NULL,
    away_goals INT NOT NULL,
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
    UNIQUE (understat_player_id, understat_match_id)
);

CREATE TABLE IF NOT EXISTS staging.transfermarkt_players (
    id BIGSERIAL PRIMARY KEY,
    raw_page_id BIGINT REFERENCES raw.transfermarkt_pages(id),
    tm_player_id TEXT NOT NULL,
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    birth_date DATE,
    age INT,                          -- Transfermarkt sólo da la edad en la tabla de plantilla, no la fecha exacta
    nationality TEXT,
    position TEXT,
    height_cm INT,
    market_value_eur NUMERIC,
    valued_at DATE NOT NULL,          -- fecha del valor de mercado capturado en este scrape
    UNIQUE (tm_player_id, valued_at)
);
