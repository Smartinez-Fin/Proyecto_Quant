# Monitor de Probabilidad de Default — Merton/KMV

Proyecto de portafolio orientado a roles de crédito y riesgo (bancos y fondos).
Estima la distancia al default (DD) y la probabilidad de default (PD) de empresas
del S&P 500 con el modelo estructural de Merton/KMV, y la compara con ratings
crediticios y eventos de estrés.

Pregunta central: ¿puede el mercado accionario anticipar el deterioro crediticio
antes que las agencias de calificación? La especificación completa del método
está en README.md (fuente de verdad metodológica).

## Decisiones metodológicas
- Horizonte T = 1 año; tasa libre de riesgo = T-Bill 1 año de FRED (serie `DGS1`,
  CSV público sin API key).
- Punto de default KMV: D = deuda de corto plazo + 0.5 × deuda de largo plazo.
- E = precio de cierre × acciones en circulación (acciones desde SEC XBRL).
- σ_V y V por iteración de Vassalou & Xing (2004): σ_V⁰ = σ_E·E/(E+D), resolver
  Merton día a día, recalcular σ_V con log-retornos de V, tolerancia 1e-4.
- μ = media anualizada de log-retornos de V. DD con μ; PD = N(−DD).
- Universo: 30 empresas no financieras del S&P 500 (sin bancos ni aseguradoras),
  ratings variados, algunas con episodios de estrés. Periodo: últimos 5 años.
- La PD se interpreta sobre todo como medida ordinal (ranking de riesgo).

## Stack
- Python 3.11+ (entorno local: `.venv`)
- pandas, numpy, scipy
- yfinance (precios de cierre diarios), FRED (tasa libre de riesgo)
- API XBRL de la SEC (`data.sec.gov`) para balances (deuda, pasivos)
- plotly (gráficos), Streamlit (dashboard)
- pytest (tests)

## Estructura
```
src/
  data.py       # descarga y limpieza: precios (yfinance) y balances (SEC XBRL)
  merton.py     # modelo Merton/KMV: valor y volatilidad de activos, DD, PD
  analysis.py   # comparación vs ratings, eventos de estrés, métricas
notebooks/      # exploración y validación
app/            # dashboard Streamlit
tests/          # pytest
data/           # datos crudos y procesados — NO se sube a git
```

## Reglas
- **Sin look-ahead bias**: un balance solo se usa a partir de su fecha de
  publicación (`filed` en la SEC), nunca desde la fecha de cierre del periodo.
- Funciones pequeñas, con docstrings y type hints.
- Las peticiones a la SEC llevan un `User-Agent` con nombre y correo
  (leído de variable de entorno `SEC_USER_AGENT`, nunca hardcodeado en el repo)
  y respetan el límite de 10 peticiones/segundo.
- Antes de implementar cada fase, explicar en español el método.
- Al terminar cada fase: correr los tests, resumir resultados y proponer el commit.

## Fases
0. Estructura del proyecto, entorno virtual y git.
1. Descarga de datos de 30 empresas del S&P 500 con distintos ratings.
2. Modelo Merton/KMV con tests.
3. Análisis vs ratings y eventos de estrés.
4. Dashboard Streamlit y README final.

## Comandos
- Activar entorno: `.\.venv\Scripts\Activate.ps1`
- Instalar dependencias: `pip install -r requirements.txt`
- Tests: `pytest`
- Descargar datos: `python -m src.data`
- Dashboard: `streamlit run app/streamlit_app.py`
