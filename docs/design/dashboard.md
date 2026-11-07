# Dashboard de Strava AI Coach

Diseño del boceto aprobado por el usuario el 7 de noviembre de 2026. [Abrir el prototipo](dashboard-prototype.html). La referencia visual original es [Running Dashboard, de Pickolab Studio](https://dribbble.com/shots/27490588-Running-Dashboard).

## Inicio

- En escritorio, barra lateral plegable con un botón junto a la marca. La primera fila reúne progreso y ritmo medio a la izquierda, entrenamientos al centro y agenda a la derecha. En pantallas estrechas los paneles se apilan.
- El progreso semanal muestra número de semana o rango de fechas, sesiones realizadas frente a las previstas y kilómetros realizados frente a los previstos. El indicador utiliza un arco abierto de 240°. La parte turquesa representa el porcentaje del arco visible y el resto queda gris. Las sesiones pautadas por tiempo se presentan en minutos cuando no tienen distancia objetivo.
- En Entrenamientos, un tick verde identifica las sesiones completadas. Las pendientes muestran una ficha con día y fecha, como «Dom 08».
- La Agenda semanal tiene un selector para consultar semanas pasadas y futuras. Cambiar la semana de la agenda permite explorar otras sesiones mientras el progreso del inicio sigue mostrando la semana actual.
- Rendimiento ocupa un panel ancho junto al Coach. La composición se conserva como referencia. Las métricas y el diseño detallado de Rendimiento quedan pendientes.

## Mi plan y detalle

- Mi plan comienza plegado y se abre en la semana actual. El selector permite recorrer semanas pasadas y futuras.
- Cada sesión ocupa una fila. **Previsto** y **Realizado** aparecen en la misma línea cuando hay espacio. En pantallas estrechas, el texto puede ajustarse. Si falta la actividad de una sesión pasada, se muestra «Sin actividad vinculada».
- El nombre de cada sesión abre una pantalla de detalle. Volver a Mi plan restaura la semana seleccionada y el desplegable abierto.
- La tipografía del boceto es Manrope con respaldo del sistema. Los selectores usan texto compacto y una flecha separada del borde. Los enlaces van sin subrayado, incluso al pasar el cursor, y deben conservar un foco visible al navegar con teclado.

## Uso durante el desarrollo

- **Orquestador.** Adjuntar esta especificación y el prototipo al encargo cuando se autorice un incremento de UI.
- **Arquitecto.** Contrastar el diseño con el estado real descrito en PROJECT.md. Definir el alcance y la validación del incremento, incluidos escritorio, móvil y navegación por teclado. Confirmar los criterios para vincular sesiones previstas con actividades reales si forman parte del alcance.
- **Desarrollador.** Usar el prototipo como referencia visual y esta especificación como referencia de comportamiento. Verificar los controles, la navegación entre semanas y el retorno desde el detalle según los criterios del incremento.

El prototipo usa datos ficticios. La aprobación cubre el diseño del boceto. Los datos, la vinculación con Strava y la integración con Streamlit se definen en sus respectivos incrementos.
