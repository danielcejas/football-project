-- Snapshots crudos de cada fuente. Nunca se sobreescriben: cada scrape inserta una fila
-- nueva, así se puede reprocesar el parseo sin volver a golpear la web fuente.

-- Understat expone endpoints JSON internos (sin protección anti-bot) que usa su propio
-- frontend: getLeagueData, main/getPlayersStats y getPlayerData/{id}. Guardamos la
-- respuesta cruda tal cual.
CREATE TABLE IF NOT EXISTS raw.understat_responses (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    endpoint TEXT NOT NULL,         -- 'league_data', 'players_stats', 'player_data'
    competition TEXT NOT NULL,      -- 'La_liga'
    season TEXT NOT NULL,           -- '2024'
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_understat_responses_endpoint_scraped ON raw.understat_responses (endpoint, competition, season, scraped_at DESC);

CREATE TABLE IF NOT EXISTS raw.transfermarkt_pages (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    entity_type TEXT NOT NULL,      -- 'squad', 'player_profile', 'market_value_history', ...
    competition TEXT NOT NULL,
    season TEXT NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    html TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tm_pages_url_scraped ON raw.transfermarkt_pages (url, scraped_at DESC);
