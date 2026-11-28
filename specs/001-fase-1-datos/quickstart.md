# Guía de validación — Fase 1

Cómo comprobar que la fase 1 funciona de verdad. Cada escenario indica qué
ejecutar y qué resultado debe dar. Sirve para validar la implementación y para
volver a validarla si algo cambia más adelante.

---

## Requisitos previos

```powershell
# Entorno activo (debe verse (.venv) en la terminal)
.\.venv\Scripts\Activate.ps1

# El archivo .env debe existir y contener el User-Agent de la SEC
Get-Content .env
```

Se da por bueno el entorno ya reconstruido: Python 3.12.10, dependencias de
`requirements.txt` instaladas y 9 tests de humo pasando.

---

## Escenario 0 — Fuente de la tasa libre de riesgo: ✅ verificada

Comprobado el 2026-11-28: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1`
descarga el CSV con normalidad desde la máquina del autor. FRED se mantiene como
fuente y el riesgo R-01 queda cerrado.

**Nota operativa**: FRED no es accesible desde el entorno de desarrollo
asistido, así que los escenarios que descargan la tasa de verdad —el 4, el 5 y
el 6— los ejecuta el autor en su máquina. Todo lo demás se valida sin red.

---

## Escenario 1 — Los tests pasan sin conexión

Es el escenario más importante, porque es el que se ejecutará cientos de veces.

```powershell
pytest -q
```

**Resultado esperado**: todos los tests pasan, incluidos los 9 de humo que ya
existen. Las pruebas que tocan la red están marcadas `red` y **no** se ejecutan.

Para comprobar que de verdad no dependen de la red, basta desconectar el wifi y
repetir: el resultado debe ser idéntico.

Para ejecutar también las de red, cuando se quiera:

```powershell
pytest -m red
```

---

## Escenario 2 — El panel no mira al futuro (principio I)

Es la validación que sostiene la tesis del proyecto.

```powershell
pytest tests/test_vigencia.py -v
```

**Resultado esperado**: pasan al menos estos casos:

| Caso | Comportamiento exigido |
|---|---|
| Hecho con `filed` posterior a la fecha consultada | Se ignora por completo |
| Varios periodos publicados | Devuelve el `end` más reciente ya publicado |
| Mismo `end` publicado dos veces (reexpresión) | Usa el valor conocido en esa fecha, no el corregido después |
| Fecha anterior a toda publicación | Devuelve `None`, no extrapola |

Y sobre el panel ya construido, la comprobación directa:

```powershell
python -c "import pandas as pd; p = pd.read_parquet('data/procesado/panel_diario.parquet'); print('violaciones:', ((p.filed_deuda > p.fecha) | (p.filed_acciones > p.fecha)).sum())"
```

**Resultado esperado**: `violaciones: 0`. Cualquier número distinto de cero
invalida la fase entera (SC-003).

---

## Escenario 3 — Las divisiones de acciones no rompen el patrimonio

```powershell
pytest tests/test_splits.py -v
```

**Resultado esperado**: pasa el caso real de NVIDIA, cuyas acciones declaradas
pasan de 2.460 millones a 24.530 millones entre mayo y agosto de 2024 por su
división 10:1 (ver D-03 en [research.md](./research.md)). Tras el ajuste, el
patrimonio no presenta ningún salto en esa fecha (SC-008).

Comprobación visual sobre los datos descargados, si NVDA está en el universo:

```powershell
python -c "import pandas as pd; p = pd.read_parquet('data/procesado/panel_diario.parquet'); n = p[p.ticker=='NVDA'].sort_values('fecha'); print(n[(n.fecha>'2024-05-01')&(n.fecha<'2024-09-01')][['fecha','E','acciones_ajustadas','factor_split']].to_string())"
```

**Resultado esperado**: `E` evoluciona de forma continua. Un salto de factor 10
significa que el ajuste no se aplicó.

---

## Escenario 4 — Descarga de prueba sobre pocas empresas

Antes de descargar las 30, probar con tres (FR-017):

```powershell
python -m src.data --empresas NVDA,BA,T
```

**Resultado esperado**:

- Termina con código de salida `0`.
- Imprime el resumen de cobertura de las tres empresas.
- Crea `data/procesado/panel_diario.parquet` con filas de esas tres.
- Tarda menos de dos minutos.

---

## Escenario 5 — Reproducibilidad (SC-002)

```powershell
# 1. Guardar una huella del panel actual
python -c "import pandas as pd, hashlib; p = pd.read_parquet('data/procesado/panel_diario.parquet'); print(hashlib.sha256(pd.util.hash_pandas_object(p, index=False).values.tobytes()).hexdigest())"

# 2. Borrar todos los datos
Remove-Item -Recurse -Force data

# 3. Regenerar
python -m src.data

# 4. Repetir la huella del paso 1
```

**Resultado esperado**: la misma huella en el paso 4 que en el paso 1. Si
difiere, la ventana no es realmente fija o algo depende de la fecha de
ejecución.

---

## Escenario 6 — Un fallo de fuente se ve, no se disimula

```powershell
# Con el wifi desconectado
python -m src.data --solo tasas
```

**Resultado esperado**: código de salida distinto de `0` y un mensaje en
`stderr` que nombre la fuente inaccesible. **No** debe terminar en `0`, ni
escribir un archivo de tasas con ceros, ni usar una tasa constante de reserva
(FR-011, principio IV).

---

## Escenario 7 — Las entradas manuales están completas

```powershell
pytest tests/test_entradas.py -v
```

**Resultado esperado**: falla si el universo no tiene 30 filas, si el reparto
por tramo de rating no es 3/5/8/4/2, si alguna empresa de estrés no tiene
motivo, o si algún registro de rating o de evento carece de `fuente_url` o de
`fecha_consulta` (FR-020, SC-005).

---

## Escenario 8 — Nadie desaparece en silencio

```powershell
python -c "import pandas as pd; c = pd.read_csv('data/cobertura.csv'); print('filas:', len(c)); print(c[['ticker','pct_cobertura','apta','motivo_no_apta']].to_string())"
```

**Resultado esperado**: **30 filas exactas**, incluidas las empresas no aptas,
cada una con su motivo (FR-016). Si hay menos de 30, alguna empresa se perdió en
el camino sin avisar.

---

## Criterio de cierre de la fase

La fase 1 está terminada cuando:

- [ ] `pytest` pasa al 100 % sin conexión.
- [ ] Los diez casos límite de la especificación tienen test.
- [ ] `violaciones: 0` en la comprobación del escenario 2.
- [ ] El escenario 5 reproduce la misma huella.
- [ ] `data/cobertura.csv` tiene 30 filas y al menos las del grupo de estrés son
      aptas (sin ellas no hay estudio de evento).
- [ ] `data/manifiesto.json` registra ventana, versiones y fuente de la tasa.
- [ ] La bitácora del README está actualizada y el commit propuesto.
