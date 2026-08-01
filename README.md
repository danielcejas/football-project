# Football Analytics — La Liga

Plataforma de analítica de fútbol: scraping de Understat + Transfermarkt, ETL en capas
sobre Postgres (`raw` → `staging` → `core` → `marts`), analítica (rankings Elo, similitud
de jugadores/equipos, valoración estilo Moneyball, forma reciente, jóvenes promesas) y un
dashboard en Streamlit.

## Stack

- **Fuentes de datos**: Understat (xG/xA/tiros/pases clave) y Transfermarkt (valor de
  mercado, edad, posición). FBref se evaluó y se descartó — bloqueado por Cloudflare.
- **Base de datos**: Postgres (Docker Compose).
- **Orquestación**: Prefect.
- **Frontend**: Streamlit + Altair.

## Setup

```bash
cp .env.example .env      # ajustar credenciales si hace falta
docker compose up -d      # levanta Postgres
pip install -r requirements.txt
python -m src.db.apply_schema
```

## Cargar datos y calcular analítica (una temporada/competición)

```bash
python -m src.flows.daily_pipeline
```

O paso a paso, ver `src/scraping/`, `src/etl/build_core.py` y `src/analytics/compute_*.py`.

## Dashboard

```bash
streamlit run app/streamlit_app.py
```

## Tests

```bash
pytest
```

## Flujo de trabajo

- `main`: rama estable.
- `dev`: integración de desarrollo.
- Cada tarea sale de `dev` como `feature/<issue>-<slug>` y se mergea vía Pull Request
  (referenciando el issue con `Closes #<n>`).
