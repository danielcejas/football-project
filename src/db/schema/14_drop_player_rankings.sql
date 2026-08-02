-- marts.player_rankings (definida en 05_marts.sql) tiene el mismo bug que
-- marts.club_rankings (issue #20): toma el ultimo partido de cada jugador en TODA su
-- historia, sin filtrar por temporada. Con 3 temporadas de historial, el "top 20 actual"
-- podia incluir jugadores que ya no juegan en La Liga (ej. Toni Kroos, retirado tras
-- 2023/24; Artem Dovbyk, transferido a la Roma) con su rating de una temporada pasada.
-- Se retira: app/streamlit_app.py ya no la usa, consulta marts.player_elo_history
-- directamente, filtrando por competicion/temporada (issue #21).

DROP VIEW IF EXISTS marts.player_rankings;
