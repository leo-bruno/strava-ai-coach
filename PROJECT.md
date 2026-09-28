🏃 Strava AI Coach

Plataforma de análisis de entrenamiento basada en datos de Strava, diseñada para evolucionar hacia un entrenador inteligente capaz de entender el historial del atleta, detectar patrones y ayudar a tomar decisiones de entrenamiento.

⸻

🎯 Visión del producto

Strava AI Coach busca transformar los datos históricos y actuales de entrenamiento en información útil para el atleta.

El sistema se está construyendo por capas:

Strava → Analytics → Trends → Insights → Coach

Cada capa tiene una responsabilidad diferente.

Analytics

Calcula y describe objetivamente lo ocurrido.

Ejemplos:

* Ritmo medio de un entrenamiento.
* Kilómetros realizados durante una semana.
* Número de sesiones.
* Distribución de tipos de entrenamiento.

Trends

Compara períodos y permite entender cómo evolucionan las métricas a medio plazo.

Ejemplo:

24 km → 27 km → 30 km → 33 km durante las últimas cuatro semanas.

Insights

Detecta automáticamente hechos y patrones relevantes a partir de Analytics y Trends.

Ejemplo:

El volumen semanal ha aumentado un 37,5 % durante las últimas cuatro semanas.

Los Insights describen lo que está ocurriendo, pero no prescriben qué hacer.

Coach

Interpreta toda la información anterior teniendo en cuenta el contexto del atleta.

Ejemplo:

El volumen lleva varias semanas aumentando. Teniendo en cuenta tu carga reciente y tu objetivo, esta semana podría ser conveniente reducirlo.

Esta separación es una decisión fundamental del producto:

Analytics calcula → Trends compara → Insights detecta → Coach interpreta y recomienda.

⸻

🗺️ Estado del producto

Área	Estado
Strava Integration	🟡 Parcial
Individual Analytics	🟡 Parcial
Weekly Analytics V1	🚧 En desarrollo
Trends	⏳ Pendiente
Insights	⏳ Pendiente
AI Coach	⏳ Pendiente
Training Planning	⏳ Futuro
UI	⏳ Futuro

⸻

📍 Current Focus

Weekly Analytics V1

Estamos construyendo la capacidad de entender una semana completa de entrenamiento, en lugar de analizar únicamente sesiones individuales.

La estrategia de desarrollo es incremental:

1. ✅ Definir correctamente qué actividades pertenecen a una semana.
2. ✅ Calcular distancia semanal.
3. ✅ Calcular número de entrenamientos.
4. 🚧 Completar el modelo y métricas de volumen semanal.
5. ⏳ Añadir estructura e intensidad.
6. ⏳ Añadir recuperación y densidad de entrenamiento.
7. ⏳ Validar Weekly Analytics con datos reales.
8. ⏳ Construir comparaciones entre semanas.

No se implementará Weekly Analytics completo de una sola vez.

Cada nueva capacidad debe seguir el ciclo:

Definir → Implementar → Tests → Validar → Continuar

⸻

🏗️ Lo que tenemos construido

1. Strava Integration 🟡

Existe una integración funcional con la API de Strava.

Implementado

* Generación de URL de autorización.
* Scopes read y activity:read_all.
* Intercambio del authorization code.
* Refresh de access tokens.
* Persistencia local del refresh token.
* Protección del fichero de token con permisos del propietario.
* Obtención del atleta autenticado.
* Obtención de una página de actividades.
* Parámetros before, after, page y per_page.
* Validación y mapeo de actividades.

Pendiente

Todavía no existe una experiencia completa de conexión con Strava.

Entre otras cosas faltan:

* Callback integrado en la aplicación.
* Paginación automática.
* Gestión de rate limits.
* Retries.
* Recuperación automática ante expiración durante una operación.
* Sincronización/persistencia de actividades.
* Obtención integrada de actividad detallada y laps.

⸻

2. Modelo de dominio

Actualmente existen modelos inmutables para representar:

