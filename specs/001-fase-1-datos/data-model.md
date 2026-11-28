# Modelo de datos — Fase 1

Entidades derivadas de la especificación, con sus campos, tipos y reglas de
validación. Las reglas llevan entre paréntesis el requisito que las origina.

---

## Empresa del universo

Archivo versionado: `datos_entrada/universo.csv`

| Campo | Tipo | Descripción |
|---|---|---|
| `ticker` | texto | Identificador de mercado, en mayúsculas |
| `cik` | texto | CIK de 10 dígitos con ceros a la izquierda |
| `nombre` | texto | Razón social |
| `sector` | texto | Sector, para poder demostrar la exclusión de financieras |
| `grupo` | enum | `base` o `estres` |
| `motivo` | texto | Por qué se incluyó. Obligatorio en el grupo de estrés |
| `categoria_rating` | enum | `AA+`, `A`, `BBB`, `BB`, `B-` (tramo usado en el reparto) |
| `apta` | booleano | Lo calcula el informe de cobertura; no se rellena a mano |

**Reglas de validación**

- 30 filas exactas, `ticker` único (FR-021).
- 22 filas con `grupo = base`, repartidas 3 / 5 / 8 / 4 / 2 entre `AA+`, `A`,
  `BBB`, `BB` y `B-` (FR-021).
- 8 filas con `grupo = estres`, todas con `motivo` no vacío (FR-021).
- Ningún `sector` perteneciente a banca o seguros (FR-021).
- Todo `ticker` debe existir en `datos_entrada/ratings.csv` (FR-020).
- `cik` de exactamente 10 caracteres numéricos (D-06).

---

## Calificación crediticia

Archivo versionado: `datos_entrada/ratings.csv`. Una fila por calificación
vigente y una fila adicional por cada cambio ocurrido dentro de la ventana.

| Campo | Tipo | Descripción |
|---|---|---|
| `ticker` | texto | Empresa |
| `agencia` | enum | `S&P`, `Moody's` o `Fitch` |
| `calificacion` | texto | Por ejemplo `BBB+`, `Ba2` |
| `escalon` | entero | Posición en la escala normalizada, para poder comparar agencias |
| `fecha` | fecha | Fecha de la calificación o del cambio |
| `tipo` | enum | `vigente`, `rebaja`, `mejora` o `sin_cambios` |
| `fuente_nivel` | enum | `agencia`, `prensa` o `regulador` (prioridad de FR-022) |
| `fuente_url` | texto | Enlace a la nota concreta, no al medio |
| `fecha_consulta` | fecha | Cuándo se consultó |

**Reglas de validación**

- Ninguna fila con `fuente_url` o `fecha_consulta` vacíos: un dato sin fuente
  citable no entra en la tabla (FR-020, FR-022).
- Toda empresa del universo tiene al menos una fila con `tipo = vigente`
  (FR-020).
- Una empresa sin cambios en la ventana lleva una fila explícita con
  `tipo = sin_cambios`, para distinguirla de una no consultada (FR-022).
- Toda empresa con `grupo = estres` tiene al menos una fila con `tipo = rebaja`
  que cumple el criterio: caída de dos escalones o más, o cruce desde grado de
  inversión a grado especulativo (FR-021).
- `fecha` dentro de la ventana, salvo en las filas `vigente`, que pueden ser
  anteriores.

---

## Evento de estrés

Archivo versionado: `datos_entrada/eventos_estres.csv`

| Campo | Tipo | Descripción |
|---|---|---|
| `ticker` | texto | Empresa |
| `fecha` | fecha | Fecha del episodio |
| `descripcion` | texto | Una línea |
| `fuente_url` | texto | Enlace a la nota concreta |
| `fecha_consulta` | fecha | Cuándo se consultó |

**Reglas de validación**: `fuente_url` y `fecha_consulta` obligatorios (FR-019);
`fecha` dentro de la ventana; `ticker` presente en el universo.

---

## Observación contable

`data/procesado/hechos_contables.parquet`. Un registro por hecho tal como lo
publicó la SEC, sin transformar.

| Campo | Tipo | Descripción |
|---|---|---|
| `cik` | texto | Empresa |
| `concepto` | enum | `deuda_corto`, `deuda_largo`, `acciones` |
| `etiqueta` | texto | Etiqueta XBRL realmente usada, p. ej. `us-gaap:DebtCurrent` |
| `end` | fecha | Fecha a la que se refiere el dato |
| `filed` | fecha | **Fecha de publicación**: gobierna la vigencia |
| `form` | texto | `10-K` o `10-Q` |
| `accn` | texto | Número de expediente, distingue reexpresiones |
| `valor` | decimal | Importe en USD, o número de acciones |

**Reglas de validación**

- `filed` nunca nulo: un hecho sin fecha de publicación no es utilizable (FR-003).
- `filed >= end` en los hechos de deuda. Se admite `filed` posterior en varios
  meses (D-01).
- Clave natural `(cik, concepto, end, accn)`. Dos registros con el mismo `end` y
  distinto `accn` son una reexpresión legítima, no un duplicado (FR-006, D-04).
- `valor >= 0` en los conceptos de deuda; `valor > 0` en `acciones` (FR-013).
- `etiqueta` siempre registrada, para que la cadena de respaldos sea auditable
  (FR-011, D-02).

---

## Observación de precio

`data/procesado/precios.parquet`

| Campo | Tipo | Descripción |
|---|---|---|
| `fecha` | fecha | Día de cotización |
| `ticker` | texto | Empresa |
| `cierre` | decimal | Precio **no ajustado por dividendos**: alimenta el patrimonio |
| `cierre_ajustado` | decimal | Ajustado por dividendos: alimenta la volatilidad |
| `volumen` | entero | Volumen negociado |

