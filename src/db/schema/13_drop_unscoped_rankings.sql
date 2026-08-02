-- marts.club_rankings (definida en 05_marts.sql) tomaba el ultimo partido de cada
-- equipo en TODA su historia, sin filtrar por temporada. Con 3 temporadas de historial
-- esto mezclaba equipos ya descendidos (Cadiz, Almeria...) con la temporada vigente
-- (issue #20). Se retira: app/streamlit_app.py ya no la usa, consulta
-- marts.club_elo_history directamente, filtrando por competicion/temporada.
--
-- marts.player_rankings tiene el mismo bug pero se deja para la issue #21 (alcance
-- separado) -- no tocar aqui para no romper load_player_rankings() a medias.

DROP VIEW IF EXISTS marts.club_rankings;
