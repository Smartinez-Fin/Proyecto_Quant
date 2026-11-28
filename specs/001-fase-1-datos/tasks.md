# Tareas: Fase 1 — Descarga y preparación de datos

**Entrada**: documentos de diseño de `/specs/001-fase-1-datos/`

**Prerrequisitos**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: **incluidos y obligatorios**. No son opcionales en este proyecto: el
principio V de la constitución exige pruebas por cada fórmula y transformación,
y SC-007 exige cubrir los diez casos límite.

**Organización**: por historia de usuario, para que cada una se pueda
implementar y probar por separado.

## Formato: `[ID] [P?] [Historia] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Historia]**: `US1`, `US2`, `US3` según [spec.md](./spec.md)
- **[MANUAL]**: trabajo de recopilación del autor; no es programable
- **[AUTOR]**: debe ejecutarse en la máquina del autor, no en el entorno
  asistido (FRED no es accesible desde allí; ver D-08 en research.md)

## Nota sobre el orden de las historias

FR-026 impone que **la tabla de ratings se construya antes que el universo**,
porque el reparto del grupo base depende de las calificaciones. Y el universo lo
necesitan las tres historias. Por eso la recopilación de ratings y la fijación
del universo están en la **fase 2 (bloqueante)** y no en la historia 3, que es
donde aparecían en la especificación. La historia 3 conserva lo que sí es
independiente: la tabla de eventos de estrés y las validaciones de completitud y
de fuentes.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: configuración y andamiaje, sin lógica de negocio.

- [ ] T001 Crear `pytest.ini` en la raíz: registrar el marcador `red` y
  excluirlo por defecto con `addopts = -m "not red"`, para que `pytest` pase sin
  conexión (quickstart escenario 1)
- [ ] T002 [P] Crear `src/config.py` con `VENTANA_INICIO = date(2021, 11, 25)`,
  `VENTANA_FIN = date(2026, 11, 24)`, `COBERTURA_MINIMA = 0.95`,
  `PETICIONES_POR_SEGUNDO = 8.0`, `RUTA_DATOS`, `RUTA_ENTRADA` y la cadena
  `ETIQUETAS` de etiquetas XBRL por concepto en orden de prioridad según D-02 de
  research.md. Sin lógica: solo constantes, y la ventana nunca derivada de la
  fecha de ejecución
- [ ] T003 [P] Crear `src/errores.py` con `ErrorDeDatos` y sus cuatro
  subclases `FuenteInaccesible`, `DatoNoDisponible`, `ValorImposible` y
  `ConfiguracionInvalida`, cada una obligando a incluir empresa y fecha o
  periodo en el mensaje (contracts/api_publica.md, sección Excepciones)
- [ ] T004 [P] Fijar la versión de `yfinance` en `requirements.txt` (de
  `>=0.2.50` a `==1.8.0`), porque el valor por defecto de `auto_adjust` cambió
  entre versiones y con él el significado de la columna `Close` (D-05)
- [ ] T005 [P] Crear `tests/fixtures/` con recortes reales en kilobytes: una
  respuesta de `companyconcept` de la SEC con hechos que incluyan `filed` y una
  reexpresión, una tabla de precios con dos series, una serie de divisiones con
  el 10:1 de NVIDIA, y un CSV de tasa con días sin publicación (D-10)
- [ ] T006 [P] Crear `datos_entrada/` con las tres plantillas CSV vacías, solo
  con sus cabeceras exactas según [contracts/esquemas_datos.md](./contracts/esquemas_datos.md):
  `universo.csv`, `ratings.csv` y `eventos_estres.csv`

---

## Fase 2: Base bloqueante (prerrequisitos de todas las historias)

**Propósito**: las entradas manuales de las que dependen las tres historias.

**⚠️ CRÍTICO**: ninguna historia puede empezar hasta que esta fase esté completa.

