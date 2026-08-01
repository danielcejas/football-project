-- Similitud entre temporadas: hasta ahora player_similarity/team_similarity solo comparaban
-- dentro de una misma temporada (similar_player_id/similar_team_id venian siempre de la misma
-- "season" que la fila de referencia). Se anade similar_season para poder guardar coincidencias
-- de OTRA temporada -- el buscador de "parecidos" pasa a comparar entre las 3 temporadas.

ALTER TABLE marts.player_similarity ADD COLUMN IF NOT EXISTS similar_season TEXT;
UPDATE marts.player_similarity SET similar_season = season WHERE similar_season IS NULL;
ALTER TABLE marts.player_similarity ALTER COLUMN similar_season SET NOT NULL;

ALTER TABLE marts.team_similarity ADD COLUMN IF NOT EXISTS similar_season TEXT;
UPDATE marts.team_similarity SET similar_season = season WHERE similar_season IS NULL;
ALTER TABLE marts.team_similarity ALTER COLUMN similar_season SET NOT NULL;
