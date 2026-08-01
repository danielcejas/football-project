"""Aplica todos los .sql de src/db/schema/ en orden alfabético."""

from pathlib import Path

from sqlalchemy import text

from src.db.connection import get_engine

SCHEMA_DIR = Path(__file__).parent / "schema"


def apply_schema() -> None:
    engine = get_engine()
    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))
    with engine.begin() as conn:
        for sql_file in sql_files:
            print(f"Applying {sql_file.name}")
            conn.execute(text(sql_file.read_text()))


if __name__ == "__main__":
    apply_schema()
