# Lista de verificación de calidad — Fase 1: Descarga y preparación de datos

**Propósito**: validar que la especificación está completa antes de pasar a la planificación
**Creada**: 2026-11-25
**Última revisión**: 2026-11-25 (segunda iteración, tras resolver las aclaraciones)
**Especificación**: [spec.md](../spec.md)

## Calidad del contenido

- [x] Sin detalles de implementación (lenguajes, librerías, APIs concretas)
- [x] Centrada en el valor para el usuario y la necesidad del proyecto
- [x] Escrita de forma comprensible sin conocer el código
- [x] Todas las secciones obligatorias completadas

## Completitud de los requisitos

- [x] No quedan marcadores [NEEDS CLARIFICATION]
- [x] Los requisitos son verificables y sin ambigüedad
- [x] Los criterios de éxito son medibles
- [x] Los criterios de éxito no dependen de una tecnología concreta
- [x] Los escenarios de aceptación están definidos para las tres historias
- [x] Los casos límite están identificados (diez casos)
- [x] El alcance está acotado: 30 empresas en dos grupos declarados (base y de
      estrés), cinco años, cuatro insumos de datos
- [x] Supuestos y dependencias identificados

## Preparación de la fase

- [x] Cada requisito funcional tiene criterios de aceptación claros
- [x] Las historias de usuario cubren los flujos principales
- [x] La fase cumple los resultados medibles de los criterios de éxito
- [x] No se filtran detalles de implementación en la especificación

## Notas

**16 de 16 puntos cumplidos.** La especificación está lista para `/speckit-plan`.

Decisiones tomadas en la primera revisión:

1. **Universo en dos grupos** (FR-021): ~22 empresas por regla documentada y ~8
   de estrés incluidas a propósito. Evita presentar una muestra sobremuestreada
   como si fuera aleatoria. El sesgo de supervivencia queda declarado.
2. **Historial de ratings dentro de la ventana** (FR-022), no solo la
   calificación vigente. Registrar el historial únicamente de las empresas ya
   marcadas como de estrés habría condicionado el estudio de evento a su propio
   resultado.
3. **Dos series de precios** (FR-023): sin ajustar por dividendos para el
   patrimonio, ajustada para la volatilidad. Sin coste extra, porque ambas
   llegan en la misma descarga.
4. **Consistencia de divisiones de acciones** (FR-024, FR-025): requisito
   añadido durante la revisión. Los precios vienen en la base de splits vigente
   al final del periodo y los datos contables en la base de su momento; sin
   corregirlo, el patrimonio de una empresa que dividió 10:1 queda diez veces
   mal en todo el tramo anterior.

Lo único que queda abierto es la **lista nominal de las 30 empresas**, que se
fija en `/speckit-clarify`. El criterio de selección ya está escrito en FR-021,
que es lo que la especificación debe garantizar.
