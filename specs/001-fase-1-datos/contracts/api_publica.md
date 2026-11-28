# Contrato — Interfaz pública de la fase 1

Define qué expone cada módulo y qué garantiza. Son firmas y contratos, no
implementación: el código se escribe en la fase de implementación.

---

## Interfaz de línea de comandos

```
python -m src.data [--solo PASO] [--empresas TICKER,...] [--forzar]
```

| Parámetro | Efecto |
|---|---|
| *(sin parámetros)* | Descarga completa del universo y genera todos los archivos |
| `--empresas NVDA,BA` | Ejecuta solo sobre esas empresas (FR-017) |
| `--solo precios` | Ejecuta una sola etapa: `ratings`, `universo`, `sec`, `precios`, `tasas`, `panel` o `cobertura` |
| `--forzar` | Vuelve a descargar aunque exista el crudo en disco |

**Garantías de la CLI**

- Código de salida `0` solo si todas las etapas terminaron y el panel se
  escribió completo.
- Código de salida distinto de `0` con mensaje en `stderr` ante cualquier fallo
  de fuente, dato imposible o cobertura insuficiente del universo entero
  (FR-011).
- Imprime al final el resumen de cobertura por empresa (FR-015).
- Una ejecución interrumpida no deja el panel en estado aparentemente completo:
  los archivos procesados se escriben primero a un temporal y se renombran al
  terminar (FR-018).

---

## `src/config.py`

Constantes, sin lógica. No tiene funciones públicas.

| Constante | Valor |
|---|---|
| `VENTANA_INICIO` | `date(2021, 11, 25)` |
| `VENTANA_FIN` | `date(2026, 11, 24)` |
| `COBERTURA_MINIMA` | `0.95` |
| `PETICIONES_POR_SEGUNDO` | `8.0` |
| `ETIQUETAS` | Cadena de etiquetas XBRL por concepto, en orden de prioridad |
| `RUTA_DATOS`, `RUTA_ENTRADA` | Rutas de `data/` y `datos_entrada/` |

**Garantía**: la ventana nunca se deriva de la fecha de ejecución. Cambiarla es
editar este archivo, lo que deja constancia en el historial de git.

---

## `src/sec.py` — cliente XBRL

```python
def crear_cliente(user_agent: str, peticiones_por_segundo: float = 8.0,
                  descargar: Callable[[str, str], bytes] | None = None) -> ClienteSEC
```

```python
class ClienteSEC:
    def resolver_cik(self, ticker: str) -> str
    def obtener_hechos(self, cik: str, concepto: str) -> list[Hecho]
```

**Contrato**

- `user_agent` es **obligatorio y posicional**: es imposible construir el
  cliente sin él, lo que hace inviable incumplir FR-009 por descuido.
- El cliente no lee `.env` por sí mismo. Quien lo construye le pasa el valor.
  Así los tests no dependen de la configuración de la máquina.
- `descargar` permite inyectar una función de descarga falsa en los tests
  (D-10). Si es `None`, usa `requests`.
- Nunca supera `peticiones_por_segundo` (FR-010), medido como mínimo intervalo
  entre peticiones consecutivas.
- `obtener_hechos` recorre la cadena de etiquetas de `config.ETIQUETAS` y
  devuelve los hechos de la primera que responda, anotando en cada uno la
  etiqueta usada. Un **404 no es un error**: significa que la empresa no reporta
  esa etiqueta, y se pasa a la siguiente (D-02).
- Si ninguna etiqueta de la cadena responde, lanza `DatoNoDisponible` con el
  ticker y el concepto. **No devuelve una lista vacía**, porque un vacío se
  confunde con "sin deuda" (FR-011).
- Ante `429` o `503`, reintenta con espera creciente; al agotar los reintentos
  lanza `FuenteInaccesible`. Nunca devuelve datos parciales como si fueran
  completos.
- `resolver_cik` devuelve el CIK con ceros a la izquierda hasta 10 dígitos
  (D-06).

---

## `src/precios.py`

```python
def descargar_precios(tickers: list[str], inicio: date, fin: date,
                      descargar: Callable | None = None) -> tuple[DataFrame, DataFrame]
```

**Contrato**

- Devuelve dos tablas: precios y divisiones de acciones, con los esquemas de
  [esquemas_datos.md](./esquemas_datos.md).
- Llama a yfinance con **`auto_adjust=False` explícito**, de modo que `cierre`
  queda sin ajustar por dividendos y `cierre_ajustado` ajustado (D-05, FR-023).
- No rellena días sin cotización (FR-012).
- Elimina duplicados de `(fecha, ticker)` conservando una sola observación y
  devolviendo el recuento de eliminados (FR-014).
- Lanza `DatoNoDisponible` si una empresa no devuelve ninguna fila.

---

## `src/tasas.py`

