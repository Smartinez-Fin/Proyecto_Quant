# Monitor de Probabilidad de Default — Modelo Merton / KMV

> Sistema de alerta temprana de riesgo de crédito que usa información del mercado accionario para estimar, día a día, la probabilidad de que una empresa no pueda pagar su deuda.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red) ![Estado](https://img.shields.io/badge/estado-en%20desarrollo-yellow)

---

## Tabla de contenido

1. [Resumen](#resumen)
2. [El problema](#el-problema)
3. [Intuición del modelo](#intuición-del-modelo)
4. [Metodología](#metodología)
5. [Datos](#datos)
6. [Estructura del repositorio](#estructura-del-repositorio)
7. [Instalación y uso](#instalación-y-uso)
8. [Resultados](#resultados)
9. [Limitaciones](#limitaciones)
10. [Próximos pasos](#próximos-pasos)
11. [Referencias](#referencias)

---

## Resumen

Este proyecto implementa el modelo estructural de crédito de **Merton (1974)** con los ajustes prácticos de **KMV (Moody's)** para calcular la **distancia al default (DD)** y la **probabilidad de default (PD)** de 30 empresas del S&P 500 con distintas calificaciones crediticias.

**Qué hace:**

- Descarga precios diarios de mercado y datos de deuda desde la SEC.
- Estima el valor y la volatilidad de los activos de cada empresa (variables no observables).
- Calcula DD y PD diarias.
- Valida el modelo comparándolo con ratings de agencias y con eventos reales de estrés.
- Presenta los resultados en un dashboard interactivo.

**Pregunta central:** *¿Puede el mercado de acciones anticipar el deterioro crediticio de una empresa antes que las agencias de calificación?*

---

## El problema

Las instituciones que prestan dinero o invierten en deuda corporativa (bancos, fondos de crédito, gestoras de activos) necesitan detectar a tiempo qué empresas se están deteriorando. Las fuentes tradicionales tienen limitaciones:

| Fuente | Frecuencia | Problema |
|---|---|---|
| Ratings de agencias (S&P, Moody's, Fitch) | Pocas revisiones al año | Reaccionan tarde |
| Estados financieros | Trimestral | Miran hacia atrás |
| **Precio de la acción** | **Diaria** | **Incorpora expectativas del mercado en tiempo real** |

El modelo de Merton traduce la información del mercado accionario en una medida de riesgo de crédito, con lo que se obtiene una señal **diaria y prospectiva**.

---

## Intuición del modelo

La idea clave de Merton: **el patrimonio (equity) de una empresa es una opción call sobre sus activos.**

- La empresa tiene activos con valor $V$ y una deuda $D$ que vence en $T$.
- Al vencimiento:
  - Si $V > D$ → los accionistas pagan la deuda y se quedan con $V - D$.
  - Si $V < D$ → la empresa entra en **default**: los acreedores se quedan con los activos y los accionistas reciben 0.

El pago para el accionista es $\max(V_T - D,\ 0)$, idéntico al de una **opción call europea** con precio de ejercicio $D$. Por eso se puede aplicar la fórmula de **Black-Scholes** para relacionar lo que observamos (valor y volatilidad del equity) con lo que no observamos (valor y volatilidad de los activos).

---

## Metodología

### 1. Ecuaciones de Merton

Valor del equity como call sobre los activos:

$$E = V\,N(d_1) - D\,e^{-rT}\,N(d_2)$$

$$d_1 = \frac{\ln(V/D) + (r + \tfrac{1}{2}\sigma_V^2)\,T}{\sigma_V\sqrt{T}}, \qquad d_2 = d_1 - \sigma_V\sqrt{T}$$

Donde:

| Símbolo | Significado | ¿Observable? |
|---|---|---|
| $E$ | Valor de mercado del equity (precio × acciones en circulación) | ✅ |
| $\sigma_E$ | Volatilidad del equity | ✅ |
| $D$ | Punto de default (deuda) | ✅ (balance) |
| $r$ | Tasa libre de riesgo | ✅ |
| $T$ | Horizonte (1 año) | ✅ |
| $V$ | Valor de mercado de los activos | ❌ — se estima |
| $\sigma_V$ | Volatilidad de los activos | ❌ — se estima |

### 2. Ajustes KMV

- **Punto de default:** $D = \text{Deuda de corto plazo} + 0.5 \times \text{Deuda de largo plazo}$.
  En la práctica las empresas entran en default antes de que los activos caigan por debajo del total de la deuda.
- **Estimación iterativa de $\sigma_V$** (Vassalou & Xing, 2004):
  1. Valor inicial: $\sigma_V^{(0)} = \sigma_E \cdot \dfrac{E}{E + D}$.
  2. Para cada día $t$, resolver numéricamente la ecuación de Merton para obtener $V_t$ dado $E_t$ y $\sigma_V^{(k)}$.
  3. Calcular $\sigma_V^{(k+1)}$ como la desviación estándar anualizada de los retornos logarítmicos de $V_t$.
  4. Repetir hasta que $|\sigma_V^{(k+1)} - \sigma_V^{(k)}| < 10^{-4}$.
  5. El drift $\mu$ se estima como la media anualizada de los retornos logarítmicos de $V_t$.

### 3. Distancia al default y probabilidad de default

$$DD = \frac{\ln(V/D) + (\mu - \tfrac{1}{2}\sigma_V^2)\,T}{\sigma_V\sqrt{T}}$$

$$PD = N(-DD)$$

**Interpretación:** la DD mide cuántas desviaciones estándar les faltan a los activos para caer por debajo del punto de default. Una DD alta indica una empresa segura; una DD cercana a 0, una empresa en zona de peligro.

**Ejemplo:** $V = 100$, $D = 80$, $\sigma_V = 20\%$, $\mu \approx 0$ → $DD \approx 1.0$, es decir, una PD de alrededor del 15% a un año.

### 4. Control de *look-ahead bias*

Los datos de deuda de cada trimestre se usan **solo a partir de su fecha de publicación en la SEC** (*filed date*), no desde la fecha de cierre del periodo. Así se replica la información que realmente estaba disponible en cada momento.

### 5. Validación

- **Ordenamiento por rating:** ¿las empresas con peor calificación tienen menor DD?
- **Estudios de evento:** evolución de la PD en los meses previos a eventos reales de estrés crediticio.
- **Señal anticipada:** ¿la PD aumentó antes de las rebajas de calificación?

---

## Datos

| Dato | Fuente | Frecuencia |
|---|---|---|
| Precios de cierre | `yfinance` | Diaria |
| Acciones en circulación | SEC XBRL API (`data.sec.gov`) | Trimestral |
| Deuda de corto y largo plazo | SEC XBRL API (`data.sec.gov`) | Trimestral |
| Tasa libre de riesgo (T-Bill 1 año) | FRED | Diaria |
| Ratings crediticios | Recopilación manual de fuentes públicas | Puntual |

**Universo:** 30 empresas del S&P 500 con distintos ratings, incluidas algunas que han pasado por episodios de estrés crediticio. Se excluyen bancos y aseguradoras (ver [Limitaciones](#limitaciones)).

**Periodo:** últimos 5 años.

---

## Estructura del repositorio

```
merton-default-monitor/
├── README.md
├── CLAUDE.md               # Instrucciones de desarrollo
├── requirements.txt
├── .gitignore
├── src/
│   ├── data.py             # Descarga y limpieza de datos
│   ├── merton.py           # Modelo Merton/KMV: V, σ_V, DD, PD
│   └── analysis.py         # Validación y métricas
├── notebooks/
│   └── analisis.ipynb      # Exploración y gráficos
├── app/
│   └── streamlit_app.py    # Dashboard interactivo
├── tests/
│   └── test_merton.py      # Pruebas unitarias del modelo
└── data/                   # Datos descargados (no versionados)
```

---

## Instalación y uso

```bash
# 1. Clonar el repositorio
git clone https://github.com/Smartinez-Fin/merton-default-monitor.git
cd merton-default-monitor

# 2. Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows (PowerShell)
# source .venv/bin/activate   # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar el User-Agent para la SEC (nombre y correo)
copy .env.example .env        # Windows; luego edita SEC_USER_AGENT

# 5. Descargar datos
python -m src.data

# 6. Correr pruebas
pytest

# 7. Lanzar el dashboard
streamlit run app/streamlit_app.py
```

---

## Resultados

> 🚧 *Sección en construcción. Se completará al finalizar la fase de análisis.*

### Distancia al default por rating
<!-- Insertar gráfico: boxplot de DD por categoría de rating -->

### Estudio de evento: evolución de la PD antes de un evento de estrés
<!-- Insertar gráfico: serie temporal de PD con la fecha del evento marcada -->

### Principales hallazgos
- *Hallazgo 1 (pendiente)*
- *Hallazgo 2 (pendiente)*
- *Hallazgo 3 (pendiente)*

### Dashboard
<!-- Insertar captura del dashboard de Streamlit -->

---

## Limitaciones

- **Supuesto de lognormalidad:** el modelo supone que el valor de los activos sigue un movimiento browniano geométrico, sin saltos. Por eso tiende a **subestimar la PD de corto plazo**.
- **Estructura de deuda simplificada:** toda la deuda se resume en un único punto de default con un solo vencimiento.
- **No aplica a instituciones financieras:** en bancos y aseguradoras la deuda es parte del negocio operativo, lo que distorsiona el modelo.
- **Solo empresas cotizadas:** requiere precio de mercado del equity.
- **PD como medida ordinal:** la PD depende del supuesto sobre $\mu$; es más confiable para **ordenar** empresas por riesgo que como probabilidad absoluta.
- **Datos públicos:** la calidad de los datos XBRL varía entre empresas y periodos.

---

## Hoja de ruta

- [x] Fase 0 — estructura del proyecto, entorno virtual y git
- [ ] Fase 1 — descarga de datos (30 empresas, distintos ratings)
- [ ] Fase 2 — modelo Merton/KMV con tests
- [ ] Fase 3 — análisis vs ratings y eventos de estrés
- [ ] Fase 4 — dashboard Streamlit y README final

## Próximos pasos

- [ ] Comparar la DD con *spreads* de bonos o CDS.
- [ ] Implementar la versión simplificada "naïve" de Bharath & Shumway (2008) y comparar ambas.
- [ ] Ampliar el universo a empresas *high yield*.
- [ ] Agregar alertas automáticas cuando la PD supere un umbral.

---

## Referencias

- Merton, R. C. (1974). *On the Pricing of Corporate Debt: The Risk Structure of Interest Rates*. Journal of Finance, 29(2), 449–470.
- Crosbie, P., & Bohn, J. (2003). *Modeling Default Risk*. Moody's KMV.
- Vassalou, M., & Xing, Y. (2004). *Default Risk in Equity Returns*. Journal of Finance, 59(2), 831–868.
- Bharath, S. T., & Shumway, T. (2008). *Forecasting Default with the Merton Distance to Default Model*. Review of Financial Studies, 21(3), 1339–1369.

---

## Autor

**Santiago** — Estudiante de ciencia de datos con enfoque en finanzas cuantitativas.

[GitHub](https://github.com/Smartinez-Fin) · [LinkedIn](https://linkedin.com/in/<tu-perfil>)