- [ ] T007 **[MANUAL]** Recopilar las calificaciones crediticias en
  `datos_entrada/ratings.csv`: calificación vigente de cada candidata más los
  cambios ocurridos en la ventana, con agencia, fecha, escalón normalizado,
  nivel de fuente, URL de la nota concreta y fecha de consulta. Orden de
  prioridad de fuentes: agencia → prensa financiera → informe ante el
  regulador. Una empresa sin cambios lleva fila explícita con
  `tipo = sin_cambios`. Campos restringidos: `data-model.md` →
  `Calificación crediticia.tipo`, `.fuente_nivel`, `.escalon`, `.fuente_url`,
  `.fecha_consulta`
- [ ] T008 **[MANUAL]** Fijar el universo en `datos_entrada/universo.csv`
  aplicando la regla de FR-021 sobre la tabla del paso anterior: 22 empresas del
  grupo base con reparto exacto 3 / 5 / 8 / 4 / 2 entre `AA+`, `A`, `BBB`, `BB`
  y `B-`, más 8 del grupo de estrés con motivo escrito. Sin bancos ni
  aseguradoras. Campos restringidos: `data-model.md` →
  `Empresa del universo.cik` (texto de 10 dígitos, nunca entero),
  `.grupo`, `.categoria_rating`, `.motivo`. **Requiere revisión y aprobación
  antes de lanzar la descarga completa (FR-026)**
- [ ] T009 Crear `src/entradas.py` con los cargadores y validadores de las tres
  tablas de `datos_entrada/`, leyendo `cik` como texto para no perder los ceros
  a la izquierda, y lanzando `ConfiguracionInvalida` con el detalle del registro
  incumplidor
- [ ] T010 Crear `tests/test_entradas.py`: 30 filas exactas, reparto
  3/5/8/4/2 del grupo base, motivo obligatorio en el grupo de estrés, toda
  empresa con calificación asociada, y ningún registro sin `fuente_url` o
  `fecha_consulta` (quickstart escenario 7, SC-005)

**Punto de control**: entradas validadas. Las historias pueden empezar.

---

## Fase 3: Historia 1 — Panel diario de insumos (Prioridad: P1) 🎯 MVP

**Objetivo**: un comando produce, por empresa y día hábil, el patrimonio de
mercado, el punto de default y la tasa libre de riesgo.

**Prueba independiente**: ejecutar la descarga sobre dos o tres empresas y
obtener una tabla diaria continua con las tres cantidades y unidades coherentes.

### Descarga desde las fuentes

- [ ] T011 [P] [US1] Crear `src/sec.py` con `crear_cliente` y `ClienteSEC`
  (`resolver_cik`, `obtener_hechos`): User-Agent obligatorio y posicional,
  limitador que nunca supera `config.PETICIONES_POR_SEGUNDO`, recorrido de la
  cadena de etiquetas anotando la usada, reintentos con espera creciente ante
  429 y 503, y función de descarga inyectable. Campos restringidos:
  `data-model.md` → `Observación contable.filed` (nunca nulo),
  `.etiqueta`, `.valor`, `.accn`
- [ ] T012 [P] [US1] Crear `tests/test_sec.py`: el limitador respeta el
  intervalo mínimo entre peticiones; un **404 por etiqueta inexistente** pasa a
  la siguiente de la cadena y no es un error; agotar la cadena lanza
  `DatoNoDisponible` y **nunca** devuelve lista vacía; `resolver_cik` rellena
  con ceros a 10 dígitos. Cubre los casos límite **3 (cambio de identificador)**
  y **8 (fuente que rechaza las peticiones)**
- [ ] T013 [P] [US1] Crear `src/precios.py` con `descargar_precios`, llamando a
  yfinance con `auto_adjust=False` **explícito** y devolviendo la tabla de
  precios y la de divisiones. Campos restringidos: `data-model.md` →
  `Observación de precio.cierre`, `.cierre_ajustado` (ambos mayores que cero),
  y `División de acciones.factor`
- [ ] T014 [P] [US1] Crear `tests/test_precios.py`: se obtienen las dos series
  y son distintas en una empresa con dividendos; no se rellenan los días sin
  cotización; se eliminan los duplicados de `(fecha, ticker)` devolviendo el
  recuento. Cubre el caso límite **9 (dato duplicado para la misma fecha)**
