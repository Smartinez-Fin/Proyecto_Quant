# Especificación — Fase 1: Descarga y preparación de datos

**Rama**: `fase-1-datos`

**Creada**: 2026-11-25

**Estado**: Borrador — aclaraciones resueltas; falta fijar la lista concreta de
empresas en `/speckit-clarify`

**Entrada**: Descripción del usuario: "Fase 1 — Descarga y preparación de datos.
Obtener y guardar los insumos del modelo Merton/KMV para 30 empresas no
financieras del S&P 500 de los últimos 5 años: precios de cierre diarios,
acciones en circulación y deuda de corto y largo plazo con su fecha de
publicación, tasa libre de riesgo diaria, y una tabla versionada de ratings
crediticios con fuente y fecha de consulta."

## Escenarios de uso y pruebas *(obligatorio)*

### Historia 1 — Panel diario de insumos del modelo (Prioridad: P1)

El analista ejecuta un único comando y obtiene, para cada empresa del universo y
cada día hábil del periodo, las cuatro cantidades que el modelo de Merton
necesita: el valor de mercado del patrimonio, el punto de default, la tasa libre
de riesgo y la serie de precios de la que se deriva la volatilidad del
patrimonio. El resultado queda guardado localmente para no volver a descargarlo.

**Por qué esta prioridad**: sin este panel no existe la fase 2. Es el mínimo
entregable que ya aporta valor: con él se puede calcular DD y PD aunque no haya
ratings ni auditoría de cobertura.

**Prueba independiente**: ejecutar la descarga para un subconjunto reducido de 2
o 3 empresas y verificar que se obtiene una tabla diaria continua, sin huecos no
justificados, con las cuatro cantidades presentes y con unidades coherentes
(moneda y cantidad de acciones en la misma escala).

**Escenarios de aceptación**:

1. **Dado** un universo definido y un periodo de 5 años, **cuando** el analista
   ejecuta la descarga completa, **entonces** obtiene un panel diario por
   empresa con patrimonio, punto de default y tasa libre de riesgo, y un resumen
   que indica la cobertura lograda para cada empresa.
2. **Dado** que la descarga ya se ejecutó antes, **cuando** se vuelve a
   ejecutar, **entonces** el resultado es idéntico para el mismo periodo
   (reproducible) y no se duplican registros.
3. **Dado** un día en que el mercado estuvo cerrado, **cuando** se construye el
   panel, **entonces** ese día no aparece como observación con valores
   inventados.
4. **Dado** que se borra por completo la carpeta de datos, **cuando** se
   ejecuta de nuevo el comando de descarga, **entonces** todos los datos se
   reconstruyen sin intervención manual.

---

### Historia 2 — Auditoría de integridad temporal y cobertura (Prioridad: P2)

El analista necesita poder demostrar que ningún dato contable se usó antes de
estar públicamente disponible, y saber exactamente qué le falta a cada empresa
antes de pasar al modelo.

**Por qué esta prioridad**: es la defensa del principio I de la constitución. La
tesis del proyecto —que el mercado anticipa a las agencias— se cae si hay fuga
de información futura, y un informe de cobertura evita descubrir en la fase 3
que media muestra estaba incompleta.

**Prueba independiente**: tomar un trimestre cuya fecha de publicación es
posterior a su fecha de cierre y comprobar que el valor solo aparece en el panel
a partir de la fecha de publicación, nunca antes.

**Escenarios de aceptación**:

1. **Dado** un dato contable con fecha de cierre de periodo anterior a su fecha
   de publicación, **cuando** se construye el panel, **entonces** ese valor
   aparece únicamente desde la fecha de publicación en adelante.
2. **Dado** un panel ya construido, **cuando** se ejecuta la auditoría,
   **entonces** se obtiene por empresa el porcentaje de días cubiertos, el
   primer y último día disponibles, y la lista de periodos sin dato de deuda.
3. **Dado** que una misma métrica fue republicada con un valor corregido para
   el mismo periodo, **cuando** se construye el panel, **entonces** queda
   registrado cuál de las dos versiones se usó en cada fecha y por qué.
4. **Dado** que una empresa no alcanza la cobertura mínima exigida, **cuando**
   termina la descarga, **entonces** la empresa queda marcada como no apta y el
   motivo se reporta al analista, sin excluirla en silencio.

---

### Historia 3 — Ratings y eventos de estrés documentados (Prioridad: P3)

