# Constitución — Monitor de Probabilidad de Default (Merton/KMV)

## Principios fundamentales

### I. Sin look-ahead bias (NO NEGOCIABLE)

Ningún cálculo fechado en el día `t` PUEDE usar información que no estuviera
públicamente disponible en `t`.

- Todo dato contable DEBE incorporarse a la serie a partir de su fecha de
  publicación en la SEC (campo `filed`), NUNCA desde la fecha de cierre del
  periodo (campo `end`).
- Toda función que combine series de distinta frecuencia (diaria con trimestral)
  DEBE documentar en su docstring qué fecha usa como referencia temporal.
- Las medias, volatilidades y cualquier estadístico móvil DEBEN calcularse solo
  con observaciones anteriores o iguales a `t`.
- Cada transformación con riesgo de fuga temporal DEBE tener un test que la
  verifique con datos de prueba fechados.

**Razón:** la tesis del proyecto es que el mercado accionario anticipa el
deterioro crediticio antes que las agencias. Una sola fuga de información futura
produce exactamente esa apariencia de anticipación sin que sea real, y vuelve
inútil todo el resultado.

### II. Fidelidad metodológica

El método está fijado y NO se improvisa durante la implementación.

- Horizonte `T = 1` año. Tasa libre de riesgo: serie `DGS1` de FRED.
- Punto de default KMV: `D = deuda de corto plazo + 0.5 × deuda de largo plazo`.
- `E = precio de cierre × acciones en circulación` (acciones desde SEC XBRL).
- `V` y `σ_V` por iteración de Vassalou & Xing (2004): `σ_V⁰ = σ_E · E/(E+D)`,
  resolver la ecuación de Merton día a día, recalcular `σ_V` con los
  log-retornos de `V`, tolerancia `1e-4`.
- `μ` = media anualizada de los log-retornos de `V`. `DD` se calcula con `μ`.
  `PD = N(−DD)`.
- La `PD` se reporta e interpreta como **medida ordinal** (ranking de riesgo),
  no como probabilidad absoluta calibrada.
- `README.md` es la fuente de verdad metodológica. Cualquier desviación DEBE
  documentarse allí **antes** de implementarse, con su justificación.

**Razón:** las decisiones ya fueron tomadas y documentadas; cambiarlas a
conveniencia mientras se programa haría que los resultados no correspondan al
método publicado.

### III. Reproducibilidad con datos públicos

Cualquier persona DEBE poder reproducir los resultados desde un repositorio
recién clonado, sin credenciales de pago.

- Fuentes permitidas: `yfinance` (precios), API XBRL de la SEC (balances y
  acciones en circulación) y FRED vía CSV público (tasa libre de riesgo).
  Ninguna requiere API key de pago.
- `data/` NO DEBE versionarse. Todo dato descargado o derivado DEBE poder
  regenerarse ejecutando `python -m src.data`.
- El entorno DEBE quedar declarado en `requirements.txt`. Toda dependencia
  nueva se añade ahí en el mismo cambio que la introduce.
- Las entradas manuales (ratings crediticios, fechas de eventos de estrés)
  DEBEN guardarse en archivos versionados, con la fuente pública citada y la
  fecha de consulta.

**Razón:** un proyecto de portafolio que no se puede volver a correr no
demuestra nada; y los ratings, al ser manuales, son el único punto donde no hay
trazabilidad automática.

### IV. Secretos fuera del repo y respeto a las fuentes

- El User-Agent de la SEC DEBE leerse de la variable de entorno
  `SEC_USER_AGENT` (archivo `.env`). NUNCA hardcodeado ni versionado.
- `.env.example` DEBE documentar cada variable necesaria, sin valores reales.
- Toda petición a `data.sec.gov` DEBE enviar ese User-Agent y respetar el límite
  de **10 peticiones por segundo**.
- Si una fuente falla, bloquea o devuelve datos incompletos, el error DEBE
  propagarse con un mensaje claro. NO DEBE sustituirse en silencio por datos
  sintéticos, parciales o cacheados sin que quede registrado.

**Razón:** la SEC bloquea a los clientes no identificados, y un fallo silencioso
de descarga produce resultados que parecen válidos pero no lo son.

### V. Código verificado y legible

- Funciones pequeñas, con una sola responsabilidad, docstring en español y type
  hints en la firma.
- Cada fórmula del modelo DEBE tener al menos un test con valores conocidos.
  Caso de referencia obligatorio: `V = 100`, `D = 80`, `σ_V = 0.20`, `μ = 0`,
  `T = 1` → `DD ≈ 1.0`, `PD ≈ 15 %`.