**Reglas de validación**: clave `(fecha, ticker)` única (FR-014);
`cierre > 0` y `cierre_ajustado > 0` (FR-013); solo días en que el mercado
cotizó, sin filas rellenadas (FR-012).

---

## División de acciones

`data/procesado/divisiones.parquet`

| Campo | Tipo | Descripción |
|---|---|---|
| `ticker` | texto | Empresa |
| `fecha` | fecha | Fecha efectiva de la división |
| `factor` | decimal | Por ejemplo `10.0` en una división 10:1 |

**Reglas de validación**: `factor > 0` y distinto de 1; clave
`(ticker, fecha)` única. Su existencia es obligatoria para auditar el ajuste
(FR-025).

---

## Observación de tasa libre de riesgo

`data/procesado/tasa_libre_riesgo.parquet`

| Campo | Tipo | Descripción |
|---|---|---|
| `fecha` | fecha | Día |
| `r_anual` | decimal | Tasa a un año en forma decimal (`0.0461`, no `4.61`) |
| `arrastrada` | booleano | `True` si se arrastró desde la última publicación |

**Reglas de validación**

- `r_anual` en forma decimal, nunca en porcentaje: evita un error de factor 100
  que pasaría desapercibido en la fórmula de Merton.
- El campo `arrastrada` hace explícito el arrastre en días sin publicación, de
  modo que no se confunda con un dato observado (FR-012).
- Se admite `r_anual` negativa: ha ocurrido en otros mercados y no es un error
  de datos.

---

## Panel diario de insumos

`data/procesado/panel_diario.parquet`. Es el entregable de la fase y la entrada
de la fase 2.

| Campo | Tipo | Descripción |
|---|---|---|
| `fecha` | fecha | Día hábil |
| `ticker` | texto | Empresa |
| `E` | decimal | Patrimonio de mercado: `cierre × acciones_ajustadas` |
| `D` | decimal | Punto de default: `deuda_corto + 0.5 × deuda_largo` |
| `r_anual` | decimal | Tasa libre de riesgo de ese día |
| `cierre_ajustado` | decimal | Para calcular `σ_E` en la fase 2 |
| `acciones_ajustadas` | decimal | Acciones en la base de la serie de precios |
| `deuda_corto` | decimal | Componente de `D`, conservado para auditar |
| `deuda_largo` | decimal | Componente de `D`, conservado para auditar |
| `filed_deuda` | fecha | `filed` del dato de deuda usado ese día |
| `filed_acciones` | fecha | `filed` del dato de acciones usado ese día |
| `factor_split` | decimal | Factor acumulado aplicado ese día |

**Reglas de validación**

- **`filed_deuda <= fecha` y `filed_acciones <= fecha` en el 100 % de las filas.**
  Es la prueba automática que sostiene SC-003 y el principio I.
- `D >= 0`; `E > 0` (FR-013).
- Clave `(fecha, ticker)` única (FR-014).
- Un día sin dato disponible **no genera fila**; no se rellena con ceros ni se
  interpola (FR-011, FR-012).
- `E` no presenta discontinuidades atribuibles a una división: se comprueba
  sobre al menos un caso real (SC-008, FR-024).

**Las columnas `filed_*` y `factor_split` no son decorativas**: convierten el
cumplimiento del principio I y del requisito de divisiones en algo verificable
por consulta, en lugar de confiar en que el código lo hizo bien.

---

## Informe de cobertura

`data/cobertura.csv`, en CSV porque está hecho para leerlo a ojo.

| Campo | Tipo | Descripción |
|---|---|---|
| `ticker` | texto | Empresa |
| `grupo` | enum | `base` o `estres` |
| `dias_cubiertos` | entero | Filas completas en el panel |
| `dias_habiles` | entero | Días hábiles de la ventana |
| `pct_cobertura` | decimal | Cociente de los dos anteriores |
| `primer_dia` | fecha | Primera fecha con dato |
| `ultimo_dia` | fecha | Última fecha con dato |
| `periodos_sin_deuda` | texto | Lista de periodos sin dato de deuda |
| `etiquetas_usadas` | texto | Qué etiqueta XBRL se usó para cada concepto |
| `divisiones_aplicadas` | entero | Número de divisiones corregidas |
| `apta` | booleano | `pct_cobertura >= 0.95` |
| `motivo_no_apta` | texto | Vacío si es apta |

**Reglas de validación**: una fila por cada empresa del universo, incluidas las
no aptas: ninguna empresa desaparece en silencio (FR-016).

---

## Manifiesto de ejecución

`data/manifiesto.json`. Lo que convierte SC-002 en verificable.

| Campo | Descripción |
|---|---|
| `ventana_inicio`, `ventana_fin` | La ventana fija usada |
| `fecha_ejecucion` | Momento de la descarga |
| `versiones` | Versión de Python y de cada dependencia relevante |
| `fuente_tasa` | Qué fuente entregó la tasa libre de riesgo (ver R-01) |
| `filas_por_archivo` | Número de filas de cada archivo generado |
| `empresas_aptas`, `empresas_no_aptas` | Recuento resultante |

---

## Flujo entre entidades

```text
ratings.csv ──────► universo.csv          (el reparto por rating exige los ratings primero: FR-026)
                         │
      ┌──────────────────┼──────────────────┐
      ▼                  ▼                  ▼
  hechos_contables   precios +          tasa_libre_riesgo
  (SEC, con filed)   divisiones         (FRED; fuente aislada)
      │                  │                  │
      │   vigencia.py    │   splits.py      │
      │  (filed <= t)    │ (factor acum.)   │
      └──────────────────┼──────────────────┘
                         ▼
                   panel_diario            ──► cobertura.csv + manifiesto.json
                         │
                         ▼
                   (fase 2: merton.py)
```
