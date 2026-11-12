# Dashboard de Strava AI Coach

La referencia visual es el prototipo [Stride](dashboard-prototype.html), adaptado al patrón Streamlit y a los datos que el proyecto realmente tiene disponibles.

## Inicio

- La página conserva la composición del prototipo en todos los estados: navegación lateral, encabezado con acción principal, cuatro tarjetas, gráfico junto al módulo de entrenamiento y, debajo, las carreras recientes junto al panel de Coach. Usa controles y gráficos nativos de Streamlit.
- La primera tarjeta identifica que no hay un objetivo semanal configurado; no muestra denominador, porcentaje ni barra de progreso. Las otras tres muestran distancia Run, ritmo medio derivado de tiempo/distancia y tiempo en movimiento, todos del intervalo cargado. Sin datos, sus valores son guiones; los detalles explican por qué.
- El gráfico representa las siete semanas calendario completas consultadas con fecha de inicio. Antes de cargar datos, permanece visible con un estado vacío y sin puntos de ejemplo.
- El módulo de entrenamiento permanece visible y declara que no hay un plan conectado; no inventa calendario, sesiones futuras ni metas.
- El historial muestra hasta cinco actividades Run del intervalo consultado, ordenadas desde la más reciente. Sin datos, explica si falta conectar Strava o cargar el intervalo. Un resultado cero explica que no se devolvieron carreras Run, sin inferir inactividad ni descanso.
- El panel visual de Coach permanece visible en todos los estados y abre la ruta existente; no incluye una respuesta generada ni simula una conversación.
- «Actualizar datos de Strava» es la única acción en Inicio que consulta Strava. Solo aparece con una conexión vigente; la carga reutiliza la consulta manual existente, sus límites de paginación y su almacenamiento temporal por sesión.
- Sin conexión, datos semanales, carreras Run, metadatos de cobertura incompletos o token vencido, la interfaz explica el estado dentro del módulo afectado y conserva el resto de la composición. El intervalo, fecha de consulta, páginas y límites de cobertura se muestran junto al contenido disponible.
- Un cero describe los registros Run devueltos para ese intervalo y no demuestra inactividad ni descanso.

## Navegación y límites del producto

- La navegación conserva Inicio, Estadísticas y Coach. Estadísticas mantiene OAuth, la vista semanal, el preview y análisis individual existentes; Coach mantiene su flujo separado con las advertencias actuales.
- Se retiró la ruta de Mi plan porque el proyecto no tiene un backend de planificación. El módulo vacío de entrenamiento lo comunica sin incluir datos futuros o ficticios. No se muestran comparaciones mensuales ni respuestas de Coach simuladas.
- Actividades, resúmenes y datos derivados permanecen en la sesión de Streamlit. No se sincronizan ni se escriben cambios en Strava.

El prototipo HTML original incluye valores y respuestas de ejemplo para ilustrar el diseño. Es una referencia visual; esos valores no forman parte de la aplicación conectada.
