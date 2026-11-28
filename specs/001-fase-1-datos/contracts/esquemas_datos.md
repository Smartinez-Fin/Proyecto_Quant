# Contrato — Esquemas de archivos

Esquema exacto de cada archivo que la fase 1 lee o escribe. Es el contrato entre
esta fase y la fase 2, y entre el código y el trabajo manual de recopilación.

**Convenciones**

- Codificación **UTF-8** en todos los CSV. Los nombres de empresa llevan
  acentos y símbolos.
- Separador de CSV: **coma**. Los campos de texto con comas van entre comillas.
- Fechas en **ISO** (`AAAA-MM-DD`) en todos los archivos del proyecto, aunque la
  fuente las entregue en otro formato.
- Los decimales usan **punto**, nunca coma.
- Parquet escrito con `pyarrow`, compresión por defecto.

---

## Entrada versionada: `datos_entrada/universo.csv`

| Columna | Tipo | Obligatoria | Nota |
|---|---|---|---|
| `ticker` | string | sí | Mayúsculas |
| `cik` | string | sí | 10 dígitos, ceros a la izquierda; se guarda como **texto** para no perderlos |
| `nombre` | string | sí | |
| `sector` | string | sí | |
| `grupo` | string | sí | `base` \| `estres` |
| `categoria_rating` | string | sí | `AA+` \| `A` \| `BBB` \| `BB` \| `B-` |
| `motivo` | string | solo si `grupo = estres` | |

Clave: `ticker`. Exactamente 30 filas.

> `cik` **debe** leerse como texto. Si se lee como entero, `0000320193` se
> convierte en `320193` y todas las llamadas a la API fallan.

---

## Entrada versionada: `datos_entrada/ratings.csv`

| Columna | Tipo | Obligatoria | Nota |
|---|---|---|---|
| `ticker` | string | sí | |
| `agencia` | string | sí | `S&P` \| `Moody's` \| `Fitch` |
| `calificacion` | string | sí | Tal como la publica la agencia |
| `escalon` | int | sí | Escala normalizada: 1 = AAA, descendente |
| `fecha` | date | sí | |
| `tipo` | string | sí | `vigente` \| `rebaja` \| `mejora` \| `sin_cambios` |
| `fuente_nivel` | string | sí | `agencia` \| `prensa` \| `regulador` |
| `fuente_url` | string | sí | Enlace a la nota concreta |
| `fecha_consulta` | date | sí | |

Clave: `(ticker, agencia, fecha, tipo)`.

**La escala normalizada es necesaria** porque Moody's usa `Baa1` donde S&P usa
`BBB+`. Sin un entero común no se puede medir "dos escalones" ni repartir el
grupo base por tramo.

---

## Entrada versionada: `datos_entrada/eventos_estres.csv`

| Columna | Tipo | Obligatoria |
|---|---|---|
| `ticker` | string | sí |
| `fecha` | date | sí |
| `descripcion` | string | sí |
| `fuente_url` | string | sí |
| `fecha_consulta` | date | sí |

Clave: `(ticker, fecha)`.

---

## Crudo: `data/crudo/`

| Ruta | Formato | Contenido |
|---|---|---|
| `sec/<CIK>_<etiqueta>.json` | JSON | Respuesta literal de `companyconcept`, sin tocar |
| `precios/<TICKER>.parquet` | Parquet | Lo que devolvió yfinance, sin tocar |
| `tasas/tasa.csv` | CSV | Lo que devolvió la fuente, sin tocar |

**Se guarda sin transformar a propósito.** Permite reprocesar sin volver a
descargar y deja comprobar, si un número sorprende, si el error es de la fuente
o del procesamiento.

---

## Procesado: `data/procesado/hechos_contables.parquet`

| Columna | Tipo |
|---|---|
| `cik` | string |
| `concepto` | string (`deuda_corto` \| `deuda_largo` \| `acciones`) |
| `etiqueta` | string |
| `end` | date |
| `filed` | date |
| `form` | string |
| `accn` | string |
| `valor` | float64 |

Clave: `(cik, concepto, end, accn)`. `filed` nunca nulo.

---

## Procesado: `data/procesado/precios.parquet`

| Columna | Tipo |
|---|---|
| `fecha` | date |
| `ticker` | string |
| `cierre` | float64 |
| `cierre_ajustado` | float64 |
| `volumen` | int64 |

Clave: `(fecha, ticker)`.

---

## Procesado: `data/procesado/divisiones.parquet`

| Columna | Tipo |
|---|---|
| `ticker` | string |
| `fecha` | date |
| `factor` | float64 |

Clave: `(ticker, fecha)`. Archivo vacío válido si ninguna empresa dividió.

---

## Procesado: `data/procesado/tasa_libre_riesgo.parquet`

| Columna | Tipo | Nota |
|---|---|---|
| `fecha` | date | |
| `r_anual` | float64 | **Decimal**: `0.0461` = 4,61 % |
| `arrastrada` | bool | |

Clave: `fecha`.

---

## Procesado: `data/procesado/panel_diario.parquet`

Entregable de la fase y entrada de la fase 2.

| Columna | Tipo | Nota |
|---|---|---|
| `fecha` | date | |
| `ticker` | string | |
| `E` | float64 | `cierre × acciones_ajustadas` |
| `D` | float64 | `deuda_corto + 0.5 × deuda_largo` |
| `r_anual` | float64 | Decimal |
| `cierre_ajustado` | float64 | Para `σ_E` en la fase 2 |
| `acciones_ajustadas` | float64 | En la base de la serie de precios |
| `deuda_corto` | float64 | |
| `deuda_largo` | float64 | |
| `filed_deuda` | date | **Auditoría del principio I** |
| `filed_acciones` | date | **Auditoría del principio I** |
| `factor_split` | float64 | Factor acumulado aplicado |

Clave: `(fecha, ticker)`.

**Invariante comprobable por consulta**, no solo por confianza en el código:

```
filed_deuda <= fecha  Y  filed_acciones <= fecha   en el 100 % de las filas
```

---

## Salida: `data/cobertura.csv`

| Columna | Tipo |
|---|---|
| `ticker` | string |
| `grupo` | string |
| `dias_cubiertos` | int |
| `dias_habiles` | int |
| `pct_cobertura` | float |
| `primer_dia` | date |
| `ultimo_dia` | date |
| `periodos_sin_deuda` | string |
| `etiquetas_usadas` | string |
| `divisiones_aplicadas` | int |
| `apta` | bool |
| `motivo_no_apta` | string |

Una fila por empresa del universo, siempre 30 filas. En CSV y no en Parquet
porque está hecho para abrirlo y leerlo.

---

## Salida: `data/manifiesto.json`

```json
{
  "ventana_inicio": "2021-11-25",
  "ventana_fin": "2026-11-24",
  "fecha_ejecucion": "2026-11-28T14:32:00",
  "versiones": {
    "python": "3.12.10",
    "pandas": "3.1.1",
    "yfinance": "1.8.0",
    "pyarrow": "26.0.1"
  },
  "fuente_tasa": "FRED DGS1",
  "filas_por_archivo": {
    "hechos_contables": 0,
    "precios": 0,
    "divisiones": 0,
    "tasa_libre_riesgo": 0,
    "panel_diario": 0
  },
  "empresas_aptas": 0,
  "empresas_no_aptas": 0
}
```

El campo `fuente_tasa` registra qué fuente entregó la tasa. Está ahí por el
riesgo R-01: si la fuente cambiase, cada conjunto de datos dirá cuál se usó, y
no habrá que deducirlo.
