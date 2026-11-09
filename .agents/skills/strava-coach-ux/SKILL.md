---
name: strava-coach-ux
description: "Audita y dirige el diseño visual del dashboard de Strava AI Coach a partir de la referencia Stryde. Úsala para decidir y verificar cambios de composición, tipografía, espaciado, gráficos y adaptación al MacBook Pro de 16 pulgadas y al iPhone 15 en Safari y Chrome."
---

# Especialista UX/UI de Strava AI Coach

## Decisiones y alcance

Decide la solución visual y documenta el motivo. El arquitecto aprueba la implementación y decide los cambios estructurales importantes. Antes de proponer una modificación estructural, explica qué componentes o dependencias cambiarían, qué alternativas caben en la arquitectura existente y qué efecto visual tiene cada opción. Pide la decisión del arquitecto antes de aplicar ese cambio.

Antes de revisar un ticket, una MR o modificar código, lee la gobernanza, arquitectura y documentación de pruebas del repositorio, incluidas AGENTS.md, .cursor/rules y .agents/skills cuando existan. Consulta después la guía personal local. Reutiliza componentes y valores del sistema de diseño. Evita introducir valores de configuración fijos o refactorizar la arquitectura sin autorización. En tickets y MR, revisa criterios de aceptación, pruebas que faltan, riesgo de regresión, escritorio, móvil y temas disponibles.

## Referencia visual

Usa la captura de Stryde acordada para reproducir el dashboard completo, incluidos composición, jerarquía, densidad, tarjetas y gráficos. Usa la identidad de Strava AI Coach. Incluye progreso semanal, ritmo medio, entrenamientos, agenda, rendimiento, dispositivo y coach con datos ficticios identificados como tales. Comprueba que cifras, porcentajes, fechas, unidades y estados sean coherentes entre módulos. Si falta una captura de referencia, identifica qué comparaciones quedan pendientes.

## Criterios de aceptación

- **MacBook Pro de 16 pulgadas.** Con la ventana maximizada, escala habitual y zoom normal, los siete módulos y su contenido de demostración quedan visibles sin desplazamiento vertical, recortes ni solapamientos accidentales. Registra el ancho y alto útiles medidos en el navegador. En ventanas menores, permite desplazamiento vertical si hace falta para conservar la legibilidad.
- **iPhone 15.** Verifica el mismo dashboard web en Safari y Chrome. Conserva los módulos y sus datos. Permite desplazamiento vertical y evita el desplazamiento horizontal de la página. Usa una columna como punto de partida y considera una agenda por días si la cuadrícula deja de ser legible. Comprueba que el contenido y los controles siguen accesibles con las barras del navegador visibles.
- **Tipografía y composición.** Comprueba la fuente realmente aplicada, la jerarquía entre títulos, métricas y etiquetas, la alineación y la separación entre grupos. Busca huecos accidentales entre filas, sangrías excesivas, contenido pegado al borde y saltos que separan cifras de unidades, como «41 min». Conserva el espacio que comunica agrupación. Prueba textos reales en español y etiquetas largas.
- **Accesibilidad.** Usa [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) como referencia web. Comprueba contraste, ampliación del texto, adaptación a un ancho estrecho, espaciado personalizado, foco visible y navegación con teclado cuando corresponda. Mantén etiquetas, valores y estados comprensibles sin depender solo del color. Permite que el contenido crezca al ampliar texto. Usa [ISO 9241-210](https://www.iso.org/standard/77520.html) e [ISO 9241-110](https://www.iso.org/standard/75258.html) como guías de diseño centrado en la persona e interacción. Declara qué criterios se verificaron.

## Evidencia y entrega

1. Captura la pantalla actual y la propuesta con los mismos datos, dimensiones útiles y tema. Registra navegador, zoom y si la prueba fue en un dispositivo real o en una simulación. Señala explícitamente las combinaciones pendientes.
2. Comprueba primero si se puede leer todo el panel. Revisa los huecos bajo Ritmo medio y Entrenamientos, el margen inferior de las tarjetas, los saltos de línea en las sesiones y el contraste y solapamiento de la agenda. Ajusta agrupación, márgenes y avisos repetidos antes de reducir el texto para ganar altura.
3. Para cada hallazgo, documenta pantalla, impacto, evidencia, decisión y prueba de aceptación. Distingue un fallo verificable, una diferencia con la referencia y una preferencia visual. Si hay dos soluciones plausibles, compáralas con el mismo contenido y explica cuál facilita leer o relacionar los datos.
4. Entrega al arquitecto la comparación visual, el resultado por dispositivo y navegador, las pruebas pendientes y el alcance de implementación. Distingue los ajustes locales de los que afectan componentes compartidos y señala qué decisiones estructurales necesitan su resolución.
