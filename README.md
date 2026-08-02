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

## Valoración Moneyball

`src/analytics/valuation.py` + `src/analytics/compute_valuation.py` calculan, por
temporada, un valor de mercado "predicho por rendimiento" para cada jugador y lo comparan
con su valor de mercado real de Transfermarkt.

**Datos de entrada**: solo delanteros y centrocampistas con ≥ 450 minutos esa temporada.
Understat no da métricas defensivas (entradas, intercepciones, despejes, paradas), así
que incluir defensas/porteros con estas columnas no los valoraría de verdad, solo
mediría cuánto "ruido" tienen — ver más abajo por qué esto no tiene un arreglo fácil.

**Modelo**: una regresión Ridge (regularizada, porque con ~200-400 jugadores y variables
muy correlacionadas entre sí — goles/xG/npxG casi miden lo mismo — una regresión sin
regularizar da coeficientes inestables) sobre:

```
log(valor_de_mercado) ~ goles/90 + asistencias/90 + xG/90 + xA/90 + npxG/90
                         + pases_clave/90 + edad + posición
```

Todas las variables se estandarizan antes de ajustar. Es un ajuste **dentro de la propia
muestra** (in-sample) — no se evalúa contra jugadores nuevos, porque lo que se busca es
"¿quién rinde más de lo que cuesta *dentro de esta liga y temporada*?", no predecir el
valor de un jugador fuera de la muestra.

**De log(valor) a euros**: la predicción del modelo está en escala logarítmica.
`exp(predicción)` a secas subestima sistemáticamente (matemáticamente estima la mediana,
no la media, de una distribución tan sesgada a la derecha como los valores de mercado),
así que se corrige con el **estimador de suavizado de Duan**: se multiplica por un factor
calculado a partir de los propios residuos del ajuste (`media(exp(residuo))`).

**Resultado**: `predicted_value_eur` (lo que "debería" valer según su rendimiento),
`value_gap_eur`/`value_gap_pct` (`predicted - real`, positivo = posible ganga, negativo =
el mercado paga más de lo que el rendimiento sugiere).

**Qué NO ve el modelo**: reputación, trofeos, potencial futuro, marketing. Por eso las
superestrellas consagradas (Mbappé, Vinícius Júnior, Pedri...) salen sistemáticamente con
gap negativo grande y consistente entre temporadas — es la prima de reputación que el
mercado paga y que un modelo que solo mira producción de la temporada no puede explicar.
No es un error del modelo, es la lectura Moneyball esperada para ese perfil de jugador.

**Por qué no hay (todavía) una versión para defensas/porteros**: no es cuestión de
ajustar el modelo, es que Understat simplemente no expone ninguna métrica defensiva ni
de portero (nada de entradas, intercepciones, despejes, duelos aéreos, paradas, PSxG...).
Cualquier intento de valorarlos con las columnas actuales mediría solo ruido. Haría falta
una fuente de datos nueva con estadísticas defensivas/de portero por partido (candidatas:
FBref — bloqueado por Cloudflare, ver más arriba — u otra fuente equivalente) antes de
poder construir una valoración Moneyball real para esas posiciones.

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
