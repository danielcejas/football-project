"""Dashboard mínimo: rankings Elo de clubes y jugadores de La Liga 2025/2026,
calculados en src/analytics/compute_rankings.py y guardados en marts.*"""

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import get_engine

BLUE = "#2a78d6"
AQUA = "#1baf7a"
RED = "#e34948"
NEUTRAL_GRAY = "#c3c2b7"

# marts.player_valuation/player_similarity/team_similarity ya guardan varias temporadas;
# el dashboard muestra solo la vigente hasta que se construya un selector de temporada.
CURRENT_SEASON = "2025"


def season_label(season: str) -> str:
    """'2025' (el año de inicio, como se guarda en la base de datos) -> '2025/2026' (como
    se conoce la temporada realmente) para mostrar en la UI."""
    return f"{season}/{int(season) + 1}"

st.set_page_config(page_title="Football Analytics — La Liga", layout="centered")


@st.cache_data(ttl=600)
def load_club_seasons() -> list[str]:
    query = "SELECT DISTINCT season FROM core.matches WHERE competition = 'La_liga' ORDER BY season DESC"
    return pd.read_sql(query, get_engine())["season"].tolist()


@st.cache_data(ttl=600)
def load_club_rankings(season: str) -> pd.DataFrame:
    """Elo de cada equipo al final (o al momento mas reciente disponible) de la
    temporada elegida -- antes se tomaba el ultimo partido de cada equipo en TODA su
    historia, mezclando equipos ya descendidos con la temporada vigente (issue #20)."""
    query = """
        WITH latest AS (
            SELECT DISTINCT ON (ceh.team_id) ceh.team_id, ceh.elo_after AS elo_rating, ceh.match_date
            FROM marts.club_elo_history ceh
            JOIN core.matches m ON m.id = ceh.match_id
            WHERE m.competition = 'La_liga' AND m.season = :season
            ORDER BY ceh.team_id, ceh.match_date DESC, ceh.id DESC
        )
        SELECT t.canonical_name AS team, latest.elo_rating, latest.match_date
        FROM latest
        JOIN core.teams t ON t.id = latest.team_id
        ORDER BY latest.elo_rating DESC
    """
    return pd.read_sql(text(query), get_engine(), params={"season": season})


