# Investigación — Fase 1: Descarga y preparación de datos

**Fecha**: 2026-11-28
**Método**: sondeos de solo lectura contra las APIs reales, ejecutados desde el
entorno del proyecto. Los scripts de sondeo se escribieron fuera del repositorio
y no forman parte del código.

---

## D-01 — El campo `filed` existe y la fecha de publicación es utilizable

**Decisión**: usar el endpoint `companyconcept` de la API XBRL de la SEC, que
devuelve cada hecho con su fecha de publicación.

**Verificado**: cada hecho trae exactamente estas claves:

```
['accn', 'end', 'filed', 'form', 'fp', 'frame', 'fy', 'val']
```

- `end`: fecha a la que se refiere el dato (cierre de periodo, o fecha de
  portada en el caso de las acciones en circulación).
- `filed`: fecha en que se publicó ante la SEC. **Es el campo que sostiene el
  principio I de la constitución.**
- `accn`: número de expediente, útil para distinguir reexpresiones.
- `form`: `10-K` o `10-Q`.
- `frame` aparece solo en algunos hechos (los que encajan en un trimestre
  calendario estándar); **no se puede asumir presente**.

**Consecuencia**: FR-003 y FR-004 son implementables tal como están escritos, sin
aproximaciones.

---

## D-02 — Etiquetas XBRL de deuda y acciones

**Decisión**: cadena de etiquetas con prioridad declarada, registrando siempre
cuál se usó.

| Concepto | Etiqueta primaria | Respaldos |
|---|---|---|
| Deuda de corto plazo | `us-gaap:DebtCurrent` | `us-gaap:LongTermDebtCurrent`, luego la suma de `ShortTermBorrowings` y `CommercialPaper` |
| Deuda de largo plazo | `us-gaap:LongTermDebtNoncurrent` | `us-gaap:LongTermDebt` menos la parte corriente |
| Acciones en circulación | `dei:EntityCommonStockSharesOutstanding` | `us-gaap:CommonStockSharesOutstanding` |

**Verificado con NVIDIA** (CIK 0001045810):

| Etiqueta | Resultado |
|---|---|
| `LongTermDebtNoncurrent` | ✅ 48 hechos, unidad USD |
| `LongTermDebtCurrent` | ✅ 40 hechos |
| `DebtCurrent` | ✅ 42 hechos |
| `LongTermDebt` | ✅ 98 hechos (es el total: 8.468 = 7.469 + 999 ✓) |
| `ShortTermBorrowings` | ❌ **404**: esta empresa no la reporta |
| `CommercialPaper` | ✅ 22 hechos, todos en cero |
| `dei:EntityCommonStockSharesOutstanding` | ✅ 69 hechos (el más frecuente) |
| `us-gaap:CommonStockSharesOutstanding` | ✅ 34 hechos |

**Rationale**: un 404 por etiqueta inexistente es normal y esperable, no un
fallo: cada empresa etiqueta lo que le aplica. Por eso la cadena de respaldos es
necesaria y por eso FR-011 exige registrar qué etiqueta se usó en cada caso, en
lugar de asumir una sola para las 30 empresas.

**Alternativa descartada**: el endpoint `companyfacts`, que trae todos los
conceptos de una empresa en una sola petición (30 peticiones en vez de 180).
Rechazado porque el archivo por empresa pesa decenas de megabytes, y el
proyecto vive dentro de OneDrive: 30 empresas serían cientos de megabytes
sincronizándose. Con `companyconcept` cada archivo pesa kilobytes.

---

## D-03 — El problema de las divisiones de acciones, confirmado con datos reales

**Decisión**: FR-024 es obligatorio, no una precaución teórica.

**Verificado**: acciones en circulación declaradas por NVIDIA alrededor de su
división 10:1 de junio de 2024.

| `end` | `filed` | Formulario | Acciones declaradas |
|---|---|---|---|
| 2024-02-16 | 2024-02-21 | 10-K | 2.500.000.000 |
| 2024-05-24 | 2024-05-29 | 10-Q | 2.460.000.000 |
| **2024-08-23** | **2024-08-28** | **10-Q** | **24.530.000.000** |
| 2024-11-15 | 2024-11-20 | 10-Q | 24.490.000.000 |

El conteo se multiplica por diez de un trimestre al siguiente. Los datos
históricos **no** se reexpresan retroactivamente: cada informe declara las
acciones vigentes en su momento. La serie de precios, en cambio, llega ya
expresada en la base posterior a la división.

**Consecuencia**: sin el ajuste del factor acumulado, el patrimonio de NVIDIA
saldría **diez veces subestimado** en todo el tramo anterior a junio de 2024, lo
que arrastraría el apalancamiento, `σ_V`, la DD y la PD de esa empresa.