El analista registra, en archivos que viajan con el repositorio, la calificación
crediticia de cada empresa y las fechas de los episodios de estrés que se usarán
para validar el modelo, cada uno con su fuente pública y la fecha en que se
consultó.

**Por qué esta prioridad**: no hace falta para calcular DD ni PD, pero sin ella
la fase 3 no puede comparar el modelo contra las agencias. Es información
recopilada a mano, así que es el único punto del proyecto sin trazabilidad
automática.

**Prueba independiente**: revisar que toda empresa del universo tiene una
calificación asociada y que cada registro cita una fuente verificable con su
fecha de consulta.

**Escenarios de aceptación**:

1. **Dado** el universo de empresas, **cuando** se consulta la tabla de
   ratings, **entonces** cada empresa tiene su calificación vigente y los
   cambios ocurridos en la ventana, cada uno con agencia, fecha, fuente y fecha
   de consulta; y las empresas sin cambios figuran explícitamente como tales.
2. **Dado** un evento de estrés crediticio, **cuando** se registra, **entonces**
   incluye la empresa, la fecha del evento, una descripción breve y la fuente.
3. **Dado** un registro al que le falta la fuente o la fecha de consulta,
   **cuando** se valida la tabla, **entonces** la validación falla e indica qué
   registro está incompleto.

---

### Casos límite

- **Trimestre sin dato de deuda**: una empresa no reporta deuda de corto o de
  largo plazo en algún periodo. El punto de default no puede inventarse.
- **Empresa con menos historia que el periodo pedido**: salió a bolsa hace
  menos de 5 años, o dejó de cotizar durante el periodo.
- **Cambio de identificador**: la empresa cambió de ticker o de razón social
  durante el periodo.
- **División de acciones (*split*)**: la empresa dividió sus acciones durante el
  periodo, de modo que el conteo de acciones reportado antes de la división y la
  serie de precios quedan expresados en unidades distintas.
- **Días sin precio frente a días sin tasa**: el mercado accionario y la
  publicación de la tasa libre de riesgo no comparten calendario; hay festivos
  en que existe uno y no el otro.
- **Reexpresiones contables**: la misma métrica del mismo periodo publicada dos
  veces con valores distintos.
- **Valores imposibles**: deuda negativa, acciones en circulación igual a cero,
  precio nulo o patrimonio negativo.
- **Descarga interrumpida**: corte de red o del proceso a mitad de la descarga,
  dejando datos parciales en disco.
- **Fuente que rechaza las peticiones**: la fuente de datos contables bloquea o
  limita el acceso y devuelve errores en lugar de datos.
- **Dato duplicado para la misma fecha**: la misma empresa y fecha aparece dos
  veces en una serie descargada.

## Requisitos *(obligatorio)*

### Requisitos funcionales

- **FR-001**: El sistema DEBE producir, para cada empresa del universo y cada
  día hábil del periodo, el valor de mercado del patrimonio, el punto de default
  y la tasa libre de riesgo correspondiente a ese día.
- **FR-002**: El sistema DEBE calcular el punto de default como la deuda de
  corto plazo más la mitad de la deuda de largo plazo vigentes en esa fecha.
- **FR-003**: El sistema DEBE registrar, para cada dato contable, la fecha en
  que se publicó, además de la fecha de cierre del periodo al que corresponde.
- **FR-004**: El sistema NO DEBE usar un dato contable en ninguna fecha anterior
  a su fecha de publicación.
- **FR-005**: El sistema DEBE mantener vigente el último dato contable publicado
  hasta que se publique uno más reciente.
- **FR-006**: Cuando una métrica del mismo periodo haya sido republicada con un
  valor distinto, el sistema DEBE usar la versión disponible en cada fecha y
  dejar constancia de cuál usó.
- **FR-007**: El sistema DEBE reconstruir todos los datos desde cero con un solo
  comando, sin pasos manuales.
- **FR-008**: El sistema NO DEBE versionar los datos descargados en el control
  de versiones.
- **FR-009**: El sistema DEBE identificarse ante la fuente de datos contables
  con un dato de contacto leído de la configuración local del entorno, nunca
  escrito en el código.
- **FR-010**: El sistema DEBE respetar un máximo de 10 peticiones por segundo
  contra la fuente de datos contables.
- **FR-011**: Ante un error de la fuente, un dato ausente o un dato incompleto,
  el sistema DEBE informarlo de forma explícita y NO DEBE sustituirlo por un
  valor sintético, interpolado o cacheado sin dejar registro.
