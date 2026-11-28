# Plan de implementación — Fase 1: Descarga y preparación de datos

**Rama**: `fase-1-datos` | **Fecha**: 2026-11-28 | **Especificación**: [spec.md](./spec.md)

**Entrada**: especificación de la fase en `/specs/001-fase-1-datos/spec.md`

## Resumen

Construir el panel diario de insumos del modelo Merton/KMV para 30 empresas no
financieras del S&P 500 en la ventana fija 2021-11-25 → 2026-11-24: patrimonio
de mercado, punto de default y tasa libre de riesgo para cada empresa y día
hábil, más el informe de cobertura y las tablas versionadas de ratings y eventos
de estrés.

El enfoque técnico está determinado por tres hallazgos de la investigación
(ver [research.md](./research.md)):

1. La API de la SEC entrega cada hecho con su fecha de publicación (`filed`), lo
   que permite implementar el control de look-ahead de forma exacta y no
   aproximada.
2. Las acciones en circulación **no** se reexpresan tras una división de
   acciones, confirmado con el caso real de NVIDIA (×10 en junio de 2024). El
   ajuste del factor acumulado es obligatorio, no una precaución.
3. Las funciones de descarga se separan de las de transformación, de modo que
   toda la lógica delicada —vigencia temporal, divisiones, ensamblado— quede en
   funciones puras y comprobables sin red.

## Contexto técnico

**Lenguaje / versión**: Python 3.12.10 en el entorno local `.venv`

**Dependencias principales**: pandas 3.1, numpy 2.5, scipy 1.18, yfinance 1.8
(con `auto_adjust=False` explícito), requests 2.34, python-dotenv 1.2,
pyarrow 26 (Parquet)

**Almacenamiento**: archivos locales en `data/`, excluida del control de
versiones. Crudos tal como llegan de la fuente; procesados en Parquet; informe
de cobertura en CSV; manifiesto de ejecución en JSON. Datos de entrada
recopilados a mano en `datos_entrada/`, esta sí versionada.

**Pruebas**: pytest 9.2, con inyección de dependencias en los módulos de
descarga y fixtures recortados de respuestas reales. Las pruebas que tocan la
red se marcan `@pytest.mark.red` y se excluyen por defecto.

**Plataforma objetivo**: Windows 11 con Python 3.12; el código no usa nada
específico de plataforma, así que funciona igual en Linux o macOS.

**Tipo de proyecto**: biblioteca con interfaz de línea de comandos
(`python -m src.data`), de un solo usuario, sin servicio en línea.

**Objetivos de rendimiento**: descarga completa del universo por debajo de 60
minutos (SC-006). Dimensionado: 180 peticiones a la SEC a 8 por segundo ≈ 23 s;
30 descargas de precios; 1 descarga de la tasa. El cuello de botella real es
yfinance, no la SEC.

**Restricciones**: máximo 10 peticiones por segundo contra `data.sec.gov`
(objetivo 8, para dejar margen); User-Agent obligatorio leído de
`SEC_USER_AGENT`; ningún dato sintético en sustitución de uno ausente; el
proyecto reside en OneDrive, así que el volumen en disco debe mantenerse bajo.

**Escala / alcance**: 30 empresas × ~1.255 días hábiles ≈ 37.650 filas en el
panel. Volumen en disco esperado por debajo de 100 MB.

## Verificación contra la constitución

*BARRERA: debe pasar antes de la investigación de fase 0 y volver a verificarse
tras el diseño de fase 1.*

| Principio | Cómo lo satisface este plan | Estado |
|---|---|---|
| **I. Sin look-ahead bias** | Módulo `vigencia.py` dedicado: para cada día toma el hecho con `filed` más reciente anterior o igual a esa fecha. Es una función pura con tests obligatorios. El campo `filed` fue verificado contra la API real | ✅ Pasa |
| **II. Fidelidad metodológica** | `D = DebtCurrent + 0.5 × LongTermDebtNoncurrent` (FR-002); ventana fija y tasa a un año según la especificación. Ninguna desviación introducida | ✅ Pasa |
| **III. Reproducibilidad con datos públicos** | Ventana fija, manifiesto de ejecución, `data/` regenerable con un comando, dependencias declaradas, entradas manuales versionadas con su fuente | ✅ Pasa |
| **IV. Secretos fuera del repo y respeto a las fuentes** | User-Agent desde `.env`; limitador a 8 peticiones/s; reintentos con espera creciente y **fallo explícito** al agotarlos; registro de qué etiqueta y qué fuente se usó en cada dato | ✅ Pasa |
| **V. Código verificado y legible** | Módulos planos de una sola responsabilidad; funciones con docstring en español y type hints; los diez casos límite cubiertos con fixtures, sin red | ✅ Pasa |