**Detalle fino a respetar**: el conteo de acciones se refiere a `end` (fecha de
portada), mientras que la restricción de look-ahead se rige por `filed`. Son dos
fechas distintas para dos usos distintos:

- **Qué factor aplicar**: divisiones con fecha posterior a `end`.
- **Desde cuándo se puede usar el dato**: desde `filed`.

---

## D-04 — Reexpresiones: el mismo periodo publicado más de una vez

**Decisión**: para cada día `t`, de cada periodo `end` se toma el hecho con el
`filed` más reciente que sea anterior o igual a `t`; entre los periodos
disponibles se toma el de `end` más reciente.

**Verificado**: `CommonStockSharesOutstanding` de NVIDIA presenta el periodo
`end=2025-01-26` publicado dos veces, con `filed=2025-02-26` y con
`filed=2026-02-25` (la segunda vez como comparativo del informe siguiente).

**Rationale**: este algoritmo reproduce exactamente lo que se sabía en cada
fecha, que es lo que exigen FR-004, FR-005 y FR-006. Es además una función pura
sobre listas de hechos, así que se puede probar sin red.

---

## D-05 — Las dos series de precios en una sola descarga

**Decisión**: llamar a yfinance con `auto_adjust=False` de forma **explícita** y
fijar la versión en `requirements.txt`.

**Verificado por búsqueda**: las versiones recientes de yfinance aplican el
ajuste por defecto (`auto_adjust=True`) y, al hacerlo, **eliminan la columna
`Adj Close`**. Con `auto_adjust=False` se obtienen los precios tal como se
negociaron más la columna ajustada. Las fuentes discrepan sobre en qué versión
cambió el valor por defecto (0.2.51 o 0.2.54), lo que refuerza la conclusión:
el parámetro nunca debe dejarse implícito, porque el significado de `Close`
cambiaría en silencio al actualizar la librería.

**Consecuencia para FR-023**: el coste de tener las dos series es cero, una sola
petición las devuelve. `Close` alimenta el patrimonio; `Adj Close` alimenta la
volatilidad.

---

## D-06 — Mapa de identificadores

**Decisión**: resolver el CIK de cada empresa con
`https://www.sec.gov/files/company_tickers.json`, y guardar el CIK en el archivo
versionado del universo para no depender de que el mapa no cambie.

**Verificado**: 10.400 empresas, cada registro con las claves
`['cik_str', 'ticker', 'title']`; por ejemplo
`{'cik_str': 320193, 'ticker': 'AAPL', 'title': 'Apple Inc.'}`.

**Detalle**: `cik_str` llega como entero, pero la API exige el CIK con **ceros a
la izquierda hasta 10 dígitos** (`CIK0000320193`).

---

## D-07 — Límite de 10 peticiones por segundo

**Decisión**: limitador propio en el cliente de la SEC, con un objetivo de
**8 peticiones por segundo** para dejar margen, reintentos con espera creciente
ante errores 429 y 503, y fallo explícito tras agotar los reintentos.

**Dimensionamiento**: 30 empresas × 6 etiquetas = 180 peticiones ≈ **23 segundos**
a 8 por segundo. Muy por debajo del límite de 60 minutos de SC-006.

**Rationale**: el principio IV prohíbe el reemplazo silencioso de datos, así que
agotar los reintentos debe abortar con un mensaje claro, nunca continuar con un
hueco disimulado.

---

## D-08 — FRED es accesible desde la máquina del autor (resuelto)

**Estado**: **resuelto el 2026-11-28**. El autor comprobó que
`https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1` descarga el CSV con
normalidad desde su navegador. El fallo era una restricción del entorno de
desarrollo asistido, no de FRED. **La fuente se mantiene tal como la nombran los
principios II y III de la constitución y no hace falta ninguna enmienda.**

**Consecuencia práctica para la implementación**: la descarga real de la tasa no
se puede ejercitar desde el entorno asistido. El código y sus tests se escriben
y se validan sin red, como ya exige D-10, pero **la prueba de descarga efectiva
contra FRED la ejecuta el autor en su máquina** (escenario 6 de la guía de
validación). Es una limitación del entorno, no del diseño.

**Lo observado**: tres intentos contra `fred.stlouisfed.org` fallaron, con dos
endpoints distintos y con dos clientes HTTP distintos:

| Endpoint | Resultado |
|---|---|
| `/graph/fredgraph.csv?id=DGS1&cosd=...&coed=...` | `ReadTimeout` tras 30 s |
| `/graph/fredgraph.csv?id=DGS1` | `RemoteDisconnected` (con `urllib` y con `requests`, también con 60 s de espera) |
| `/data/DGS1.txt` | `ReadTimeout` tras 30 s |