```python
def descargar_tasa_libre_riesgo(inicio: date, fin: date,
                                descargar: Callable | None = None) -> DataFrame
```

**Contrato**

- Devuelve `fecha`, `r_anual` y `arrastrada`, con `r_anual` **en forma decimal**
  (`0.0461`), nunca en porcentaje.
- Marca `arrastrada = True` en los días hábiles de mercado sin publicación de
  tasa, donde se arrastra el último valor disponible.
- Lanza `FuenteInaccesible` si la fuente no responde: **no hay valor por
  defecto ni tasa constante de reserva** (FR-011, principio IV).

> **Esta es la única función que conoce la fuente de la tasa.** Es deliberado:
> el riesgo R-01 sobre la accesibilidad de FRED sigue abierto, y si hay que
> cambiar de fuente, el cambio se limita a esta función y a su test.

---

## `src/vigencia.py` — punto en el tiempo (función pura)

```python
def valor_vigente(hechos: list[Hecho], fecha: date) -> Hecho | None
def serie_vigente(hechos: list[Hecho], fechas: list[date]) -> DataFrame
```

**Contrato** — es el módulo que sostiene el principio I:

1. Se descartan todos los hechos con `filed > fecha`. **Sin excepciones.**
2. De los restantes, se agrupan por `end` y de cada grupo se toma el de `filed`
   más reciente: así se respeta la reexpresión conocida en esa fecha (FR-006).
3. De esos, se devuelve el de `end` más reciente (FR-005).
4. Devuelve `None` si no hay ningún hecho publicado a esa fecha. **No
   extrapola hacia atrás** (FR-011).

Sin red, sin archivos, sin reloj: entra una lista y una fecha, sale un hecho.
Por eso se puede probar de forma exhaustiva.

---

## `src/splits.py` (función pura)

```python
def factor_acumulado(divisiones: DataFrame, ticker: str, desde: date) -> float
def ajustar_acciones(acciones: DataFrame, divisiones: DataFrame) -> DataFrame
```

**Contrato**

- `factor_acumulado` devuelve el producto de los factores de las divisiones
  **posteriores a `desde`**. Sin divisiones posteriores devuelve `1.0`.
- `desde` es la fecha `end` del hecho (la fecha a la que se refiere el conteo),
  **no** su `filed`. Son dos fechas con dos propósitos distintos (D-03).
- `ajustar_acciones` devuelve el conteo expresado en la base de la serie de
  precios, más la columna `factor_split` aplicada, para que el ajuste sea
  auditable (FR-025).

---

## `src/panel.py`

```python
def construir_panel(hechos: DataFrame, precios: DataFrame,
                    divisiones: DataFrame, tasas: DataFrame,
                    universo: DataFrame) -> DataFrame
```

**Contrato**

- Devuelve el panel diario con el esquema de
  [esquemas_datos.md](./esquemas_datos.md), incluidas las columnas `filed_*` y
  `factor_split`.
- `E = cierre × acciones_ajustadas`; `D = deuda_corto + 0.5 × deuda_largo`
  (FR-002).
- **No emite ninguna fila** cuyo `filed_deuda` o `filed_acciones` sea posterior
  a `fecha`: es una condición verificada dentro de la función, no solo en los
  tests (FR-004).
- Omite la fila, en lugar de rellenarla, cuando falta cualquier insumo (FR-012).
- Lanza `ValorImposible` ante deuda negativa, acciones no positivas o precio no
  positivo, indicando empresa y fecha (FR-013).

---

## `src/cobertura.py`

```python
def calcular_cobertura(panel: DataFrame, universo: DataFrame,
                       hechos: DataFrame) -> DataFrame
```

**Contrato**

- Una fila por empresa del universo, **incluidas las que no tienen ninguna fila
  en el panel**: ninguna empresa desaparece en silencio (FR-016).
- `apta = pct_cobertura >= config.COBERTURA_MINIMA`.
- Rellena `motivo_no_apta` con una razón legible en las no aptas.
- No excluye a nadie: decidir qué hacer con una empresa no apta es del analista
  (FR-016).

---

## Excepciones

| Excepción | Cuándo se lanza |
|---|---|
| `FuenteInaccesible` | La fuente no responde o agota los reintentos |
| `DatoNoDisponible` | Ninguna etiqueta de la cadena devolvió datos para un concepto |
| `ValorImposible` | Deuda negativa, acciones ≤ 0, precio ≤ 0 |
| `ConfiguracionInvalida` | Falta `SEC_USER_AGENT`, o el universo no cumple sus reglas |

Todas heredan de una base `ErrorDeDatos` y **todas llevan en el mensaje la
empresa y la fecha o el periodo afectados**. El principio IV exige que un fallo
sea visible; un mensaje sin contexto es apenas mejor que el silencio.
