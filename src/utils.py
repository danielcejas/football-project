import pandas as pd
import numpy as np
import matplotlib.pyplot as plt



class AnalisisUnivariante:
    """Análisis univariante automático de un DataFrame.

    Recorre cada columna y, según su tipo, hace el análisis apropiado:
    - Numéricas: estadísticos, nulos, ceros, outliers (IQR), histograma + densidad + boxplot.
    - Categóricas: nulos, cardinalidad, frecuencias, gráfico de barras.
    - Alta cardinalidad (IDs, nombres, URLs): solo resumen, sin gráfico.
    - Fechas: rango temporal y distribución por año.

    Uso:
        an = AnalisisUnivariante(df, ignorar=["Url", "MatchURL"])
        an.resumen()              # tabla global de todas las columnas
        an.analizar_todo()        # análisis detallado columna a columna
        an.analizar_columna("xG") # una columna concreta
    """

    def __init__(self, df, max_categorias=20, ignorar=None):
        self.df = df
        self.max_categorias = max_categorias   # tope para tratar como categórica "graficable"
        self.ignorar = set(ignorar or [])

    # ------------------------------------------------ clasificación de tipo

    def _tipo(self, col):
        s = self.df[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            return "fecha"
        if pd.api.types.is_numeric_dtype(s):
            # numérica con poquísimos valores distintos = categórica encubierta (ej. CrdR: 0/1/2)
            if s.nunique(dropna=True) <= 10:
                return "categorica"
            return "numerica"
        if s.nunique(dropna=True) > self.max_categorias:
            return "alta_cardinalidad"
        return "categorica"

    # ------------------------------------------------ análisis por tipo

    def _analizar_numerica(self, col):
        s = self.df[col].dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outliers = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()

        print(f"  nulos: {self.df[col].isna().sum()} ({self.df[col].isna().mean()*100:.1f}%)")
        print(f"  media={s.mean():.3f}  mediana={s.median():.3f}  std={s.std():.3f}")
        print(f"  min={s.min():.3f}  q1={q1:.3f}  q3={q3:.3f}  max={s.max():.3f}")
        print(f"  asimetría (skew): {s.skew():.2f}  |  ceros: {(s == 0).sum()} ({(s == 0).mean()*100:.1f}%)")
        print(f"  outliers (regla 1.5·IQR): {outliers} ({outliers/len(s)*100:.1f}%)")

        fig, axes = plt.subplots(1, 2, figsize=(11, 2.8))
        s.hist(bins=40, ax=axes[0], density=True, alpha=0.6)
        try:
            s.plot(kind="kde", ax=axes[0], color="crimson")
        except Exception:
            pass  # KDE falla si la varianza es 0
        axes[0].set_title(f"{col} — distribución y densidad", fontsize=9)
        axes[1].boxplot(s, vert=False)
        axes[1].set_title("boxplot", fontsize=9)
        plt.tight_layout(); plt.show()

    def _analizar_categorica(self, col):
        s = self.df[col]
        frec = s.value_counts(dropna=False)
        print(f"  nulos: {s.isna().sum()} ({s.isna().mean()*100:.1f}%)")
        print(f"  categorías: {s.nunique(dropna=True)}")
        print("  frecuencias:")
        for val, n in frec.head(self.max_categorias).items():
            print(f"    {val}: {n} ({n/len(s)*100:.1f}%)")

        frec.head(self.max_categorias).plot(kind="barh", figsize=(8, max(1.5, 0.3*min(len(frec), self.max_categorias))))
        plt.title(f"{col} — frecuencias", fontsize=9)
        plt.gca().invert_yaxis()
        plt.tight_layout(); plt.show()

    def _analizar_alta_cardinalidad(self, col):
        s = self.df[col]
        print(f"  nulos: {s.isna().sum()} ({s.isna().mean()*100:.1f}%)")
        print(f"  valores únicos: {s.nunique(dropna=True)} (probable ID/nombre — sin gráfico)")
        print(f"  ejemplos: {s.dropna().unique()[:5].tolist()}")

    def _analizar_fecha(self, col):
        s = self.df[col].dropna()
        print(f"  nulos: {self.df[col].isna().sum()}")
        print(f"  rango: {s.min()} → {s.max()}")
        s.dt.year.value_counts().sort_index().plot(kind="bar", figsize=(8, 2.5))
        plt.title(f"{col} — filas por año", fontsize=9)
        plt.tight_layout(); plt.show()

    # ------------------------------------------------ API pública

    def analizar_columna(self, col):
        tipo = self._tipo(col)
        print("=" * 80)
        print(f"### {col}  [{tipo}]  (dtype: {self.df[col].dtype})")
        print("=" * 80)
        getattr(self, f"_analizar_{tipo}")(col)
        print()

    def analizar_todo(self):
        for col in self.df.columns:
            if col in self.ignorar:
                continue
            self.analizar_columna(col)

    def resumen(self):
        """Tabla global: una fila por columna con tipo, nulos y cardinalidad."""
        filas = []
        for col in self.df.columns:
            s = self.df[col]
            filas.append({
                "columna": col,
                "tipo_detectado": self._tipo(col),
                "dtype": str(s.dtype),
                "n_nulos": s.isna().sum(),
                "pct_nulos": round(s.isna().mean() * 100, 1),
                "n_unicos": s.nunique(dropna=True),
            })
        return pd.DataFrame(filas).sort_values("pct_nulos", ascending=False).reset_index(drop=True)
    



POS_NOMBRE = {
    "GK": "Goalkeeper",
    "DF": "Defender",
    "MF": "Midfielder",
    "FW": "Forward",
}


def parsear_posiciones(serie_pos):
    """Parsea la columna Pos de FBref ('MF,FW') a tres columnas legibles.

    Devuelve un DataFrame con:
      - Position_main: posicion principal ('Midfielder')      -> para logica/filtros
      - Position_sec:  posicion secundaria ('Forward' o NA)   -> versatilidad
      - Position:      version para mostrar ('Midfielder / Forward')
    """
    def _parse(pos):
        if pd.isna(pos):
            return pd.NA, pd.NA, pd.NA
        tokens = [t.strip() for t in str(pos).split(",")]
        nombres = [POS_NOMBRE.get(t, t) for t in tokens]
        principal = nombres[0]
        secundaria = nombres[1] if len(nombres) > 1 else pd.NA
        return principal, secundaria, " / ".join(nombres)

    parsed = serie_pos.map(_parse)
    out = pd.DataFrame({
        "Position_main": parsed.str[0],
        "Position_sec": parsed.str[1],
        "Position": parsed.str[2],
    }, index=serie_pos.index)

    raros = out.loc[out["Position_main"].notna() &
                    ~out["Position_main"].isin(POS_NOMBRE.values()), "Position_main"].unique()
    assert len(raros) == 0, f"posiciones sin mapear en POS_NOMBRE: {raros}"
    return out


def corregir_por_jugador(df, columna, fixes, solo_nulos=True):
    """Aplica correcciones manuales verificadas: dict {Player: valor} sobre <columna>.

    solo_nulos=True (por defecto) solo rellena huecos, nunca sobreescribe
    valores existentes. Devuelve el numero de filas corregidas.
    """
    mask = df["Player"].isin(fixes)
    if solo_nulos:
        mask &= df[columna].isna()
    df.loc[mask, columna] = df.loc[mask, "Player"].map(fixes)
    return int(mask.sum())


def imputar_por_ritmo(df, jugador, temporada, cols,
                      col_min="Min_Playing", col_n90="Mins_Per_90_Playing",
                      min_minutos_ref=400):
    """Imputa <cols> (acumulados) de una temporada rota de un jugador como:
    (ritmo per-90 medio de sus otras temporadas con >= min_minutos_ref) x (noventas de la temporada).

    Estimacion con sesgo conocido: asume que su ritmo fue como el de sus otras
    temporadas. Documentar siempre su uso. No hace nada (y avisa) si no hay
    temporadas de referencia.
    """
    m_target = (df["Player"] == jugador) & (df["Season_End_Year"] == temporada)
    if not m_target.any():
        print(f"[imputar_por_ritmo] no existe {jugador} {temporada}")
        return
    m_ref = ((df["Player"] == jugador) & ~m_target &
             (df[col_min] >= min_minutos_ref) &
             df[cols].notna().all(axis=1))
    if not m_ref.any():
        print(f"[imputar_por_ritmo] sin temporadas de referencia para {jugador}")
        return
    ref = df[m_ref]
    ratios = ref[cols].div(ref[col_n90], axis=0).mean()
    n90 = df.loc[m_target, col_n90].iloc[0]
    valores = (ratios * n90).round(1)
    df.loc[m_target, cols] = valores.values
    print(f"[imputar_por_ritmo] {jugador} {temporada}: {dict(valores)} "
          f"(ref: {int(m_ref.sum())} temporadas, {n90:.1f} noventas)")


def imputar_ceros_marginales(df, cols, col_min="Min_Playing", umbral_min=200):
    """Imputa 0 en <cols> SOLO para filas con menos de <umbral_min> minutos.

    Guardian: si queda algun nulo en filas con minutos relevantes, lanza
    AssertionError en vez de imputar ceros falsos por descuido.
    """
    mask = df[cols].isna().any(axis=1)
    relevantes = df.loc[mask & (df[col_min] >= umbral_min)]
    assert relevantes.empty, (
        f"filas con minutos relevantes y nulos en {cols}:\n"
        f"{relevantes[['Player', 'Season_End_Year', col_min]].to_string()}"
    )
    df[cols] = df[cols].fillna(0)
    return int(mask.sum())


def convertir_numericas_disfrazadas(df, excluir=()):
    """Convierte a numerico las columnas object donde >70% de los valores lo son."""
    convertidas = []
    for c in df.columns:
        if df[c].dtype == object and c not in excluir:
            conv = pd.to_numeric(df[c], errors="coerce")
            no_nulos = df[c].notna().sum()
            if no_nulos and conv.notna().sum() / no_nulos > 0.7:
                df[c] = conv
                convertidas.append(c)
    return convertidas