- [ ] T015 [P] [US1] Crear `src/tasas.py` con
  `descargar_tasa_libre_riesgo`, **única función que conoce la fuente de la
  tasa**, devolviendo la tasa en forma decimal y marcando el arrastre. Campos
  restringidos: `data-model.md` → `Observación de tasa libre de riesgo.r_anual`
  (decimal, nunca porcentaje) y `.arrastrada`
- [ ] T016 [P] [US1] Crear `tests/test_tasas.py`: el parseo convierte `4.61` en
  `0.0461`; los días hábiles sin publicación arrastran el último valor y quedan
  marcados; una tasa negativa se acepta; y si la fuente no responde se lanza
  `FuenteInaccesible` **sin valor por defecto ni tasa constante de reserva**.
  Cubre el caso límite **4 (días sin precio frente a días sin tasa)**

### Lógica delicada (funciones puras, sin red)

- [ ] T017 [US1] Crear `src/vigencia.py` con `valor_vigente` y `serie_vigente`:
  descartar todo hecho con `filed` posterior a la fecha, de cada `end` tomar el
  `filed` más reciente conocido, y devolver el `end` más reciente; `None` si no
  hay nada publicado, **sin extrapolar hacia atrás**. Campo restringido:
  `data-model.md` → `Observación contable.filed`
- [ ] T018 [US1] Crear `tests/test_vigencia.py`: un hecho con `filed`
  posterior se ignora; se arrastra el último publicado; el mismo `end`
  publicado dos veces usa el valor conocido en la fecha y no el corregido
  después; antes de toda publicación devuelve `None`. Cubre el caso límite
  **5 (reexpresiones contables)** (quickstart escenario 2)
- [ ] T019 [US1] Crear `src/splits.py` con `factor_acumulado` y
  `ajustar_acciones`: producto de los factores de las divisiones **posteriores a
  `end`** (no a `filed`), y conteo de acciones expresado en la base de la serie
  de precios, con la columna `factor_split` para poder auditarlo
- [ ] T020 [US1] Crear `tests/test_splits.py`: sin divisiones posteriores el
  factor es `1.0`; se usa `end` y no `filed` como fecha de corte; y el **caso
  real de NVIDIA** (2.460 millones declarados en mayo de 2024 frente a 24.530 en
  agosto) queda corregido sin salto en el patrimonio. Cubre el caso límite
  **10 (división de acciones)** (SC-008, quickstart escenario 3)

### Ensamblado y CLI

- [ ] T021 [US1] Crear `src/panel.py` con `construir_panel`:
  `E = cierre × acciones_ajustadas`, `D = deuda_corto + 0.5 × deuda_largo`, y
  **verificación interna** de que ninguna fila emitida tiene `filed` posterior a
  su fecha. Campos restringidos: `data-model.md` → `Panel diario de insumos.E`,
  `.D`, `.filed_deuda`, `.filed_acciones`, `.factor_split`
- [ ] T022 [US1] Crear `tests/test_panel.py`: el punto de default usa el
  coeficiente 0,5; falta un insumo y **se omite la fila en lugar de
  rellenarla**; una deuda negativa, acciones no positivas o un precio no
  positivo lanzan `ValorImposible` con empresa y fecha. Cubre los casos límite
  **1 (trimestre sin dato de deuda)** y **6 (valores imposibles)**
- [ ] T023 [US1] Implementar `src/data.py` como orquestador y CLI
  (`python -m src.data`) con `--empresas`, `--solo` y `--forzar`, escribiendo
  los archivos procesados primero a un temporal y renombrándolos al terminar, y
  devolviendo código de salida distinto de cero ante cualquier fallo
- [ ] T024 [US1] Crear `tests/test_data.py`: una ejecución interrumpida **no
  deja el panel en estado aparentemente completo**; los códigos de salida
  distinguen éxito de fallo; `--empresas` restringe el trabajo al subconjunto.
  Cubre el caso límite **7 (descarga interrumpida)**
- [ ] T025 **[AUTOR]** [US1] Ejecutar `python -m src.data --empresas NVDA,BA,T`
  en la máquina del autor y comprobar que termina en código 0, imprime el
  resumen y genera el panel en menos de dos minutos (quickstart escenario 4)

