"""Parsea el HTML de raw.transfermarkt_pages (páginas de plantilla) y lo vuelca en
staging.transfermarkt_players."""

import re

from bs4 import BeautifulSoup
from sqlalchemy import text

from src.db.connection import get_engine

MARKET_VALUE_RE = re.compile(r"€([\d.]+)(m|k)?")


def _parse_market_value(text_value: str) -> float | None:
    text_value = text_value.strip()
    if text_value in ("-", ""):
        return None
    match = MARKET_VALUE_RE.search(text_value)
    if not match:
        return None
    amount, unit = match.groups()
    amount = float(amount)
    if unit == "m":
        return amount * 1_000_000
    if unit == "k":
        return amount * 1_000
    return amount


def parse_squad_page(html: str, team_name: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="items")
    if table is None:
        return []

    players = []
    for row in table.find_all("tr", class_=("odd", "even")):
        profile_link = row.select_one("td.posrela a[href*='/profil/spieler/']")
        if profile_link is None:
            continue
        tm_player_id = profile_link["href"].rstrip("/").rsplit("/", 1)[-1]
        name = profile_link.get_text(strip=True)

        position_cell = row.select_one("td.posrela table.inline-table tr:nth-of-type(2) td")
        position = position_cell.get_text(strip=True) if position_cell else None

        all_tds = row.find_all("td", recursive=False)
        # estructura de columnas: [rueckennummer, posrela, age, nationality, team, market_value]
        age = None
        if len(all_tds) >= 3:
            age_text = all_tds[2].get_text(strip=True)
            age = int(age_text) if age_text.isdigit() else None

        nationality = None
        if len(all_tds) >= 4:
            flag = all_tds[3].find("img")
            nationality = flag["title"] if flag and flag.has_attr("title") else None

        market_value_cell = row.select_one("td.rechts.hauptlink")
        market_value_eur = _parse_market_value(market_value_cell.get_text()) if market_value_cell else None

        players.append(
            {
                "tm_player_id": tm_player_id,
                "name": name,
                "team": team_name,
                "position": position,
                "age": age,
                "nationality": nationality,
                "market_value_eur": market_value_eur,
            }
        )
    return players


def load_squad(raw_page_id: int, players: list[dict], valued_at: str) -> int:
    if not players:
        return 0

    rows = [
        {
            "raw_page_id": raw_page_id,
            "tm_player_id": p["tm_player_id"],
            "name": p["name"],
            "team": p["team"],
            "birth_date": None,
            "age": p["age"],
            "nationality": p["nationality"],
            "position": p["position"],
            "height_cm": None,
            "market_value_eur": p["market_value_eur"],
            "valued_at": valued_at,
        }
        for p in players
    ]

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO staging.transfermarkt_players (
                    raw_page_id, tm_player_id, name, team, birth_date, age, nationality, position,
                    height_cm, market_value_eur, valued_at
                ) VALUES (
                    :raw_page_id, :tm_player_id, :name, :team, :birth_date, :age, :nationality, :position,
                    :height_cm, :market_value_eur, :valued_at
                )
                ON CONFLICT (tm_player_id, valued_at) DO UPDATE SET
                    raw_page_id = EXCLUDED.raw_page_id,
                    name = EXCLUDED.name,
                    team = EXCLUDED.team,
                    age = EXCLUDED.age,
                    nationality = EXCLUDED.nationality,
                    position = EXCLUDED.position,
                    market_value_eur = EXCLUDED.market_value_eur
                """
            ),
            rows,
        )
    return len(rows)