- Los casos límite DEBEN estar cubiertos por tests: `σ_V → 0`, `V ≤ D`,
  series con huecos y empresas sin dato de deuda en algún trimestre.
- `pytest` DEBE pasar al 100 % antes de proponer el commit de cierre de fase.
- Importar un módulo de `src/` NO DEBE descargar datos, escribir archivos ni
  imprimir en pantalla. Todo efecto se dispara desde una llamada explícita.

**Razón:** el modelo produce números que nadie puede validar a ojo; los tests
con valores conocidos son la única defensa contra un error de signo o de
unidades que pase inadvertido.

## Restricciones técnicas y de alcance

- **Stack:** Python 3.11+ en `.venv`; pandas, numpy, scipy; yfinance, requests,
  python-dotenv; plotly y Streamlit para la presentación; pytest para pruebas.
- **Universo:** 30 empresas **no financieras** del S&P 500, con ratings
  variados e incluyendo algunas con episodios de estrés crediticio. Periodo:
  últimos 5 años.
- **Exclusión obligatoria:** bancos y aseguradoras. En ellos la deuda es parte
  del negocio operativo y el modelo estructural pierde sentido.
- **Estructura:** cada fase expone **un único módulo público** en `src/`:
  `src/data.py` (descarga y limpieza), `src/merton.py` (modelo) y
  `src/analysis.py` (validación y métricas). Ese módulo público PUEDE apoyarse
  en módulos auxiliares de una sola responsabilidad situados directamente en
  `src/`, **sin subpaquetes anidados**. El resto del árbol: `notebooks/`
  (exploración), `app/` (dashboard), `tests/` (pytest), `datos_entrada/`
  (recopilación manual, versionada) y `data/` (datos descargados, sin
  versionar).

  Añadir un módulo auxiliar en `src/` NO requiere enmienda. Crear un subpaquete
  anidado o una carpeta nueva de primer nivel SÍ la requiere.
- **Limitaciones declaradas:** lognormalidad sin saltos (subestima la PD de
  corto plazo), estructura de deuda resumida en un único punto de default, y
  solo empresas cotizadas. DEBEN mantenerse visibles en el README y no
  presentarse el resultado como si no existieran.

## Flujo de desarrollo

- **Fases secuenciales:** 0 estructura → 1 datos → 2 modelo → 3 análisis →
  4 dashboard y README. NO se inicia una fase sin cerrar la anterior y sin
  **confirmación explícita del usuario**.
- **Spec Kit por fase:** `/speckit-specify` → `/speckit-clarify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
- **Antes de implementar** cada fase, el método DEBE explicarse en español.
- **Antes de ejecutar** cualquier comando, DEBE explicarse en español qué hace.
- **Ningún archivo del proyecto se modifica sin autorización explícita** del
  usuario.
- **Al cerrar cada fase:** correr `pytest`, resumir los resultados obtenidos y
  **proponer** el commit. El commit no se ejecuta sin aprobación.
- **Al cerrar cada sesión:** actualizar la sección "Bitácora de desarrollo" del
  README con el estado, las decisiones tomadas y el siguiente paso.
- **Idioma:** documentación, docstrings, comentarios y mensajes de commit en
  español.
- **Identidad de git:** los commits usan la cuenta `Smartinez-Fin` con el correo
  privado de GitHub (`...@users.noreply.github.com`), nunca el correo personal.

## Gobernanza

Esta constitución prevalece sobre cualquier otra práctica del proyecto.
`CLAUDE.md` es la guía operativa del día a día y DEBE mantenerse coherente con
ella; `README.md` es la fuente de verdad metodológica. Si alguno entra en
conflicto con esta constitución, se corrige el documento en conflicto o se
enmienda la constitución, pero NO se deja la contradicción sin resolver.

**Enmiendas:** requieren una propuesta escrita con su justificación, la
aprobación explícita del autor del proyecto (único responsable), y la
actualización de la versión y de la fecha de última modificación en el mismo
cambio.

**Versionado semántico:**

- **MAJOR:** eliminar o redefinir un principio de forma incompatible con lo
  ya construido.
- **MINOR:** añadir un principio o sección, o ampliar materialmente una guía.
- **PATCH:** aclaraciones de redacción, correcciones de estilo y precisiones
  que no cambian el significado.

**Revisión de cumplimiento:** al cerrar cada fase se verifica que el código
escrito respeta los cinco principios, con atención especial al principio I (sin
look-ahead bias). Toda desviación DEBE corregirse o justificarse por escrito en
el README antes de dar la fase por terminada. La complejidad añadida DEBE
justificarse: a igualdad de resultado, se prefiere la solución más simple.

**Version**: 1.1.0 | **Ratified**: 2026-11-25 | **Last Amended**: 2026-11-28
