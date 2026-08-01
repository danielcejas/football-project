-- Forma reciente = suma de los últimos 5 deltas de Elo (mismo concepto que el ranking,
-- pero mirando sólo una ventana corta en vez de toda la temporada).
-- "De la semana" = mejores deltas de un único partido dentro de los últimos 7 días
-- respecto al partido más reciente que haya en la tabla (no es necesariamente domingo a
-- domingo, es una ventana relativa a los datos que tengamos).

CREATE OR REPLACE VIEW marts.club_form AS
SELECT team_id, SUM(delta) AS form_score, COUNT(*) AS matches_considered, MAX(match_date) AS as_of
FROM (
    SELECT team_id, match_date, delta,
           ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY match_date DESC, id DESC) AS rn
    FROM marts.club_elo_history
) recent
WHERE rn <= 5
GROUP BY team_id;

CREATE OR REPLACE VIEW marts.player_form AS
SELECT player_id, SUM(delta) AS form_score, COUNT(*) AS matches_considered, MAX(match_date) AS as_of
FROM (
    SELECT player_id, match_date, delta,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY match_date DESC, id DESC) AS rn
    FROM marts.player_elo_history
) recent
WHERE rn <= 5
GROUP BY player_id;

CREATE OR REPLACE VIEW marts.club_week_best AS
WITH latest AS (SELECT MAX(match_date) AS max_date FROM marts.club_elo_history)
SELECT ceh.team_id, ceh.match_id, ceh.match_date, ceh.delta
FROM marts.club_elo_history ceh, latest
WHERE ceh.match_date >= latest.max_date - INTERVAL '6 days'
ORDER BY ceh.delta DESC;

CREATE OR REPLACE VIEW marts.player_week_best AS
WITH latest AS (SELECT MAX(match_date) AS max_date FROM marts.player_elo_history)
SELECT peh.player_id, peh.match_id, peh.match_date, peh.delta
FROM marts.player_elo_history peh, latest
WHERE peh.match_date >= latest.max_date - INTERVAL '6 days'
ORDER BY peh.delta DESC;
