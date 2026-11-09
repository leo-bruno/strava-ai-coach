# Dashboard de Strava AI Coach

Diseño del boceto aprobado por el usuario el 7 de noviembre de 2026. [Abrir el prototipo](dashboard-prototype.html). La referencia visual original es [Running Dashboard, de Pickolab Studio](https://dribbble.com/shots/27490588-Running-Dashboard).

## Inicio

- En escritorio, barra lateral plegable con un botón junto a la marca. La fila principal muestra Progreso, Ritmo medio, Entrenamientos y Agenda en ese orden cuando el ancho útil alcanza 1052 px. Las proporciones son 20:16:27:37, con anchos mínimos de 200/165/270/380 px y 12 px entre módulos. Entre 710 y 1051 px la fila se divide en dos: Progreso/Ritmo y Entrenamientos/Agenda. Por debajo de 710 px se apila. Rendimiento y Coach ocupan dos columnas desde 710 px y una por debajo; Mi plan aparece al final a ancho completo.
- El progreso semanal muestra número de semana o rango de fechas, sesiones realizadas frente a las previstas y kilómetros realizados frente a los previstos. El indicador utiliza un arco abierto de 240°. La parte turquesa representa el porcentaje del arco visible y el resto queda gris. Las sesiones pautadas por tiempo se presentan en minutos cuando no tienen distancia objetivo.
- Entrenamientos presenta cuatro sesiones en filas compactas, con fecha y tick verde para las realizadas. Una sola fila destaca la siguiente sesión pendiente con un fondo pastel e indicador fino; la sesión realizada más reciente se atenúa cuando hay una. La segunda línea solo muestra distancia y ritmo cuando los datos existen. El ritmo derivado se rotula como tal; una sesión basada solo en tiempo no recibe distancia ni ritmo inventados.
- La Agenda semanal tiene un selector para consultar semanas pasadas y futuras. Las cuatro sesiones se muestran en una cuadrícula 2×2 cuando el ancho interior alcanza 360 px; de lo contrario, se presentan en una lista. Cambiar la semana permite explorar otras sesiones mientras el progreso del inicio sigue mostrando la semana actual.
- Los datos ficticios comparten una misma fuente para Entrenamientos, Agenda, Mi plan y el resumen. El objetivo semanal sigue en 18 km: la sesión de técnica del sábado dura 20 min y no añade distancia al objetivo. En la semana anterior figura con 18 min realizados y distancia desconocida.
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
