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

El modelo mínimo WeeklyAnalysis y su construcción a partir de actividades suministradas ya están implementados y probados. Las métricas de volumen semanal aún no están completas; Weekly Analytics V1 continúa en desarrollo.

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
* WeeklyAnalysis
* Tipos de entrenamiento

Los datos opcionales ausentes permanecen como None.

Los laps mantienen su orden original.

WeeklyAnalysis representa la fecha del lunes local del atleta, la distancia semanal en metros, el número de actividades Run y running_moving_time_seconds. Es un modelo inmutable, sin lógica de cálculo ni validación automática, cuyos cuatro datos obligatorios debe proporcionar quien lo construye.

La identidad de la semana es una fecha local; el modelo no almacena límites UTC ni timezone. La timezone sigue siendo una entrada de los cálculos semanales.

Analytics ya puede construir este modelo a partir de actividades suministradas, una fecha/hora de referencia con timezone y la timezone del atleta.

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

Weekly Moving Time

running_moving_time_seconds suma exactamente los segundos en movimiento de las mismas actividades Run seleccionadas por distancia y conteo. Es un entero obligatorio; una semana sin carreras devuelve 0 y una carrera válida con tiempo 0 aporta 0. Analytics recibe Activity válidos: los valores ausentes o inválidos de Strava se rechazan en el mapper, sin estimarlos ni sustituirlos. La asignación se realiza por start_date, sin deduplicar ni repartir actividades entre semanas.

Modelo semanal

WeeklyAnalysis permite representar las tres métricas existentes junto con la fecha del lunes local. Conserva resultados cero, incluida distancia cero con un número positivo de actividades.

El flujo Activities → WeeklyAnalysis ya está disponible sobre actividades suministradas. Reutiliza la definición de semana local y los cálculos de distancia, conteo y tiempo en movimiento. La fecha del lunes se obtiene convirtiendo el límite inicial UTC a la timezone del atleta antes de extraer la fecha.

Una entrada sin carreras coincidentes produce un análisis con la fecha de la semana y las tres métricas a cero. Las referencias sin timezone se rechazan, incluso con una lista vacía. Los resultados describen los datos suministrados y no garantizan que el historial semanal esté completo ni deduplicado. Este flujo no recupera actividades de Strava.

Todavía pendiente

Entre otras capacidades:

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

383 tests passing

El contrato de WeeklyAnalysis cuenta con 8 tests, el cálculo de tiempo semanal con 18 y la construcción Activities → WeeklyAnalysis con 11. Junto con los 41 tests existentes de límites, distancia y conteo, pasan los 78 tests de Weekly Analytics. Los 39 tests del mapper también pasan. La suite completa configurada pasa con 383 tests y cobertura del 97 %; el nuevo cálculo y el constructor semanal alcanzan el 100 %. Los 7 tests adicionales de la utilidad local de captura pasan por separado.

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

Validación offline de Weekly Analytics

El flujo Activities → WeeklyAnalysis se contrastó con el mismo export real: 55 actividades Run, de las cuales 52 pertenecen a 20 semanas completas del intervalo declarado, del 4 de mayo al 20 de septiembre de 2026. Las dos semanas parciales de los extremos se analizaron por separado. La fecha semanal, distancia y conteo coincidieron con una agrupación independiente por fechas locales y sumas decimales de los datos fuente en las 22 semanas. Los 57 tests de Weekly Analytics también pasan.

La timezone utilizada fue Europe/Madrid, coherente con las 55 fechas locales, aunque el export no identifica la zona IANA del atleta. Las semanas completas suman 396,9011 km y 52 actividades. Se conservó un probable duplicado de subida del 4 de mayo y cuatro semanas sin registros. La validación confirma los cálculos sobre la muestra, no la integridad del historial de Strava ni que las semanas sin registros fueran de descanso. El informe y el detalle reproducible se encuentran en local_validation/weekly_history_report.md y local_validation/weekly_history_results.json.