* Activity
* TrainingLap
* TrainingAnalysis
* Tipos de entrenamiento

Los datos opcionales ausentes permanecen como None.

Los laps mantienen su orden original.

Todavía no existe un modelo agregado como WeeklyAnalysis.

⸻

3. Individual Analytics 🟡

Podemos construir un análisis estructurado de una carrera cuando disponemos de sus datos detallados.

Actualmente incluye:

* Identidad de la actividad.
* Fecha.
* Distancia.
* Moving time.
* Ritmo medio.
* Frecuencia cardíaca media.
* Frecuencia cardíaca máxima.
* Cadencia.
* Desnivel positivo.
* Laps.
* Ritmo de cada lap.
* FC y cadencia de cada lap cuando están disponibles.
* Tipo de entrenamiento.

El ritmo se calcula en segundos por kilómetro.

Los valores ausentes no se sustituyen artificialmente por 0.

Gap técnico pendiente

Individual Analytics todavía no está conectado directamente con la recuperación de actividades detalladas de Strava.

Actualmente:

Datos detallados proporcionados por caller → TrainingAnalysis

El flujo deseado será:

Activity ID → Strava detailed activity/laps → TrainingAnalysis

Por tanto, Individual Analytics existe como capacidad, pero todavía no constituye un flujo end-to-end completo.

⸻

4. Clasificación de entrenamientos

Actualmente existen seis categorías:

Tipo

Easy

Long

Tempo

Intervals

Race

Other

La clasificación actual es determinista y basada en el nombre del entrenamiento.

Reconoce, entre otros:

* Carrera fácil
* Carrera larga
* Tempo
* Repeticiones
* Variantes
* Serie descendente
* Millas fragmentadas
* Alternos
* Contrarreloj

La normalización contempla diferencias de mayúsculas/minúsculas, Unicode y espacios.

Decisión importante

Actualmente no intentamos inferir el tipo de entrenamiento mediante IA ni mediante ritmo, frecuencia cardíaca, distancia o estructura de laps.

Si no existe suficiente información determinista, se utiliza:

Other

Esto evita inventar información que los datos no permiten asegurar.

⸻

5. Weekly Analytics 🚧

Weekly Analytics ya está iniciado.

Definición de semana

Las semanas corresponden al calendario local del atleta:

Lunes 00:00 → siguiente lunes 00:00

Los límites se calculan utilizando la timezone del atleta y posteriormente se convierten a UTC.

Esto permite manejar correctamente:

* Cambios de horario.
* DST.
* Cambios de año.
* Semanas que no duran exactamente 168 horas.

La frontera inicial es inclusiva y la final exclusiva.

Métricas implementadas

Weekly Distance

Suma la distancia de las actividades Run pertenecientes a la semana.

Weekly Activity Count

Cuenta las actividades Run pertenecientes a la semana.

Una carrera con distancia cero continúa contando como actividad.

Actualmente TrailRun no se incluye.

Todavía pendiente

Entre otras capacidades:

* Duración semanal.
* Ritmo agregado.
* Distribución por tipo de entrenamiento.
* Estructura Easy / Quality.
* Tirada larga.
* Densidad de entrenamiento.
* Días de descanso.
* Sesiones consecutivas.
* Comparaciones entre semanas.
* Tendencias.

⸻

🧪 Validación

Automated Tests

Actualmente:

346 tests passing

La suite cubre, entre otros:

* Authentication.
* Strava client.
* Activity mapping.
* Pace.
* Training classification.
* Training analysis.
* Weekly calculations.
* Domain models.
* Casos límite.
* Manejo de datos ausentes o incorrectos.
* Límites temporales y cambios DST.

Existe además un integration test que conecta token refresh con athlete retrieval utilizando HTTP mockeado.

Actualmente no existen:

* Live-service tests.
* Browser E2E.
* LLM evaluation tests.
* CI workflows.

⸻

Validación con entrenamientos reales

Existe además una utilidad local de validación offline.

Se utilizó con datos reales exportados y produjo:

