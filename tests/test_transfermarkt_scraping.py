import datetime

from src.scraping.transfermarkt.run import _valued_at_for_season


def test_valued_at_for_past_season_uses_season_end():
    # temporada 2023/24 -> 30 de junio de 2024, sin importar cuando se scrapee
    assert _valued_at_for_season("2023") == "2024-06-30"


def test_valued_at_for_future_season_end_uses_todays_date():
    # una temporada en curso (fin de temporada en el futuro) sigue usando hoy, como antes
    far_future_season = str(datetime.date.today().year + 5)
    assert _valued_at_for_season(far_future_season) == datetime.date.today().isoformat()