@st.cache_data(ttl=600)
def load_player_rankings(limit: int = 20) -> pd.DataFrame:
    query = f"""
        SELECT p.canonical_name AS player, pr.elo_rating, pr.match_date
        FROM marts.player_rankings pr
        JOIN core.players p ON p.id = pr.player_id
        ORDER BY pr.elo_rating DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_player_valuation() -> pd.DataFrame:
    query = """
        SELECT p.canonical_name AS player, p.position, pv.market_value_eur,
               pv.predicted_value_eur, pv.value_gap_eur, pv.value_gap_pct
        FROM marts.player_valuation pv
        JOIN core.players p ON p.id = pv.player_id
        WHERE pv.season = :season
    """
    return pd.read_sql(text(query), get_engine(), params={"season": CURRENT_SEASON})


@st.cache_data(ttl=600)
def load_similarity_options() -> pd.DataFrame:
    """Una fila por jugador-temporada disponible en marts.player_similarity (las 3
    temporadas), para elegir la referencia del buscador de parecidos."""
    query = """
        SELECT DISTINCT p.id, p.canonical_name AS player, ps.season
        FROM marts.player_similarity ps
        JOIN core.players p ON p.id = ps.player_id
        ORDER BY player, ps.season DESC
    """
    df = pd.read_sql(query, get_engine())
    df["label"] = df["player"] + " (" + df["season"] + ")"
    return df


@st.cache_data(ttl=600)
def load_similar_players(player_id: int, season: str) -> pd.DataFrame:
    query = """
        SELECT p2.canonical_name AS similar_player, p2.position, ps.similar_season, ps.similarity
        FROM marts.player_similarity ps
        JOIN core.players p2 ON p2.id = ps.similar_player_id
        WHERE ps.player_id = :player_id AND ps.season = :season
        ORDER BY ps.rank
    """
    return pd.read_sql(text(query), get_engine(), params={"player_id": player_id, "season": season})


@st.cache_data(ttl=600)
def load_club_form(limit: int = 20) -> pd.DataFrame:
    query = f"""
        SELECT t.canonical_name AS team, cf.form_score, cf.matches_considered
        FROM marts.club_form cf
        JOIN core.teams t ON t.id = cf.team_id
        ORDER BY cf.form_score DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_player_form(limit: int = 20) -> pd.DataFrame:
    query = f"""
        SELECT p.canonical_name AS player, pf.form_score, pf.matches_considered
        FROM marts.player_form pf
        JOIN core.players p ON p.id = pf.player_id
        ORDER BY pf.form_score DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_club_week_best(limit: int = 10) -> pd.DataFrame:
    # las vistas de marts.* ya vienen ordenadas, pero ese orden no se conserva al pasar
    # por otro JOIN sin repetir el ORDER BY explícitamente en esta consulta
    query = f"""
        SELECT t.canonical_name AS team, cwb.match_date, cwb.delta
        FROM marts.club_week_best cwb
        JOIN core.teams t ON t.id = cwb.team_id
        ORDER BY cwb.delta DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_player_week_best(limit: int = 10) -> pd.DataFrame:
    query = f"""
        SELECT p.canonical_name AS player, pwb.match_date, pwb.delta
        FROM marts.player_week_best pwb
        JOIN core.players p ON p.id = pwb.player_id
        ORDER BY pwb.delta DESC
        LIMIT {limit}
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_young_talents(limit: int = 15) -> pd.DataFrame:
    query = f"""
        SELECT p.canonical_name AS player, yt.age, yt.market_value_eur,
               yt.predicted_value_eur, yt.value_gap_pct
        FROM marts.young_talents yt
        JOIN core.players p ON p.id = yt.player_id
        WHERE yt.season = :season
        ORDER BY yt.value_gap_pct DESC
        LIMIT {limit}
    """
    return pd.read_sql(text(query), get_engine(), params={"season": CURRENT_SEASON})


@st.cache_data(ttl=600)
def load_team_style_options() -> pd.DataFrame:
    """Una fila por equipo-temporada disponible en marts.team_similarity (las 3
    temporadas), para elegir la referencia del buscador de estilos parecidos."""
    query = """
        SELECT DISTINCT t.id, t.canonical_name AS team, ts.season
        FROM marts.team_similarity ts
        JOIN core.teams t ON t.id = ts.team_id
        ORDER BY team, ts.season DESC
    """
    df = pd.read_sql(query, get_engine())
    df["label"] = df["team"] + " (" + df["season"] + ")"
    return df


@st.cache_data(ttl=600)
def load_similar_teams(team_id: int, season: str) -> pd.DataFrame:
    query = """
        SELECT t2.canonical_name AS similar_team, ts.similar_season, ts.similarity
        FROM marts.team_similarity ts
        JOIN core.teams t2 ON t2.id = ts.similar_team_id
        WHERE ts.team_id = :team_id AND ts.season = :season
        ORDER BY ts.rank
    """
    return pd.read_sql(text(query), get_engine(), params={"team_id": team_id, "season": season})


def ranking_chart(
    df: pd.DataFrame, category_col: str, color: str, height: int, value_col: str = "elo_rating", x_title: str = "Rating Elo"
) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, color=color)
        .encode(
            x=alt.X(f"{value_col}:Q", title=x_title),
            y=alt.Y(f"{category_col}:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip(f"{category_col}:N", title=category_col.title()),
                alt.Tooltip(f"{value_col}:Q", title=x_title, format=".1f"),
            ],
        )
        .properties(height=height)
    )


def valuation_chart(df: pd.DataFrame) -> alt.Chart:
    axis_min = min(df["market_value_eur"].min(), df["predicted_value_eur"].min()) * 0.8
    axis_max = max(df["market_value_eur"].max(), df["predicted_value_eur"].max()) * 1.2
    log_scale = alt.Scale(type="log", domain=[axis_min, axis_max])

    reference_line = (
        alt.Chart(pd.DataFrame({"x": [axis_min, axis_max]}))
        .mark_line(strokeDash=[4, 4], color=NEUTRAL_GRAY)
        .encode(x=alt.X("x:Q", scale=log_scale), y=alt.Y("x:Q", scale=log_scale))
    )

    points = (
        alt.Chart(df)
        .mark_circle(size=70, opacity=0.8)
        .encode(
            x=alt.X("market_value_eur:Q", title="Valor de mercado (€)", scale=log_scale),
            y=alt.Y("predicted_value_eur:Q", title="Valor predicho por rendimiento (€)", scale=log_scale),
            color=alt.Color(
                "value_gap_pct:Q",
                title="Gap (%)",
                # dominio simétrico fijo y recortado: un par de casos extremos (jugadores
                # con valor de mercado casi cero) no deben estirar la escala para todos
                scale=alt.Scale(domain=[-100, 0, 100], range=[RED, NEUTRAL_GRAY, BLUE], clamp=True),
            ),
            tooltip=[
                alt.Tooltip("player:N", title="Jugador"),
                alt.Tooltip("market_value_eur:Q", title="Valor mercado", format=",.0f"),
                alt.Tooltip("predicted_value_eur:Q", title="Valor predicho", format=",.0f"),
                alt.Tooltip("value_gap_pct:Q", title="Gap %", format=".0f"),
            ],
        )
    )
    return (reference_line + points).properties(height=450)


st.title("⚽ Football Analytics — La Liga 2025/2026")
st.caption(
    "Rating Elo propio (no oficial): sube o baja tras cada partido según el resultado, "
    "el rival y, para jugadores, su rendimiento individual. Datos: Understat + Transfermarkt."
)

player_df = load_player_rankings()

st.header("Ranking de clubes")
st.caption(
    "Elo de cada equipo al final (o al momento más reciente) de la temporada elegida — "
    "no siempre son 20 equipos: en una temporada histórica solo aparecen los que "
    "compitieron esa campaña."
)
club_season = st.selectbox("Temporada", load_club_seasons(), format_func=season_label, key="club_season")
club_df = load_club_rankings(club_season)
st.altair_chart(ranking_chart(club_df, "team", BLUE, height=24 * len(club_df)), use_container_width=True)
with st.expander("Ver tabla"):
    st.dataframe(
        club_df.assign(elo_rating=club_df["elo_rating"].round(1)),
        use_container_width=True,
        hide_index=True,
    )

st.header("Ranking de jugadores (top 20)")
st.altair_chart(ranking_chart(player_df, "player", AQUA, height=24 * len(player_df)), use_container_width=True)
with st.expander("Ver tabla"):
    st.dataframe(
        player_df.assign(elo_rating=player_df["elo_rating"].round(1)),
        use_container_width=True,
        hide_index=True,
    )

st.header("Valoración Moneyball (delanteros y centrocampistas)")
st.caption(
    "Compara el valor de mercado real con el que 'predice' un modelo que sólo mira goles, "
    "asistencias, xG, xA, pases clave, edad y posición de esta temporada. Azul = el modelo "
    "cree que debería valer más de lo que vale (posible ganga); rojo = el mercado paga más "
    "de lo que el rendimiento de esta temporada sugiere. Limitado a F/M porque Understat no "
    "da métricas defensivas, y no ve reputación, trayectoria ni potencial: el jugador típico "
    "sale en azul (rinde en línea o por encima de lo que cuesta), pero superestrellas "
    "consagradas (ej. Mbappé, Vinícius Júnior, Pedri) salen sistemáticamente en rojo con un "
    "gap grande en las 3 temporadas — es la prima de reputación/trofeos que paga el mercado "
    "y que este modelo, al mirar solo producción de la temporada, no puede ver. Es el "
    "comportamiento esperado, no un error."
)
valuation_df = load_player_valuation()
st.altair_chart(valuation_chart(valuation_df), use_container_width=True)

VALUATION_COLUMN_CONFIG = {
    "player": st.column_config.TextColumn("Jugador"),
    "market_value_eur": st.column_config.NumberColumn("Valor mercado (€)", format="compact"),
    "predicted_value_eur": st.column_config.NumberColumn("Valor predicho (€)", format="compact"),
    "value_gap_pct": st.column_config.NumberColumn("Gap", format="%.0f%%"),
}
VALUATION_DISPLAY_COLS = ["player", "market_value_eur", "predicted_value_eur", "value_gap_pct"]

col1, col2 = st.columns(2)
with col1:
    st.subheader("Posibles gangas")
    st.dataframe(
        valuation_df.nlargest(10, "value_gap_eur")[VALUATION_DISPLAY_COLS],
        use_container_width=True,
        hide_index=True,
        column_config=VALUATION_COLUMN_CONFIG,
    )
with col2:
    st.subheader("Posibles sobrevaloraciones")
    st.dataframe(
        valuation_df.nsmallest(10, "value_gap_eur")[VALUATION_DISPLAY_COLS],
        use_container_width=True,
        hide_index=True,
        column_config=VALUATION_COLUMN_CONFIG,
    )

st.header("Jugadores parecidos")
st.caption(
    "Similitud coseno sobre el perfil de producción por 90' (goles, asistencias, xG, xA, "
    "tiros, pases clave), estandarizado — compara estilo de producción, no volumen total. "
    "Busca entre las 3 temporadas: un jugador puede salir parecido a sí mismo en otra "
    "temporada (muestra su evolución) o a otro jugador de cualquier año. Limitado a F/M "
    "por la misma razón que la valoración: sin stats defensivas, un 'parecido' entre "
    "defensas o porteros no sería real."
)
similarity_options = load_similarity_options()
selected_label = st.selectbox("Elige un jugador y temporada", similarity_options["label"])
selected_row = similarity_options.loc[similarity_options["label"] == selected_label].iloc[0]
similar_df = load_similar_players(int(selected_row["id"]), selected_row["season"])
st.dataframe(
    similar_df[["similar_player", "position", "similar_season", "similarity"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "similar_player": st.column_config.TextColumn("Jugador parecido"),
        "position": st.column_config.TextColumn("Posición"),
        "similar_season": st.column_config.TextColumn("Temporada"),
        "similarity": st.column_config.NumberColumn("Similitud", format="%.3f"),
    },
)

st.header("Equipos que juegan parecido")
st.caption(
    "Similitud coseno sobre el perfil de estilo por partido (xG/xGA a favor y en contra, "
    "ppda —presión, más bajo es más agresiva— y deep —pases cerca del área rival, proxy "
    "de verticalidad—), estandarizado y promediado en la temporada. Busca entre las 3 "
    "temporadas: un equipo puede salir parecido a sí mismo en otro año (identidad de "
    "juego que se mantiene) o a otro equipo de cualquier temporada."
)
team_style_options = load_team_style_options()
selected_team_label = st.selectbox("Elige un equipo y temporada", team_style_options["label"])
selected_team_row = team_style_options.loc[team_style_options["label"] == selected_team_label].iloc[0]
similar_teams_df = load_similar_teams(int(selected_team_row["id"]), selected_team_row["season"])
st.dataframe(
    similar_teams_df[["similar_team", "similar_season", "similarity"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "similar_team": st.column_config.TextColumn("Equipo parecido"),
        "similar_season": st.column_config.TextColumn("Temporada"),
        "similarity": st.column_config.NumberColumn("Similitud", format="%.3f"),
    },
)

st.header("Forma reciente (últimos 5 partidos)")
st.caption("Suma de los deltas de Elo de los últimos 5 partidos — mide momento, no nivel absoluto.")
form_col1, form_col2 = st.columns(2)
with form_col1:
    club_form_df = load_club_form()
    st.altair_chart(
        ranking_chart(club_form_df, "team", BLUE, height=22 * len(club_form_df), value_col="form_score", x_title="Forma"),
        use_container_width=True,
    )
with form_col2:
    player_form_df = load_player_form()
    st.altair_chart(
        ranking_chart(player_form_df, "player", AQUA, height=22 * len(player_form_df), value_col="form_score", x_title="Forma"),
        use_container_width=True,
    )

st.header("Mejores de la semana")
st.caption("Mayor delta de Elo en un único partido, dentro de los últimos 7 días respecto al partido más reciente registrado.")
week_col1, week_col2 = st.columns(2)
WEEK_COLUMN_CONFIG = {
    "match_date": st.column_config.DateColumn("Fecha"),
    "delta": st.column_config.NumberColumn("Delta Elo", format="%.1f"),
}
with week_col1:
    st.subheader("Clubes")
    st.dataframe(
        load_club_week_best(),
        use_container_width=True,
        hide_index=True,
        column_config={"team": st.column_config.TextColumn("Equipo"), **WEEK_COLUMN_CONFIG},
    )
with week_col2:
    st.subheader("Jugadores")
    st.dataframe(
        load_player_week_best(),
        use_container_width=True,
        hide_index=True,
        column_config={"player": st.column_config.TextColumn("Jugador"), **WEEK_COLUMN_CONFIG},
    )

st.header("Futuras promesas (U21)")
st.caption(
    "Jugadores de 21 años o menos cuyo rendimiento (mismo modelo que la valoración Moneyball) "
    "ya justificaría un valor de mercado más alto del que tienen hoy."
)
st.dataframe(
    load_young_talents(),
    use_container_width=True,
    hide_index=True,
    column_config={
        "player": st.column_config.TextColumn("Jugador"),
        "age": st.column_config.NumberColumn("Edad"),
        "market_value_eur": st.column_config.NumberColumn("Valor mercado (€)", format="compact"),
        "predicted_value_eur": st.column_config.NumberColumn("Valor predicho (€)", format="compact"),
        "value_gap_pct": st.column_config.NumberColumn("Gap", format="%.0f%%"),
    },
)