**Punto de control**: el MVP está entregado. Con esto la fase 2 del proyecto
(modelo Merton/KMV) ya podría empezar.

---

## Fase 4: Historia 2 — Auditoría de integridad y cobertura (Prioridad: P2)

**Objetivo**: demostrar que ningún dato contable se usó antes de estar
disponible, y saber qué le falta a cada empresa.

**Prueba independiente**: sobre un panel ya construido, obtener por empresa el
porcentaje de días cubiertos, el rango de fechas y los periodos sin deuda.

- [ ] T026 [US2] Crear `src/cobertura.py` con `calcular_cobertura`: una fila
  por empresa del universo **incluidas las que no tienen ninguna fila en el
  panel**, con etiquetas usadas y divisiones aplicadas. Campos restringidos:
  `data-model.md` → `Informe de cobertura.pct_cobertura`, `.apta`,
  `.motivo_no_apta`, `.periodos_sin_deuda`
- [ ] T027 [US2] Crear `tests/test_cobertura.py`: siempre 30 filas, también
  para empresas sin ninguna fila en el panel; `apta` sale de
  `config.COBERTURA_MINIMA`; una empresa que salió a bolsa dentro de la ventana
  queda no apta con su motivo. Cubre el caso límite **2 (empresa con menos
  historia que el periodo)** (quickstart escenario 8)
- [ ] T028 [US2] Añadir a `src/data.py` la escritura de `data/cobertura.csv` y
  de `data/manifiesto.json`, con ventana usada, fecha de ejecución, versiones de
  las dependencias, fuente de la tasa y filas por archivo
  ([contracts/esquemas_datos.md](./contracts/esquemas_datos.md))
- [ ] T029 [US2] Añadir a `tests/test_panel.py` el test del invariante del
  principio I sobre el panel completo: `filed_deuda <= fecha` y
  `filed_acciones <= fecha` en el **100 %** de las filas (SC-003)

**Punto de control**: la cobertura es auditable y el cumplimiento del principio
I es comprobable por consulta, no solo por confianza en el código.

---

## Fase 5: Historia 3 — Ratings y eventos documentados (Prioridad: P3)

**Objetivo**: que la fase 3 del proyecto pueda comparar el modelo contra las
agencias.

**Prueba independiente**: toda empresa tiene calificación con fuente
verificable, y cada evento de estrés tiene fecha y fuente.

- [ ] T030 **[MANUAL]** [US3] Rellenar `datos_entrada/eventos_estres.csv` con
  los episodios de estrés de las 8 empresas del grupo correspondiente: fecha,
  descripción de una línea, URL de la nota y fecha de consulta. Campos
  restringidos: `data-model.md` → `Evento de estrés.fuente_url`,
  `.fecha_consulta`
- [ ] T031 [US3] Ampliar `src/entradas.py` con la validación del criterio de
  estrés: cada empresa del grupo de estrés debe tener al menos una rebaja de dos
  escalones o más, o un cruce desde grado de inversión a grado especulativo,
  medido sobre `escalon` (FR-021)
- [ ] T032 [US3] Ampliar `tests/test_entradas.py`: una empresa de estrés cuya
  única acción es una rebaja de un escalón **falla** la validación; un evento
  sin fuente falla; una fecha de evento fuera de la ventana falla

**Punto de control**: las entradas manuales están completas y verificadas.

---

## Fase 6: Cierre y validación transversal

- [ ] T033 **[AUTOR]** Ejecutar la descarga completa de las 30 empresas y
  comprobar que termina por debajo de los 60 minutos (SC-006)
- [ ] T034 **[AUTOR]** Validar la reproducibilidad: calcular la huella del
  panel, borrar `data/`, regenerar y comprobar que la huella coincide
  (quickstart escenario 5, SC-002)
- [ ] T035 **[AUTOR]** Validar que un fallo de fuente se ve: con la red
  desconectada, `python -m src.data --solo tasas` debe terminar con código
  distinto de cero y mensaje en `stderr`, sin escribir tasas en cero
  (quickstart escenario 6)