Una utilidad manual separada, local_validation/capture_strava_history.py, obtuvo una nueva captura el 28 de septiembre de 2026 para el intervalo local Europe/Madrid [20 abril, 5 octubre). Reutiliza StravaClient y recorre páginas hasta una vacía, sin incorporar paginación a producción. Recuperó 89 actividades, incluidas 59 Run con 468,5869 km. Las 24 semanas coinciden con un cálculo independiente; la última permanece abierta al extraer. Tres carreras de abril y la del 26 de septiembre explican íntegramente los 40,5338 km adicionales respecto al export anterior; sus 55 carreras permanecen sin cambios en los campos comparados. No hay TrailRun ni VirtualRun. En aquella validación pasaron los 362 tests existentes y 7 tests de la utilidad; esta captura manual no equivale a sincronización ni a un live-service test automatizado.

La reconciliación de distancia queda cerrada el 29 de septiembre de 2026 sin defecto encontrado en Weekly Analytics. La suma exacta de las actividades API y la suma exacta de sus totales semanales coinciden en 468,5869 km; las 59 Run quedan asignadas a sus semanas sin pérdidas ni duplicación durante la agregación. La diferencia es de 86,9 m respecto a los 468,5 km del total general de Strava y de 96,9 m respecto a los 468,49 km que suman sus puntos semanales visibles. Son comparaciones distintas, no un error aritmético anterior. Los valores semanales visibles no siguen uniformemente ni redondeo convencional a dos decimales ni truncamiento. La diferencia residual queda documentada como una diferencia no explicada de presentación/precisión respecto a la UI de Strava, no como un error demostrado de nuestros cálculos. La UI no proporciona precisión suficiente para determinar su algoritmo interno.

Decisión de producto: Weekly Analytics utiliza los valores exactos proporcionados por la API para calcular sus métricas; no intentaremos reproducir la presentación interna de Strava ni ajustar los cálculos para igualar sus valores visibles. El cierre no elimina las limitaciones de la captura ni declara completa Weekly Analytics V1. El detalle se conserva en local_validation/strava_reconciliation_report.md.

La validación offline de running_moving_time_seconds se completó sobre la captura del 28 de septiembre: 89 actividades, 59 Run y 24 semanas. La suma independiente por semana local coincide exactamente en todas las semanas: 186774 segundos en total, sin diferencias y sin modificar la captura. Cinco semanas sin registros Run producen 0; la última seguía abierta al extraer. Los valores fuente ya están normalizados desde moving_time por el mapper. Esta comprobación no garantiza integridad del historial ni demuestra descanso en semanas sin registros. Informe y reproducción: local_validation/weekly_moving_time_report.md y local_validation/validate_weekly_moving_time.py.

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

Activities → WeeklyAnalysis (disponible sobre actividades suministradas; Weekly Analytics V1 sigue en desarrollo)

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
* No existen Trends.
* No existen Insights.
* No existe Coach.

Estos elementos deben priorizarse según las necesidades del roadmap, no necesariamente por su orden técnico.

⸻

➡️ Próximo paso

Weekly Analytics V1

Continuar de forma incremental a partir de las tres métricas semanales existentes:

* Weekly distance ✅
* Weekly activity count ✅
* running_moving_time_seconds ✅
* Modelo mínimo WeeklyAnalysis ✅
* Activities → WeeklyAnalysis sobre actividades suministradas ✅

La validación offline del flujo semanal actual ya se ha realizado con una muestra real y contraste independiente de semana local, distancia y conteo, y se ha repetido con una captura actualizada. La reconciliación de distancia está cerrada sin defecto encontrado en Weekly Analytics; la diferencia residual de presentación/precisión respecto a la UI de Strava no bloquea el siguiente incremento. El incremento running_moving_time_seconds está implementado, probado y validado offline como suma del tiempo en movimiento de las mismas actividades Run. El siguiente paso es cerrar el alcance de volumen semanal V1 antes de acordar otro incremento; no se declara completa Weekly Analytics V1. Estructura, intensidad, densidad, ritmo agregado, tirada larga, días de descanso y Trends permanecen fuera de este incremento.

El gap de detailed Strava activity → TrainingAnalysis permanece documentado y deberá cerrarse antes de considerar Individual Analytics completamente integrado.

⸻

Last updated: 29 September 2026