### Riesgos declarados

- **R-01 — CERRADO el 2026-11-28.** FRED no respondía desde el entorno de
  desarrollo asistido, pero el autor verificó que sí responde desde su máquina,
  que es donde se ejecuta el proyecto. Era una restricción de red del entorno,
  no un fallo de la fuente. FRED se mantiene y no hace falta enmendar la
  constitución. **Secuela operativa**: la descarga real de la tasa no se puede
  ejercitar desde el entorno asistido, así que el escenario 6 de la guía de
  validación lo ejecuta el autor. La tasa queda igualmente aislada en una sola
  función, y la contingencia del Tesoro de EE. UU. permanece documentada en
  [research.md](./research.md) por si la fuente cambiara en el futuro.

- **R-02 — Cobertura de etiquetas XBRL desigual entre empresas.** Se confirmó
  que `ShortTermBorrowings` devuelve 404 en NVIDIA. La cadena de respaldos de
  D-02 lo cubre, pero es previsible que alguna empresa del universo quede sin
  dato de deuda en algún trimestre. **Mitigación**: FR-015 y FR-016 ya obligan a
  reportarlo y a marcar la empresa como no apta, en lugar de rellenar el hueco.

## Estructura del proyecto

### Documentación (esta fase)

```text
specs/001-fase-1-datos/
├── spec.md                  # Especificación (ya aprobada)
├── plan.md                  # Este archivo
├── research.md              # Fase 0: decisiones de investigación verificadas
├── data-model.md            # Fase 1: entidades, campos y reglas de validación
├── quickstart.md            # Fase 1: guía de validación ejecutable
├── contracts/
│   ├── api_publica.md       # Funciones públicas de src/data.py
│   └── esquemas_datos.md    # Esquema de cada archivo de data/ y datos_entrada/
└── checklists/
    └── requirements.md      # Verificación de calidad de la especificación
```

### Código fuente (raíz del repositorio)

```text
src/
├── __init__.py
├── config.py                # Ventana fija, rutas, umbrales, etiquetas XBRL
├── data.py                  # Orquestador y CLI: `python -m src.data`
├── sec.py                   # Cliente XBRL de la SEC, con el limitador incluido
├── precios.py               # yfinance: cierre, cierre ajustado y divisiones
├── tasas.py                 # Tasa libre de riesgo (fuente aislada en una función)
├── vigencia.py              # Punto en el tiempo: filed, arrastre, reexpresiones
├── splits.py                # Factor acumulado de divisiones de acciones
├── panel.py                 # Ensamblado del panel diario y validaciones
├── cobertura.py             # Informe de cobertura y aptitud por empresa
├── merton.py                # (fase 2 — no se toca en esta fase)
└── analysis.py              # (fase 3 — no se toca en esta fase)

datos_entrada/               # Versionada en git: recopilación manual
├── universo.csv             # Las 30 empresas, con grupo y motivo de inclusión
├── ratings.csv              # Calificaciones y cambios, con fuente y fecha
└── eventos_estres.csv       # Episodios de estrés, con fuente y fecha

data/                        # NO versionada; regenerable con un comando
├── crudo/
│   ├── sec/                 # Un JSON por empresa y etiqueta
│   ├── precios/             # Un Parquet por empresa
│   └── tasas/               # CSV de la tasa, tal como llega
├── procesado/
│   ├── hechos_contables.parquet
│   ├── precios.parquet
│   ├── divisiones.parquet
│   ├── tasa_libre_riesgo.parquet
│   └── panel_diario.parquet
├── cobertura.csv
└── manifiesto.json

tests/
├── __init__.py
├── test_smoke.py            # Ya existe: 9 tests de importación
├── test_vigencia.py         # Sin look-ahead, arrastre, reexpresiones
├── test_splits.py           # Factor acumulado; caso real de NVIDIA
├── test_panel.py            # Ensamblado, valores imposibles, duplicados
├── test_cobertura.py        # Porcentajes, aptitud, periodos faltantes
├── test_sec.py              # Limitador, reintentos, 404 por etiqueta
├── test_precios.py          # Dos series de precios, calendario
├── test_tasas.py            # Parseo, arrastre en festivos
└── fixtures/                # Respuestas reales recortadas, en kilobytes

pytest.ini                   # Registro del marcador `red` y su exclusión
```