- [ ] T036 [P] Actualizar el árbol de `README.md` con los módulos realmente
  creados, y marcar la fase 1 en la hoja de ruta
- [ ] T037 [P] Actualizar la sección "Bitácora de desarrollo" de `README.md`
  con el resultado de la fase: cobertura obtenida, empresas no aptas y
  decisiones tomadas durante la implementación
- [ ] T038 Ejecutar `pytest` completo, verificar la lista de cierre del
  quickstart y proponer el commit de cierre de la fase 1

---

## Dependencias

```text
Fase 1 (T001-T006)  ──► Fase 2 (T007-T010)  ──► Fase 3 (US1, T011-T025)
                                                      │
                                      ┌───────────────┴───────────────┐
                                      ▼                               ▼
                           Fase 4 (US2, T026-T029)        Fase 5 (US3, T030-T032)
                                      └───────────────┬───────────────┘
                                                      ▼
                                           Fase 6 (T033-T038)
```

**Dependencias internas que importan**

- **T008 depende de T007**: el reparto del grupo base necesita los ratings
  (FR-026). Es la dependencia que define el orden de toda la fase.
- **T017 depende de T011**: la vigencia temporal opera sobre los hechos con su
  `filed`.
- **T021 depende de T013, T015, T017 y T019**: el panel necesita las dos series
  de precios, la tasa, la vigencia y el ajuste de divisiones.
- **T026 depende de T021**: la cobertura se calcula sobre el panel.
- **US2 y US3 son independientes entre sí** y pueden hacerse en cualquier orden
  una vez terminado US1.

---

## Oportunidades de paralelismo

**En la fase 1**: T002 a T006 son archivos distintos y sin dependencias; se
pueden hacer todos a la vez. Solo T001 conviene primero, para que `pytest`
funcione desde el inicio.

**En la fase 3, los tres módulos de descarga**: T011/T012 (SEC), T013/T014
(precios) y T015/T016 (tasa) tocan archivos distintos y no se conocen entre sí.
Son tres bloques paralelos.

**Lo que NO se puede paralelizar**: T017 a T024. Cada uno consume la salida del
anterior, y es justamente donde está la lógica que puede fallar en silencio.

---

## Estrategia de implementación

**Primero el MVP**: fases 1 a 3. Al terminar T025 existe un panel diario
utilizable, y la fase 2 del proyecto (el modelo Merton/KMV) ya podría arrancar
aunque no hubiera informe de cobertura ni tabla de eventos.

**Después la red de seguridad**: la fase 4 es la que demuestra que el MVP es
correcto. Tentador posponerla, pero es la que sostiene la tesis del proyecto; si
el panel tuviera fuga temporal, es mejor descubrirlo antes de construir el
modelo encima.

**Al final lo que habilita la fase 3 del proyecto**: la fase 5 no hace falta
para calcular DD ni PD, solo para validarlas contra las agencias.

**Orden recomendado de trabajo conjunto**

1. Yo hago T001 a T006 (preparación) y te dejo las plantillas CSV listas.
2. Tú haces T007 y T008 (ratings y universo), que es trabajo de verificación de
   fuentes y no puedo hacerlo de forma fiable.
3. Yo hago T009 a T024 (todo el código y sus tests), que se puede escribir y
   probar sin red.
4. Tú ejecutas T025, y luego T033 a T035, que necesitan red y FRED.

---

## Recuento

| Fase | Tareas | De ellas manuales | De ellas a ejecutar por el autor |
|---|---|---|---|
| 1 — Preparación | 6 | 0 | 0 |
| 2 — Base bloqueante | 4 | **2** | 0 |
| 3 — US1 (MVP) | 15 | 0 | **1** |
| 4 — US2 | 4 | 0 | 0 |
| 5 — US3 | 3 | **1** | 0 |
| 6 — Cierre | 6 | 0 | **3** |
| **Total** | **38** | **3** | **4** |

**Casos límite cubiertos**: los diez de la especificación, repartidos sin
solapamiento entre T012 (casos 3 y 8), T014 (caso 9), T016 (caso 4), T018
(caso 5), T020 (caso 10), T022 (casos 1 y 6), T024 (caso 7) y T027 (caso 2).