- **FR-012**: El sistema DEBE distinguir un día sin observación de un día con
  valor cero, y nunca representar el primero como el segundo.
- **FR-013**: El sistema DEBE rechazar y reportar valores imposibles: deuda
  negativa, acciones en circulación menores o iguales a cero, y precio menor o
  igual a cero.
- **FR-014**: El sistema DEBE eliminar duplicados de la misma empresa y fecha
  dentro de una serie, conservando una sola observación y dejando registro.
- **FR-015**: El sistema DEBE producir un resumen de cobertura por empresa con
  el porcentaje de días cubiertos, el primer y último día disponibles, y los
  periodos sin dato de deuda.
- **FR-016**: El sistema DEBE marcar como no apta para el modelo a toda empresa
  que no alcance la cobertura mínima exigida, e informar el motivo, en lugar de
  descartarla silenciosamente.
- **FR-017**: El sistema DEBE permitir ejecutar la descarga sobre un subconjunto
  reducido de empresas, para poder probarlo sin descargar el universo completo.
- **FR-018**: Una descarga interrumpida NO DEBE dejar datos que parezcan
  completos; al reanudar, el sistema DEBE poder continuar o rehacer sin producir
  registros duplicados.
- **FR-019**: El sistema DEBE almacenar la tabla de ratings crediticios y la de
  eventos de estrés en el control de versiones, y cada registro DEBE incluir su
  fuente pública y la fecha de consulta.
- **FR-020**: El sistema DEBE validar que toda empresa del universo tiene
  calificación asociada y que ningún registro de rating o evento carece de
  fuente o de fecha de consulta.
- **FR-021**: El universo DEBE estar formado por 30 empresas no financieras —se
  excluyen bancos y aseguradoras— divididas en dos grupos declarados:
  - **Grupo base** (~22 empresas): seleccionadas por una regla escrita **antes**
    de observar resultados: pertenencia al S&P 500, cinco años completos de
    historia y reparto por categoría de calificación crediticia.
  - **Grupo de estrés** (~8 empresas): incluidas deliberadamente por haber
    atravesado un episodio de deterioro crediticio en el periodo, para que los
    estudios de evento tengan eventos que estudiar.

  Cada empresa DEBE quedar etiquetada con su grupo y con el motivo de su
  inclusión. Los resultados de validación ordinal y los de estudio de evento
  DEBEN poder calcularse por separado para cada grupo.
- **FR-022**: Para cada empresa del universo, el sistema DEBE registrar la
  calificación crediticia vigente y **todo cambio de calificación ocurrido
  dentro del periodo de cinco años**, con su fecha, la agencia, la fuente
  pública y la fecha de consulta. Cuando una empresa no haya tenido cambios en
  la ventana, DEBE constar explícitamente que no los tuvo, para distinguir
  "sin cambios" de "no consultado".
- **FR-023**: El valor de mercado del patrimonio DEBE calcularse con el precio
  de cierre **no ajustado por dividendos**, mientras que la volatilidad del
  patrimonio DEBE calcularse con la serie de precios **ajustada por dividendos**
  (retorno total). Ambas series provienen de la misma descarga.
- **FR-024**: El conteo de acciones en circulación DEBE expresarse en la misma
  base de división de acciones que la serie de precios, aplicando a cada dato
  contable el factor acumulado de las divisiones posteriores a su fecha de
  publicación. El sistema NO DEBE producir en el patrimonio ningún salto
  atribuible únicamente a una división de acciones.
- **FR-025**: El sistema DEBE registrar las divisiones de acciones detectadas en
  el periodo para cada empresa, con su fecha y su factor, de modo que el ajuste
  del requisito anterior sea auditable.

### Entidades clave

- **Empresa del universo**: entidad cotizada no financiera objeto del análisis.
  Atributos: identificador de mercado, identificador ante el regulador, nombre,
  sector, grupo al que pertenece (base o de estrés), motivo de su inclusión, y
  si es apta para el modelo según su cobertura de datos.
- **División de acciones**: fecha y factor de una división de acciones de una
  empresa, necesaria para expresar precios y acciones en la misma base.
- **Observación de precio**: precio de la acción de una empresa en un día
  concreto, con el volumen asociado.
- **Observación contable**: valor de una métrica de balance (deuda de corto
  plazo, deuda de largo plazo, acciones en circulación) para un periodo, con su
  fecha de cierre y su fecha de publicación.