**Decisión de estructura**: se mantiene `src/data.py` como único punto de
entrada público y responsable de la CLI, tal como lo nombra la constitución, y
se reparte la implementación en módulos planos de una sola responsabilidad
dentro de `src/`. No se crean subpaquetes anidados. `src/merton.py` y
`src/analysis.py` quedan intactos: pertenecen a las fases 2 y 3.

## Orden de implementación

El orden está impuesto por FR-026: el reparto del grupo base depende de las
calificaciones, así que **la tabla de ratings va antes que el universo**.

| # | Paso | Entregable | Depende de |
|---|---|---|---|
| 1 | Configuración y esqueleto de la CLI | `config.py`, `data.py` con `--solo` y `--empresas` | — |
| 2 | **Tabla de ratings** y eventos de estrés | `datos_entrada/ratings.csv`, `eventos_estres.csv` | — |
| 3 | **Universo** derivado de la regla de FR-021 | `datos_entrada/universo.csv` | paso 2 |
| 4 | Cliente de la SEC con limitador | `sec.py` + tests | paso 1 |
| 5 | Precios y divisiones de acciones | `precios.py`, `splits.py` + tests | paso 1 |
| 6 | Tasa libre de riesgo | `tasas.py` + tests | paso 1, R-01 |
| 7 | Vigencia temporal (punto en el tiempo) | `vigencia.py` + tests | paso 4 |
| 8 | Ensamblado del panel | `panel.py` + tests | pasos 5, 6, 7 |
| 9 | Informe de cobertura y aptitud | `cobertura.py` + tests | paso 8 |
| 10 | Manifiesto y CLI completa | `manifiesto.json`, `python -m src.data` | paso 9 |

Los pasos 2 y 3 son trabajo de recopilación manual con verificación de fuentes;
el resto es código. El paso 3 debe revisarse y aprobarse antes de lanzar la
descarga completa, como exige FR-026.

## Seguimiento de complejidad

> Se rellena solo cuando la verificación contra la constitución tiene
> desviaciones que haya que justificar.

**Resueltas por enmienda de la constitución (v1.0.0 → v1.1.0, 2026-11-28).** Las
dos primeras dejaron de ser desviaciones: la versión 1.1.0 contempla
explícitamente los módulos auxiliares planos en `src/` y la carpeta
`datos_entrada/`. Se conserva aquí el razonamiento que motivó la enmienda.

| Decisión | Por qué es necesaria | Alternativa más simple, y por qué se rechazó |
|---|---|---|
| Nueve módulos en `src/` en lugar de concentrar la fase en `src/data.py` | Los 26 requisitos funcionales en un solo archivo darían un módulo de unas 900 líneas que mezclaría descarga, lógica temporal, ajustes y validación | Un único `src/data.py`: rechazado porque choca con el principio V ("funciones pequeñas, con una sola responsabilidad") y porque impediría probar la lógica temporal y la de divisiones sin arrastrar el código de red. `src/data.py` sigue siendo el único punto de entrada público |
| Carpeta `datos_entrada/`, versionada | FR-019 exige que ratings y eventos de estrés estén en el control de versiones, y `data/` está excluida de git por el principio III | Guardarlos dentro de `data/`: rechazado porque se perderían al regenerar los datos y no viajarían con el repositorio. Guardarlos en la raíz: rechazado por desorden |
| Archivo nuevo `pytest.ini` (no requiere enmienda: es configuración de raíz, no estructura de código) | Hace falta registrar el marcador `red` y excluirlo por defecto, para que `pytest` pase sin conexión | Pasar el parámetro a mano en cada ejecución: rechazado porque dependería de recordarlo, y un test que falla por falta de red acaba ignorándose |

## Verificación posterior al diseño

Repetida tras completar el diseño de la fase 1 (modelo de datos y contratos):

- **Principio I**: la lógica temporal quedó aislada en `vigencia.py` como función
  pura, con tres tests obligatorios. ✅
- **Principio II**: el modelo de datos no introduce ninguna transformación que
  altere el método del README. ✅
- **Principio III**: el manifiesto hace verificable la reproducibilidad; el
  riesgo R-01 sigue abierto y documentado, no oculto. ⚠️
- **Principio IV**: los contratos de `sec.py` exigen el User-Agent como
  parámetro obligatorio, de modo que es imposible llamar al cliente sin él. ✅
- **Principio V**: cada módulo tiene su archivo de tests asignado y los diez
  casos límite están repartidos entre ellos sin solapamiento. ✅

Sin desviaciones nuevas introducidas por el diseño.
