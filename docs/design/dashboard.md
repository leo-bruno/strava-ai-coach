# Dashboard Runner Coach

La referencia visual y de interacción es el prototipo [Stride](dashboard-prototype.html). Inicio la reproduce con Streamlit Custom Components v2 inline, usando sus HTML, CSS y JavaScript como punto de partida.

## Inicio de demostración

- Conserva la navegación lateral del prototipo, encabezado, cuatro tarjetas de resumen, gráfico semanal/mensual, agenda de siete días, últimas carreras, panel de Coach y vista de entrenamiento con pestañas.
- Los valores 37/50 km, 128,4 km, 5:24 min/km, 11 h 33 min, 16 carreras, las actividades, el plan, los gráficos y las respuestas de chat son datos de ejemplo del prototipo. La página los identifica como demostración.
- «Registrar carrera» solo añade un registro de demostración y lo guarda en el `localStorage` del navegador. No escribe en Strava ni en el estado Python.
- El chat, la semana, las pestañas de plan y los gráficos son interacciones locales con respuestas predefinidas. No consultan Coach ni OpenAI.
- Inicio oculta siempre la barra lateral nativa y no ofrece un puente explícito a las rutas reales. La demo no emite triggers a Python ni lee o transforma resúmenes Strava.

## Secciones reales

- Estadísticas y Coach conservan las páginas Streamlit, la navegación nativa entre secciones reales y sus flujos existentes. La rail del prototipo solo cambia entre vistas de demostración.
- Strava mantiene su conexión OAuth, preview, análisis individual y resumen semanal manual. Inicio no solicita datos, no inicia fetch y no modifica las claves de sesión de Strava.
- Coach mantiene su flujo independiente y sus acciones explícitas. La conversación de muestra del prototipo no envía preguntas al Coach real.
- La implementación inline no añade dependencias ni build frontend. CCv2 usa un Shadow DOM y el JavaScript busca elementos bajo `parentElement`; la demo no emite eventos de navegación a Python.
