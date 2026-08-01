-- Antes de meter temporadas historicas, estas tres tablas solo tenian una fila global por
-- jugador/equipo (UNIQUE sin season), asi que calcular una temporada distinta a la vigente
-- sobrescribia (player_valuation) o borraba entera la tabla via TRUNCATE (similarity/
-- team_similarity) los datos de la temporada actual. Se anade season/competition como
-- parte de la identidad de cada fila para que convivan varias temporadas.
--
-- Los datos existentes son todos de La_liga/2025 (unica competicion/temporada calculada
-- hasta ahora), asi que el backfill de las columnas nuevas usa ese valor fijo.

ALTER TABLE marts.player_valuation DROP CONSTRAINT IF EXISTS player_valuation_player_id_key;
ALTER TABLE marts.player_valuation ADD CONSTRAINT player_valuation_player_id_season_key UNIQUE (player_id, season);

ALTER TABLE marts.player_similarity ADD COLUMN IF NOT EXISTS competition TEXT;
ALTER TABLE marts.player_similarity ADD COLUMN IF NOT EXISTS season TEXT;
UPDATE marts.player_similarity SET competition = 'La_liga', season = '2025' WHERE season IS NULL;
ALTER TABLE marts.player_similarity ALTER COLUMN competition SET NOT NULL;
ALTER TABLE marts.player_similarity ALTER COLUMN season SET NOT NULL;
ALTER TABLE marts.player_similarity DROP CONSTRAINT IF EXISTS player_similarity_player_id_rank_key;
ALTER TABLE marts.player_similarity ADD CONSTRAINT player_similarity_player_id_season_rank_key UNIQUE (player_id, season, rank);

ALTER TABLE marts.team_similarity ADD COLUMN IF NOT EXISTS competition TEXT;
ALTER TABLE marts.team_similarity ADD COLUMN IF NOT EXISTS season TEXT;
UPDATE marts.team_similarity SET competition = 'La_liga', season = '2025' WHERE season IS NULL;
ALTER TABLE marts.team_similarity ALTER COLUMN competition SET NOT NULL;
ALTER TABLE marts.team_similarity ALTER COLUMN season SET NOT NULL;
ALTER TABLE marts.team_similarity DROP CONSTRAINT IF EXISTS team_similarity_team_id_rank_key;
ALTER TABLE marts.team_similarity ADD CONSTRAINT team_similarity_team_id_season_rank_key UNIQUE (team_id, season, rank);