* 55 actividades analizadas correctamente
* 0 fallos
* 218 laps preservados

Se comprobaron entrenamientos con diferentes estructuras, incluyendo rodajes fáciles, tiradas largas, tempo, repeticiones e intervalos.

Esta validación es independiente de la suite automatizada y no implica que exista todavía sincronización live completa con Strava.

⸻

🧠 Principios de desarrollo

1. Desarrollo incremental

No construiremos grandes bloques completos mediante un único prompt.

Preferimos:

Feature pequeña → implementación → tests → validación → siguiente feature

Esto permite entender y controlar el comportamiento del sistema.

⸻

2. Datos antes que IA

No utilizaremos IA para resolver problemas que puedan resolverse correctamente mediante cálculos deterministas.

Primero construiremos una base sólida de datos y Analytics.

La IA llegará posteriormente para interpretar contexto, no para sustituir cálculos fiables.

⸻

3. No inventar información

Si Strava no proporciona un dato y no puede calcularse de forma fiable, se mantiene como desconocido.

Ejemplo:

heart_rate = None

en lugar de:

heart_rate = 0

⸻

4. Validar con entrenamientos reales

Los unit tests no son suficientes.

Las capacidades relevantes de Analytics deben contrastarse también con actividades reales para comprobar que los resultados tienen sentido desde el punto de vista del entrenamiento.

⸻

🔭 Roadmap

La evolución prevista actualmente es:

Foundation

Strava Integration

↓

Individual Analytics

Activity → TrainingAnalysis

↓

Weekly Analytics ← 📍 CURRENT

Activities → WeeklyAnalysis

↓

Trends

WeeklyAnalysis[] → evolución temporal

↓

Insights

Analytics + Trends → hechos relevantes

↓

AI Coach

Athlete context + Analytics + Insights + Goal → interpretación y recomendaciones

↓

Training Planning

Creación y adaptación progresiva de planes de entrenamiento.

⸻

💡 Insights previstos

Cuando Analytics y Trends estén suficientemente desarrollados, Insights podrá detectar automáticamente hechos como:

* Aumento o reducción de volumen.
* Evolución de la tirada larga.
* Parones y regresos al entrenamiento.
* Concentración de sesiones exigentes.
* Sesiones exigentes consecutivas.
* Cambios importantes en frecuencia de entrenamiento.
* Cambios en proporción Easy / Quality.
* Cambios de rendimiento en entrenamientos comparables.
* Datos anómalos o potencialmente poco fiables.

Ejemplo válido:

Las últimas cuatro semanas fueron 24 → 27 → 30 → 33 km (+37,5 %).

Ejemplo que no corresponde a Insights:

Deberías hacer una semana de descarga.

Esta segunda afirmación requiere interpretación y pertenece al Coach.

⸻

⚠️ Gaps técnicos conocidos

No todos estos gaps necesitan resolverse inmediatamente.

Actualmente conocemos al menos:

* Individual Analytics no está conectado end-to-end con detailed activities/laps de Strava.
* No existe paginación automática de actividades.
* No existe persistencia/sincronización de actividades.
* No existe deduplicación.
* No existe un application entry point real.
* src/main.py está vacío.
* src/ai todavía está vacío.
* No existe UI.
* No existe CI.
* No existe todavía WeeklyAnalysis.
* No existen Trends.
* No existen Insights.
* No existe Coach.

Estos elementos deben priorizarse según las necesidades del roadmap, no necesariamente por su orden técnico.

⸻

➡️ Próximo paso

Weekly Analytics V1

Continuar de forma incremental a partir de las dos métricas semanales existentes:

* Weekly distance ✅
* Weekly activity count ✅

El siguiente objetivo es definir y ampliar el modelo semanal, antes de avanzar hacia estructura/intensidad y recuperación/densidad.

El gap de detailed Strava activity → TrainingAnalysis permanece documentado y deberá cerrarse antes de considerar Individual Analytics completamente integrado.

⸻

Last updated: 28 September 2026