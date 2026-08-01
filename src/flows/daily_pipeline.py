"""Flow diario: scrapea Understat + Transfermarkt, reconstruye core.* y recalcula todas
las tablas de marts.*. Envuelve funciones que ya existían y se probaron sueltas — este
flow sólo les da reintentos, logs y estructura para poder programarlo.

Ejecutar una vez: python -m src.flows.daily_pipeline
Programarlo: ver el bloque main más abajo (daily_pipeline.serve(...)).
"""

from prefect import flow, task

from src.analytics.compute_rankings import compute_and_store as _compute_rankings
from src.analytics.compute_similarity import run as _compute_similarity
from src.analytics.compute_team_style import run as _compute_team_style
from src.analytics.compute_valuation import run as _compute_valuation
from src.etl.build_core import run as _build_core
from src.scraping.transfermarkt.run import run as _scrape_transfermarkt
from src.scraping.understat.run import run as _scrape_understat_players
from src.scraping.understat.run_league_data import run as _scrape_understat_league_data


@task(retries=2, retry_delay_seconds=60)
def scrape_understat_players(competition: str, season: str) -> None:
    _scrape_understat_players(competition, season)


@task(retries=2, retry_delay_seconds=60)
def scrape_understat_league_data(competition_space: str, season: str) -> None:
    _scrape_understat_league_data(competition_space, season)


@task(retries=2, retry_delay_seconds=60)
def scrape_transfermarkt(league_slug: str, competition_code: str, season: str) -> None:
    _scrape_transfermarkt(league_slug, competition_code, season)


@task(retries=1)
def build_core(competition: str, season: str) -> None:
    _build_core(competition, season)


@task(retries=1)
def compute_rankings(competition: str, season: str) -> None:
    _compute_rankings(competition, season)


@task(retries=1)
def compute_valuation(competition: str, season: str) -> None:
    _compute_valuation(competition, season)


@task(retries=1)
def compute_similarity(competition: str) -> None:
    _compute_similarity(competition)


@task(retries=1)
def compute_team_style(competition: str, season: str) -> None:
    _compute_team_style(competition, season)


@flow(name="football-daily-pipeline", log_prints=True)
def daily_pipeline(
    competition_underscore: str = "La_liga",
    competition_space: str = "La liga",
    competition_code: str = "ES1",
    league_slug: str = "laliga",
    season: str = "2025",
) -> None:
    # scraping: cada fuente es independiente, pero se llaman en serie para no golpear
    # varias webs a la vez desde la misma máquina
    scrape_understat_players(competition_underscore, season)
    scrape_understat_league_data(competition_space, season)
    scrape_transfermarkt(league_slug, competition_code, season)

    # ETL: normaliza todo lo scrapeado a core.* (depende de que el scraping ya terminase)
    build_core(competition_underscore, season)

    # analítica: cada una lee de core.* y escribe su propia tabla en marts.*, son
    # independientes entre sí pero todas dependen del build_core de arriba
    compute_rankings(competition_underscore, season)
    compute_valuation(competition_underscore, season)
    compute_similarity(competition_underscore)
    compute_team_style(competition_underscore, season)


if __name__ == "__main__":
    daily_pipeline()