La API de la SEC funcionó con normalidad en la misma sesión, así que no es un
corte de red general.

**Conclusión tras la verificación del autor**: FRED está operativo y accesible
desde la máquina donde se ejecuta el proyecto. Lo observado arriba era una
restricción de red del entorno asistido.

**Decisión**: FRED sigue siendo la fuente, conforme a los principios II y III de
la constitución. Se mantienen de todos modos las dos medidas siguientes, porque
cuestan poco y cubren un cambio futuro de la fuente:

1. La tasa libre de riesgo se descarga en **una sola función** de `src/tasas.py`.
   Cambiar de fuente afecta a esa función y a su test, a nada más.
2. La contingencia queda ya investigada abajo, de modo que si FRED falla no haya
   que empezar de cero.

### Contingencia ya verificada: curva diaria del Tesoro de EE. UU.

**No se va a usar**, porque FRED funciona. Queda documentada porque la
investigación ya está hecha y evitaría empezar de cero si FRED dejara de
publicar la serie o cambiara de formato. Adoptarla **requeriría enmendar la
constitución a la versión 1.1.0**, porque los principios II y III nombran FRED.

| | |
|---|---|
| URL | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/<AÑO>/all?type=daily_treasury_yield_curve&field_tdr_date_value=<AÑO>&page&_format=csv` |
| Respuesta verificada | HTTP 200, `text/csv; charset=UTF-8`, sin API key |
| Columna necesaria | `"1 Yr"` — es la misma serie de vencimiento constante a un año que publica `DGS1` |
| Peticiones | Una por año natural: 6 para la ventana 2021-2026 |
| Volumen | ~250 filas por año |
| Formato de fecha | `MM/DD/YYYY` |
| Unidades | Porcentaje (`4.61` significa 4,61 %), hay que dividir por 100 |
| Orden | Descendente, la fecha más reciente primero |

**Trampa detectada y relevante**: **las columnas cambian entre años**. El archivo
de 2026 incluye `"1.5 Month"` y `"4 Mo"`, que el de 2021 no tiene:

```
2026: Date,"1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr",...
2021: Date,"1 Mo","2 Mo","3 Mo","6 Mo","1 Yr","2 Yr",...
```

Cualquier lectura por posición de columna produciría datos incorrectos en
silencio. Hay que seleccionar **por nombre**.

**Nota de fondo**: `DGS1` es un dato que FRED **redistribuye**; el Tesoro es
quien lo produce. Ir al Tesoro no degradaría la calidad de la fuente.

---

## D-09 — Almacenamiento y reproducibilidad

**Decisión**: datos crudos tal como llegan de la fuente, datos procesados en
Parquet, informe de cobertura en CSV, y un manifiesto JSON por ejecución.

**Rationale**:

- **Parquet** (vía `pyarrow`, ya en `requirements.txt`) preserva los tipos y las
  fechas, que es lo que CSV pierde. Evita que una fecha vuelva como texto.
- **El informe de cobertura en CSV** porque está hecho para leerlo a ojo.
- **El manifiesto** registra la ventana usada, la fecha de ejecución, las
  versiones de las librerías y el número de filas de cada archivo. Es lo que
  convierte SC-002 en algo verificable y no en una declaración de intenciones.

**Alternativa descartada**: guardar todo en CSV. Rechazada porque obliga a
reconstruir los tipos en cada lectura, y porque un `NaN` y un cero se vuelven
indistinguibles con facilidad, lo que choca con FR-012.

---

## D-10 — Tests sin depender de la red

**Decisión**: inyección de dependencias en los tres módulos de descarga, más
fixtures recortados de respuestas reales.

- `sec.py`, `precios.py` y `tasas.py` reciben una función de descarga como
  parámetro opcional. En producción usa `requests`; en los tests recibe una
  función falsa que devuelve el fixture. No hace falta librería de simulación.
- Los módulos de transformación (`vigencia.py`, `splits.py`, `panel.py`,
  `cobertura.py`) son **funciones puras**: se prueban pasándoles listas y
  DataFrames construidos a mano, sin red ni archivos.
- Los fixtures se recortan de respuestas reales y se versionan en
  `tests/fixtures/`. Pesan kilobytes.
- Las pruebas que sí tocan la red se marcan con `@pytest.mark.red` y quedan
  **excluidas por defecto**, para que `pytest` siga pasando sin conexión.

**Rationale**: el principio V exige que los tests pasen antes de cada commit de
cierre de fase. Un test que depende de la red falla por motivos ajenos al
código, y un test que falla por motivos ajenos al código se acaba ignorando.