- **Observación de tasa libre de riesgo**: tasa a un año para un día concreto.
- **Panel diario de insumos**: una fila por empresa y día con patrimonio, punto
  de default y tasa libre de riesgo, lista para alimentar el modelo.
- **Calificación crediticia**: calificación de una empresa por una agencia en
  una fecha, con fuente y fecha de consulta.
- **Evento de estrés**: episodio de deterioro crediticio de una empresa en una
  fecha, con descripción y fuente.
- **Informe de cobertura**: resultado de la auditoría por empresa, con días
  cubiertos, rango de fechas y faltantes.

## Criterios de éxito *(obligatorio)*

### Resultados medibles

- **SC-001**: El panel diario cubre las 30 empresas del universo y, en las
  empresas aptas, al menos el 95 % de los días hábiles del periodo de 5 años con
  los tres insumos presentes a la vez.
- **SC-002**: Borrar la carpeta de datos y volver a generarla reproduce el mismo
  panel, con un solo comando y sin intervención manual.
- **SC-003**: El 100 % de las observaciones contables del panel tiene fecha de
  publicación anterior o igual a la fecha de la fila, verificado por una prueba
  automática.
- **SC-004**: Cero valores rellenados en silencio: todo dato ausente figura como
  ausente, y el resumen de cobertura reporta su cantidad por empresa.
- **SC-005**: El 100 % de los registros de ratings y de eventos de estrés cita
  su fuente pública y su fecha de consulta.
- **SC-006**: La descarga completa del universo termina en menos de 60 minutos
  en una conexión doméstica, sin que la fuente de datos contables bloquee el
  acceso por exceso de peticiones.
- **SC-007**: Las pruebas automáticas cubren los diez casos límite listados y
  pasan en su totalidad.
- **SC-008**: En las empresas que dividieron sus acciones durante el periodo, el
  patrimonio no presenta ningún salto atribuible a la división: verificado por
  una prueba automática sobre al menos un caso real de división.

## Supuestos

- **Fuentes ya decididas**: el proyecto usa precios de mercado de un proveedor
  público gratuito, datos contables de la API pública del regulador
  estadounidense, y la tasa libre de riesgo del banco central vía descarga
  pública. Ninguna requiere credenciales de pago. Esta decisión está fijada en
  la constitución y no se revisa en esta fase.
- **Periodo**: los últimos 5 años contados desde la fecha de ejecución.
- **Calendario**: se toman como días hábiles los días en que cotizó el mercado
  estadounidense; la tasa libre de riesgo se arrastra desde su última
  publicación en los días en que no se publica.
- **Horizonte y método**: el punto de default, el horizonte de un año y el resto
  del método están definidos en el README y no se redefinen aquí.
- **Almacenamiento**: los datos se guardan localmente en un formato que preserve
  los tipos y las fechas, en una carpeta excluida del control de versiones.
- **Cobertura mínima**: se considera apta la empresa que supera el 95 % de días
  cubiertos; por debajo se marca como no apta y la decisión de excluirla o no la
  toma el analista.
- **Recopilación manual**: los ratings y los eventos de estrés se introducen a
  mano una sola vez y se mantienen en el repositorio; no se descargan
  automáticamente.
- **Sesgo de supervivencia**: el universo se construye sobre empresas que siguen
  cotizando, de modo que excluye por construcción a las que quebraron o fueron
  retiradas de bolsa. El sesgo no se puede eliminar con fuentes públicas
  gratuitas y DEBE declararse en las limitaciones del README.
- **Sobremuestreo declarado**: el grupo de estrés se elige a propósito porque un
  estudio de evento necesita eventos. Por eso los dos grupos se analizan por
  separado y nunca se presenta el resultado conjunto como si la muestra fuera
  aleatoria.
- **Base de las divisiones de acciones**: la serie de precios se toma ya
  expresada en la base vigente al final del periodo, mientras que los datos
  contables se publican en la base vigente en su momento; el ajuste del factor
  acumulado corrige esa diferencia.
- **Un solo usuario**: el proyecto lo ejecuta su autor en su equipo; no hay
  requisitos de concurrencia ni de servicio en línea.
- **Dependencia de terceros**: las fuentes son externas y pueden cambiar de
  formato, limitar el acceso o dejar de publicar una métrica. La fase asume que
  esos fallos se reportan, no que se puedan evitar.
