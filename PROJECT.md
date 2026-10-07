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

La distancia Run observada aumentó durante tres transiciones semanales consecutivas, entre cuatro observaciones.

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
Weekly Analytics V1	✅ COMPLETE
Trends V1	✅ COMPLETE
Insights V1	✅ COMPLETE — tres Insights implementados y validados conjuntamente offline
AI Coach	⏳ Pendiente
Training Planning	⏳ Futuro
UI	⏳ Futuro

⸻

📍 Current Focus

Insights V1 — COMPLETE

Insights V1 está COMPLETE con Persistent Weekly Running Distance Increase, Persistent Weekly Running Distance Decrease y ObservedRunningAfterZeroRunWeeks. Los tres están implementados, probados y validados conjuntamente offline sobre la captura existente del 28 de septiembre de 2026. La siguiente fase es diseñar AI Coach V1; no se implementa Coach todavía ni se añaden Insights automáticamente.

Weekly Analytics V1 está aprobada como COMPLETE: resume el volumen y la composición por TrainingType de las Run suministradas para una semana local. La implementación y la validación de sus tres dimensiones están cerradas.

Trends ya calcula los cambios absolutos y porcentuales de distancia, número de actividades y moving time entre dos observaciones WeeklyAnalysis con lunes consecutivos. Las seis comparaciones, la normalización de historial semanal y la generación de pares consecutivos están probadas y validadas offline; WeeklyAnalysis permanece sin cambios. También se generan los seis resultados temporales de volumen sobre historial: cambios absolutos y porcentuales de distancia, conteo y moving time, probados y validados offline por incremento. La auditoría final conjunta concluyó READY TO CLOSE, sin blockers funcionales; Trends V1 está formalmente COMPLETE con el alcance aprobado sobre observaciones suministradas. La normalización valida lunes únicos y ordena las observaciones suministradas, sin completar huecos ni evaluar cobertura. Trends V1 queda cerrada en volumen total, sin ventana fija ni modelo genérico Trend. Insights reutiliza esas capacidades para detectar los patrones implementados. El cierre calendario, la cobertura y la selección automática de semanas aptas son posibles ampliaciones posteriores y no requisitos de cierre de Trends V1.

Longest run y calendario permanecen como posibles ampliaciones futuras de Analytics, sujetas a una necesidad concreta de Trends o Insights; no bloquean el cierre de V1.

Cada nueva capacidad seguirá el ciclo:

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
* TrainingTypeSummary
* WeeklyRunningDistanceChange
* WeeklyRunningDistancePercentageChange
* WeeklyRunningActivityCountChange
* WeeklyRunningActivityCountPercentageChange
* WeeklyRunningMovingTimeChange
* WeeklyRunningMovingTimePercentageChange
* PersistentWeeklyRunningDistanceIncrease
* PersistentWeeklyRunningDistanceDecrease
* ObservedRunningAfterZeroRunWeeks
* Tipos de entrenamiento

Los datos opcionales ausentes de las actividades y sus análisis permanecen como None. En los resultados porcentuales de Trends, None significa exclusivamente porcentaje indefinido por base anterior cero; no representa datos ausentes.

Los laps mantienen su orden original.

WeeklyAnalysis representa la fecha del lunes local del atleta, las tres métricas de volumen y running_structure_by_type. Este último campo obligatorio contiene seis resúmenes inmutables TrainingTypeSummary, en el orden del enum existente, con training_type, activity_count, distance_meters y moving_time_seconds. Los modelos permanecen sin lógica de cálculo ni validación automática; quien los construye proporciona todos los datos. La distancia por tipo es obligatoria y conserva la precisión float sin redondear. El moving time por tipo es obligatorio y conserva segundos enteros exactos.

WeeklyRunningDistanceChange es una dataclass inmutable con previous_week_start_date, current_week_start_date y value: float obligatorio, no opcional. Representa el cambio ABSOLUTO de distancia en METROS entre dos semanas consecutivas observadas: una transición, no una observación puntual, porcentaje ni Insight. No calcula ni valida, no convierte unidades y no conserva referencias a WeeklyAnalysis.

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

5. Weekly Analytics V1 ✅ COMPLETE

Definición y alcance aprobado

Resumen determinista del volumen y composición por TrainingType de las actividades Run suministradas para una semana local del atleta.

Weekly Analytics V1 incluye:

* week_start_date
* running_distance_meters
* running_activity_count
* running_moving_time_seconds
* running_structure_by_type: para cada TrainingType, activity_count, distance_meters y moving_time_seconds.

Las seis categorías son Easy, Long, Tempo, Intervals, Race y Other. Weekly Structure V1 está completa en sus tres dimensiones. El cierre de Weekly Analytics V1 es independiente del posterior cierre de Trends V1. Strava Integration permanece parcial; existen los tres Insights planificados implementados y validados mediante tests, mientras que Coach permanece pendiente.

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

Weekly Structure V1 ✅ — conteo, distancia y moving time por TrainingType

El primer incremento describe cuántas actividades corresponden a Easy, Long, Tempo, Intervals, Race y Other. Selecciona exactamente las mismas Run de la semana local que las métricas de volumen y clasifica cada entrada seleccionada una sola vez mediante el clasificador existente, sin modificar sus reglas. Cada categoría aparece una vez; las ausentes tienen conteo cero. La suma reconcilia con running_activity_count. Una sesión sigue significando una actividad Run suministrada, incluso con distancia o tiempo cero; no se fusionan actividades ni se deduplican registros.

El segundo incremento añade distance_meters: suma las distancias de las mismas Run, en el mismo recorrido y con la misma clasificación que el conteo. Cada entrada aporta a una única categoría. Una actividad con distancia cero sigue contando; una categoría ausente conserva conteo 0 y distancia 0.0. La suma por categorías reconcilia con running_distance_meters dentro de la precisión float, sin redondear ni ajustar valores para forzar igualdad. No se añade validación defensiva.

El tercer incremento añade moving_time_seconds como suma exacta de Activity.moving_time_seconds. Cada Run se clasifica una sola vez y su conteo, distancia y tiempo se acumulan en la misma categoría. Tiempo cero sigue contando y distancia cero no impide aportar tiempo positivo. Las categorías ausentes y semanas sin Run conservan seis resúmenes con las tres medidas a cero. La suma de segundos por tipo reconcilia exactamente con running_moving_time_seconds. No se estima, no se usa elapsed_time y no se convierten las unidades.

Weekly Structure V1 queda completa en las tres dimensiones acordadas: activity count, distance y moving time. No se almacenarán porcentajes, Easy / Quality, intensidad fisiológica, sesión exigente, tirada larga principal, cronología ni conclusiones o recomendaciones. Other se conserva explícitamente. Los futuros patrones de densidad y sesiones consecutivas podrán necesitar información individual adicional; WeeklyAnalysis no será su única fuente.

Modelo semanal

WeeklyAnalysis representa las tres métricas de volumen, la fecha del lunes local y el conteo, distancia y moving time por tipo. Conserva resultados cero, incluida distancia cero con un número positivo de actividades.

El flujo Activities → WeeklyAnalysis ya está disponible sobre actividades suministradas. Reutiliza la definición de semana local y los cálculos de distancia, conteo, tiempo en movimiento y estructura por tipo. La fecha del lunes se obtiene convirtiendo el límite inicial UTC a la timezone del atleta antes de extraer la fecha.

Una entrada sin carreras coincidentes produce un análisis con la fecha de la semana, las tres métricas de volumen a cero y seis categorías con conteo, distancia y moving time a cero. Las referencias sin timezone se rechazan, incluso con una lista vacía. Los resultados describen los datos suministrados y no garantizan que el historial semanal esté completo ni deduplicado. Este flujo no recupera actividades de Strava.

Fuera del alcance V1

* Aggregate pace almacenado.
* Easy / Quality.
* Longest run.
* Active running days.
* Rest days.
* Sesiones consecutivas.
* Distribución diaria.
* Densidad/calendario.

Estos conceptos permanecen en el roadmap, reclasificados por responsabilidad; no son requisitos pendientes para cerrar Weekly Analytics V1.

Limitaciones del resumen

WeeklyAnalysis es un resumen y no pretende conservar toda la información de las actividades originales. No permite reconstruir sus extremos individuales ni su cronología. Trends e Insights podrán necesitar Activity u otras fuentes además de WeeklyAnalysis. No existe todavía persistencia histórica de actividades; la disponibilidad futura de esos datos deberá resolverse cuando sea necesaria.

Una semana sin Run en los datos suministrados no demuestra una semana real de descanso. La clasificación por TrainingType describe las reglas actuales basadas en nombres, no intensidad fisiológica. El tratamiento automático de semanas abiertas/incompletas queda como posible ampliación posterior a Trends V1; los totales por sí solos no garantizan la cobertura del historial.

6. TRENDS V1 — COMPLETE ✅

Implementado: cambios absolutos de las tres métricas de volumen entre dos WeeklyAnalysis consecutivos, como current menos previous:

* weekly_running_distance_change: float en metros, sin redondeos ni conversión a kilómetros.
* weekly_running_activity_count_change: int, diferencia exacta de running_activity_count.
* weekly_running_moving_time_change: int en segundos, diferencia exacta de running_moving_time_seconds.

Las seis APIs escalares reciben previous y current y comparten una única utilidad interna sencilla en src/trends/_week.py. Esta exige que ambas fechas sean lunes y estén separadas exactamente por siete días calendario en orden cronológico. Rechaza con ValueError la misma semana, el orden invertido, los huecos y las fechas que no sean lunes. No introduce timezone ni diferencias horarias UTC, no muta las observaciones y no crea modelos de dominio.

También están implementadas weekly_running_distance_percentage_change, weekly_running_activity_count_percentage_change y weekly_running_moving_time_percentage_change. Devuelven float | None: 100 * (current - previous) / previous cuando la base es positiva, sin redondear; 10.0 significa 10 %. Una base cero produce None tanto en 0 → positivo como en 0 → 0. None indica exclusivamente que el porcentaje no está definido por base cero, no dato ausente ni cambio cero. Con base positiva, mismo valor produce 0.0 y valor actual cero produce −100.0. La aritmética se comparte en una utilidad interna sencilla, sin tolerancias de producción. La validación temporal se ejecuta antes de resolver la base cero.

Trends compara hechos de Analytics y calcula diferencias y porcentajes. Insights detecta patrones mediante reglas explícitas; el primer detector reconoce persistencia de dirección, sin afirmar relevancia por magnitud. Coach interpretará y recomendará. El cálculo actual no evalúa si una semana está abierta/cerrada ni si el historial es completo, y no recibe reference_date. No rellena semanas ausentes con cero: cero y ausencia de observación son conceptos distintos.

También está implementada normalize_weekly_history: acepta una Sequence de WeeklyAnalysis, incluida una entrada vacía o una sola observación, y devuelve una tuple ordenada cronológicamente con exactamente los mismos objetos. Exige fechas de lunes únicas y rechaza con ValueError cualquier fecha duplicada, aunque se repita el mismo objeto o sus valores coincidan. No modifica la colección ni los campos, incluida running_structure_by_type. Conserva huecos y observaciones existentes con cero Run; no crea, elimina ni fusiona semanas. Normalizar significa únicamente validar identidad semanal, garantizar unicidad y establecer orden temporal.

El caller debe proporcionar observaciones con contexto compatible de atleta y timezone. La normalización no valida calidad de métricas, continuidad, cobertura, completitud ni cierre calendario. La normalización permite huecos; las comparaciones exigen consecutividad y la generación de pares selecciona únicamente transiciones consecutivas.

También está implementada consecutive_week_pairs en el área de historial. Acepta una Sequence de WeeklyAnalysis, llama internamente a normalize_weekly_history y devuelve una tuple de pares (previous, current) de observaciones adyacentes separadas exactamente siete días calendario. Conserva los objetos originales y no muta entradas ni campos. Los pares pueden solaparse; vacío y singleton producen una tuple vacía. Las fechas no lunes y los duplicados se rechazan mediante la normalización existente. Los huecos se omiten sin crear semanas ni reportarlos, y las observaciones con cero Run participan normalmente. Solo se examinan fechas; no se filtra por métricas ni se evalúan cobertura o cierre calendario.

consecutive_week_pairs devuelve pares de WeeklyAnalysis; no calcula cambios ni construye resultados temporales. Las seis APIs plurales posteriores consumen esos pares, ejecutan la comparación escalar correspondiente y construyen una tuple de resultados temporales específicos. WeeklyAnalysis conserva su contrato.

Está implementada weekly_running_distance_changes: recibe un historial de WeeklyAnalysis y devuelve una tuple de WeeklyRunningDistanceChange en orden cronológico. Compone consecutive_week_pairs para seleccionar las transiciones y weekly_running_distance_change para calcular cada valor, sin duplicar reglas ni fórmulas. Los huecos no generan resultados, las observaciones cero participan normalmente y vacío/singleton o ausencia de pares producen una tuple vacía. Los errores de normalización se propagan; las entradas permanecen intactas. Los resultados no conservan observaciones aisladas ni permiten reconstruir los totales originales.

Está implementada weekly_running_distance_percentage_changes, que compone consecutive_week_pairs y la función escalar porcentual existente. Devuelve una tuple de WeeklyRunningDistancePercentageChange, dataclass congelada sin lógica con previous_week_start_date, current_week_start_date y value: float | None. El valor se expresa como porcentaje (10.0 significa 10 %), sin redondear. None significa exclusivamente porcentaje indefinido porque la distancia anterior es cero, también en 0 → 0. La transición conserva su resultado con None; un hueco no produce objeto. No se añaden estados, metadata ni validaciones al modelo.

Está implementada weekly_running_activity_count_changes: compone consecutive_week_pairs y weekly_running_activity_count_change, sin repetir selección temporal ni resta. Devuelve una tuple de WeeklyRunningActivityCountChange, dataclass congelada sin lógica con previous_week_start_date, current_week_start_date y value: int. Representa el cambio ABSOLUTO en número de actividades, no el conteo actual ni un porcentaje. Cada par válido produce un entero, incluido 0 → 0 = 0; no convierte a float ni introduce None. Los huecos no producen resultados y las entradas permanecen intactas.

Está implementada weekly_running_activity_count_percentage_changes: compone consecutive_week_pairs y weekly_running_activity_count_percentage_change, que sigue siendo la autoridad del cálculo. Devuelve una tuple de WeeklyRunningActivityCountPercentageChange, dataclass congelada sin lógica con previous_week_start_date, current_week_start_date y value: float | None. El porcentaje se conserva sin redondeos; None indica exclusivamente base de conteo cero, tanto en 0 → positivo como en 0 → 0, y mantiene su objeto de transición. Un hueco no genera resultado. Los errores de normalización se propagan y las entradas permanecen intactas.

Está implementada weekly_running_moving_time_changes: compone consecutive_week_pairs y weekly_running_moving_time_change, que conserva la autoridad del cálculo. Devuelve una tuple de WeeklyRunningMovingTimeChange, dataclass congelada sin lógica con previous_week_start_date, current_week_start_date y value: int. Representa el cambio ABSOLUTO de moving time en segundos, sin conversiones a float ni a otras unidades. Todo par válido produce un resultado entero, incluido 0 → 0 = 0. Las semanas observadas con moving time cero mantienen sus transiciones; los huecos no generan resultados ni puentes. Los errores de normalización se propagan y las entradas permanecen intactas.

Está implementada weekly_running_moving_time_percentage_changes: compone consecutive_week_pairs y weekly_running_moving_time_percentage_change, que sigue siendo la autoridad del cálculo. Devuelve una tuple de WeeklyRunningMovingTimePercentageChange, dataclass congelada sin lógica con previous_week_start_date, current_week_start_date y value: float | None. Aunque los totales originales se expresan en segundos, el resultado es un porcentaje, sin conversiones ni redondeos. None indica exclusivamente porcentaje indefinido por moving time anterior cero, incluido 0 → 0, y conserva su objeto de transición. Los huecos no generan resultados; los errores de normalización se propagan y las entradas permanecen intactas.

Frontera aprobada de Trends V1

Trends V1 compara hechos WeeklyAnalysis suministrados. Su alcance completo incluye seis comparaciones escalares de volumen (distancia, conteo y moving time, absolutas y porcentuales), normalize_weekly_history, consecutive_week_pairs, seis modelos temporales específicos y seis APIs plurales, con tests y validación real. Las semanas se identifican por su lunes local y solo se comparan fechas separadas exactamente siete días calendario en orden cronológico. Los huecos no se atraviesan; las semanas observadas con cero son observaciones reales. Cada par válido produce un valor absoluto definido. Los porcentajes conservan su objeto con None exclusivamente cuando la base anterior es cero; None no representa hueco, error, dato desconocido ni ausencia de cambio. No hay redondeos de producción ni mutaciones.

Trends V1 NO certifica cobertura completa, historial completo, cierre calendario, mismo atleta, misma timezone ni mismo origen de datos. El caller es responsable de proporcionar observaciones compatibles con el análisis que pretende realizar. Esta frontera es el contrato aprobado, no un bug ni deuda funcional de Trends V1.

Se mantienen seis modelos específicos y APIs explícitas, aceptando la pequeña repetición declarativa y de composición. Las funciones escalares son la autoridad del cálculo y consecutive_week_pairs selecciona las transiciones. No se introducen modelos genéricos, metadata, agregados, herencia, generics ni TrendSeries.

Trends V1 está COMPLETE: la auditoría final conjunta y la validación de su alcance aprobado están cerradas. TrainingType trends, ventanas, medias móviles, segmentos, reporte de huecos, selección automática por cobertura, determinación de semana abierta/cerrada, reference_date y certificación de historial completo no son requisitos para cerrar V1; permanecen como posibles ampliaciones posteriores. Insights sigue siendo una capa posterior.

⸻

7. Insights V1 ✅ COMPLETE

FIRST INSIGHT IMPLEMENTED AND VALIDATED

Persistent Weekly Running Distance Increase

Existe detect_persistent_weekly_running_distance_increases, que recibe Sequence[WeeklyAnalysis] y devuelve tuple[PersistentWeeklyRunningDistanceIncrease, ...]. La salida siempre es una tuple cronológica: vacía, con un resultado o con varios.

Definición y semántica

Una ventana de cuatro observaciones semanales con lunes consecutivos produce un Insight cuando las cuatro tienen running_distance_meters > 0 y running_activity_count > 0, y existen tres cambios absolutos consecutivos de distancia, estrictamente positivos y temporalmente encadenados. El destino del primer cambio coincide con el origen del segundo, y el destino del segundo con el origen del tercero; tres resultados contiguos en una colección no bastan.

4 observaciones = 3 transiciones. «Persistente» tiene aquí una definición contractual concreta: tres aumentos consecutivos de distancia Run observada. El hecho describe exclusivamente los datos suministrados. No significa mejora, progresión adecuada, aumento significativo, carga fisiológica, adaptación, riesgo, sobreentrenamiento, necesidad de descanso ni recomendación.

Evidencia del resultado

PersistentWeeklyRunningDistanceIncrease es una frozen dataclass sin cálculos ni validación automática. Conserva:

* start_week_date: lunes de la primera observación.
* end_week_date: lunes de la cuarta observación, no el final calendario de esa semana.
* weekly_distances_meters: tuple de las cuatro distancias exactas en metros, en orden semanal.
* weekly_activity_counts: tuple de los cuatro conteos, en el mismo orden; acreditan la condición de elegibilidad.
* distance_changes: tuple de los tres objetos WeeklyRunningDistanceChange producidos por Trends, conservando fechas y valores exactos.

No contiene recomendaciones, confidence, metadata, porcentajes ni referencias completas a WeeklyAnalysis.

Composición y límites

Insights reutiliza normalize_weekly_history y weekly_running_distance_changes. No recalcula agregación semanal, orden temporal, validación de lunes, duplicados, pares consecutivos ni diferencias de distancia. Añade la detección del patrón y conserva su evidencia. Los ValueError de Trends se propagan incluso para un historial corto con una fecha inválida.

Analytics calcula → Trends compara → Insights detecta → Coach interpreta/recomienda.

Un hueco rompe el patrón, sin puentes ni semanas creadas. Una observación con conteo cero o distancia <= 0 invalida esa ventana. Cero no significa descanso; hueco no significa cero. La secuencia 0 → 10 → 20 → 30 no produce este Insight.

El crecimiento es estricto: 10 → 20 → 20 → 30 no cumple. No se aplican redondeos, tolerancias, epsilon ni threshold mínimo. Incrementos positivos pequeños también cumplen; no se afirma relevancia por magnitud.

Se conservan los solapamientos: 10 → 20 → 30 → 40 → 50 produce dos resultados, uno por cada ventana fija de cuatro observaciones. No existen todavía episodios ni agrupación de resultados.

El caller sigue siendo responsable del contexto compatible de atleta y timezone y de suministrar métricas válidas. El detector no certifica cobertura, completitud, cierre calendario ni origen; una semana abierta puede participar si cumple la regla sobre sus observaciones. No modifica las entradas y no requiere dependencias nuevas ni IA/LLM.

Persistent Weekly Running Distance Decrease — IMPLEMENTED AND VALIDATED mediante tests automatizados

Existe detect_persistent_weekly_running_distance_decreases, que recibe Sequence[WeeklyAnalysis] y devuelve tuple[PersistentWeeklyRunningDistanceDecrease, ...] en orden cronológico, incluida la tuple vacía cuando no hay resultados.

El contrato exige una ventana fija de cuatro observaciones de semanas calendario consecutivas, identificadas por lunes locales. Todas deben tener running_distance_meters > 0 y running_activity_count > 0. Las tres transiciones absolutas de distancia deben ser estrictamente negativas y temporalmente encadenadas: el destino de la primera coincide con el origen de la segunda, y el destino de la segunda con el origen de la tercera. Tres objetos negativos adyacentes en la colección no bastan.

35 → 31 → 27 → 22 km cumple con conteos positivos. 35 → 30 → 30 → 20 km no cumple por igualdad. 20 → 15 → 10 → 0 km no cumple por distancia cero final, incluso con conteo positivo. Un hueco rompe el patrón; no se crean observaciones ni se conectan semanas separadas por un hueco. Las observaciones ineligibles permanecen en el historial: su elegibilidad se evalúa dentro de cada ventana candidata. Se conservan todos los solapamientos, sin agrupar episodios.

PersistentWeeklyRunningDistanceDecrease es una frozen dataclass sin cálculos ni validación automática, con exactamente cinco campos:

* start_week_date: date, lunes de la primera observación.
* end_week_date: date, lunes de la cuarta observación, no el final calendario de esa semana.
* weekly_distances_meters: tuple[float, float, float, float], distancias originales en orden semanal.
* weekly_activity_counts: tuple[int, int, int, int], conteos originales en el mismo orden.
* distance_changes: tuple[WeeklyRunningDistanceChange, WeeklyRunningDistanceChange, WeeklyRunningDistanceChange], los objetos originales producidos por Trends con sus fechas y valores negativos exactos.

Reutiliza normalize_weekly_history y weekly_running_distance_changes sin recalcular agregación, orden, consecutividad ni diferencias. Propaga los ValueError por fechas duplicadas o no lunes, incluso con historiales cortos; conserva las entradas. No modifica Analytics, Trends, WeeklyAnalysis ni el contrato de Increase, y no introduce una abstracción genérica de dirección.

No aplica umbral mínimo, porcentajes, redondeos, tolerancias, confidence ni cierre calendario. El caller proporciona métricas válidas y contexto compatible de atleta/timezone. Una semana abierta puede participar; el resultado describe exclusivamente observaciones suministradas, sin certificar cobertura ni completitud. No interpreta desentrenamiento, recuperación, fitness, lesión, entrenamiento apropiado o insuficiente, ni recomienda acciones: esas responsabilidades pertenecen a Coach. Una transición hacia cero no se reinterpreta como inactividad.

La validación automatizada del 7 de octubre de 2026 incluye 7 tests del modelo Decrease y 54 tests nuevos de detectores, incluida una regresión conjunta Increase/Decrease. Pasan 352 tests focalizados y los 791 tests de la suite completa configurada. El detector y ambos modelos de Insight alcanzan el 100 % de cobertura. En aquel incremento no se realizaron solicitudes live a Strava ni validación nueva de Decrease contra la captura real; la validación offline final conjunta posterior se documenta más abajo.

ObservedRunningAfterZeroRunWeeks — IMPLEMENTED AND VALIDATED mediante tests automatizados

Existe detect_observed_running_after_zero_run_weeks, que recibe Sequence[WeeklyAnalysis] y devuelve tuple[ObservedRunningAfterZeroRunWeeks, ...] en orden cronológico por running_week_date, incluida la tuple vacía cuando no hay resultados.

Detecta una secuencia maximal de al menos DOS observaciones semanales suministradas consecutivas con running_activity_count == 0, seguida inmediatamente por una observación consecutiva con running_activity_count > 0. La elegibilidad depende exclusivamente del conteo: running_distance_meters no determina si una observación es cero-Run o contiene Run. Una observación con conteo positivo y distancia cero es válida como observación siguiente y termina la secuencia cero-Run. No se añade validación defensiva de consistencia conteo/distancia; las métricas válidas y el contexto compatible de atleta/timezone siguen siendo responsabilidad del caller.

En los siguientes ejemplos, 0 y positivo indican conteo Run, no distancia:

* 0 → positivo: ningún resultado.
* 0 → 0 → positivo: un resultado con observed_zero_week_count = 2.
* 0 → 0 → 0 → positivo: un único resultado con observed_zero_week_count = 3, conservando el episodio completo suministrado, sin ventanas solapadas.
* 0 → 0 → positivo → positivo: un único resultado.
* 0 → 0 → positivo → 0 → 0 → positivo: dos resultados separados.

La secuencia puede empezar al principio del historial; no exige una observación positiva anterior. Una secuencia cero-Run al final sin observación siguiente con conteo positivo no produce Insight. Maximal se refiere exclusivamente al tramo continuo suministrado, sin afirmar que se conoce su comienzo real fuera del historial.

Un hueco reinicia el episodio candidato, sin crear observaciones ni puentes: 0 → hueco → 0 → positivo no cumple; 0 → hueco → 0 → 0 → positivo produce un resultado para los dos ceros posteriores al hueco. Un hueco entre la secuencia cero-Run y la observación con Run también impide detectar ese episodio.

El modelo es una frozen dataclass sin cálculos ni validación automática, con exactamente:

* first_zero_week_date: date, lunes local de la primera observación cero-Run del episodio suministrado.
* observed_zero_week_count: int, número de observaciones cero-Run consecutivas del episodio maximal.
* running_week_date: date, lunes local de la observación siguiente con Run.
* running_week_activity_count: int, conteo exacto de esa observación.
* running_week_distance_meters: float, distancia exacta de esa observación, incluso cero.

El detector consume WeeklyAnalysis directamente a través de consecutive_week_pairs, que reutiliza normalize_weekly_history para validar lunes únicos y ordenar. Reutiliza la consecutividad calendario existente y reinicia el episodio cuando los pares no comparten su semana de conexión. No usa cambios de distancia ni otros cálculos Trends, y no modifica Analytics, WeeklyAnalysis, Trends, Increase o Decrease. Los errores de fechas duplicadas o no lunes se propagan incluso con historiales cortos. Las entradas, sus valores, orden, identidades y estructuras anidadas permanecen intactos.

El Insight describe observaciones suministradas. Cero Run no demuestra inactividad real, descanso, lesión, desentrenamiento, interrupción del entrenamiento, ausencia de ejercicio ni que el atleta no corrió. La observación siguiente tampoco acredita un retorno conductual. No interpreta ni recomienda, no certifica cobertura o completitud ni filtra por cierre calendario. No almacena WeeklyAnalysis completos, última fecha cero redundante, tuples de ceros, confidence, porcentajes ni información fisiológica.

Validación automatizada del 7 de octubre de 2026: 48 tests del detector y 7 del modelo, incluidos episodios maximales, mínimos, huecos y cadenas desconectadas, conteo exclusivo, distancia cero, entradas inconsistentes sin corrección, orden, errores, fechas calendario y ausencia de mutaciones. Pasan 212 tests focalizados de Insights/modelos/historial, incluida regresión de Increase/Decrease, y los 846 tests de la suite completa configurada. El nuevo detector/modelo y los Insights existentes alcanzan 100 % de cobertura. En aquel incremento no se realizaron solicitudes live a Strava ni nueva validación contra datos reales; la validación offline final conjunta posterior se documenta más abajo.

Insights V1 está COMPLETE con los tres contratos anteriores, tras la validación offline final conjunta. La siguiente fase es AI Coach V1 design. No se implementa ningún Insight adicional ni Coach todavía.

⸻

🧪 Validación

Automated Tests

Actualmente:

846 tests passing

El contrato de los modelos semanales cuenta con 14 tests, el cálculo de estructura por tipo con 26 y la construcción Activities → WeeklyAnalysis con 13. Pasan los 112 tests de Weekly Analytics; junto con los 107 del clasificador existente, pasan 219 tests específicos. Los 230 tests de src/trends siguen pasando, junto con los 36 tests de los seis modelos temporales: 266 tests del conjunto auditado de Trends V1. Increase conserva sus 7 tests de modelo y 40 tests de detector. Decrease añade 7 tests de modelo y 54 tests de detectores, incluida una regresión conjunta, para 108 tests de los dos primeros Insights y sus modelos. ObservedRunningAfterZeroRunWeeks añade 48 tests de detector y 7 de modelo, para 163 tests de Insights y sus modelos. Pasan 212 tests focalizados de Insights/modelos/historial. La suite completa configurada pasa con 846 tests: 845 Unit y 1 Integration mockeado. La cobertura global combinada de statements y branches es 97,79086892488954 % (664/679), con 544/553 statements (98,37251356238698 %) y 120/126 branches (95,23809523809524 %); los tres modelos de Insight y src/insights alcanzan el 100 %; los seis módulos de Trends y los seis modelos de cambio implementados alcanzan el 100 %; el cálculo de estructura, el constructor semanal y los modelos semanales alcanzan el 100 %. Se conservan los tests existentes de volumen, clasificación y mapper. Los 7 tests adicionales de la utilidad local de captura constan como validados anteriormente y no forman parte de la suite configurada.

La suite cubre, entre otros:

* Authentication.
* Strava client.
* Activity mapping.
* Pace.
* Training classification.
* Training analysis.
* Weekly calculations.
* Persistent Weekly Running Distance Increase y Decrease: continuidad y encadenamiento temporal, elegibilidad, dirección estricta, solapamientos, evidencia exacta, identidad de objetos Trends y ausencia de mutaciones.
* ObservedRunningAfterZeroRunWeeks: episodios maximales con mínimo de dos semanas cero-Run, presencia posterior por conteo, huecos, distancia cero y ausencia de mutaciones.
* Domain models.
* Casos límite.
* Manejo de datos ausentes o incorrectos.
* Límites temporales y cambios DST.

Existe además un integration test que conecta token refresh con athlete retrieval utilizando HTTP mockeado.

Reporting de tests tradicionales

Allure está integrado con pytest mediante allure-pytest 2.16.2 como herramienta de testing, sin dependencias en el dominio. En la validación anterior de Increase se comprobó su ejecución con Python 3.14 y pytest 9.1.1: tanto la suite normal como la generación de resultados Allure pasan con los mismos 730 tests. Los 730 resultados generados quedan clasificados centralmente por las convenciones existentes: 729 Unit y 1 Integration; hay 0 E2E existentes. Los artefactos permanecen excluidos de Git. La CLI externa de Allure no está instalada en el entorno validado; se generan resultados sin ella, pero la construcción del informe HTML queda sin verificar. La CLI y la generación HTML son aspectos de tooling y no limitaciones funcionales de Trends V1. La clasificación de Allure no cambia la selección ni ejecución de pytest. En el incremento Decrease se ejecutó la suite con cobertura (791 tests) y en el tercer Insight con 846 tests, sin regenerar los resultados Allure; el conteo de 730 resultados anterior es evidencia histórica.

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

Decisión de producto: Weekly Analytics utiliza los valores exactos proporcionados por la API para calcular sus métricas; no intentaremos reproducir la presentación interna de Strava ni ajustar los cálculos para igualar sus valores visibles. El cierre de aquella reconciliación no eliminó las limitaciones de la captura ni supuso por sí solo el cierre de Weekly Analytics V1. El detalle se conserva en local_validation/strava_reconciliation_report.md.

La validación offline de running_moving_time_seconds se completó sobre la captura del 28 de septiembre: 89 actividades, 59 Run y 24 semanas. La suma independiente por semana local coincide exactamente en todas las semanas: 186774 segundos en total, sin diferencias y sin modificar la captura. Cinco semanas sin registros Run producen 0; la última seguía abierta al extraer. Los valores fuente ya están normalizados desde moving_time por el mapper. Esta comprobación no garantiza integridad del historial ni demuestra descanso en semanas sin registros. Informe y reproducción: local_validation/weekly_moving_time_report.md y local_validation/validate_weekly_moving_time.py.

Validación offline del conteo semanal por TrainingType

El conteo se contrastó con la captura del 28 de septiembre: 89 actividades, 59 Run y 24 semanas. Una tabla de etiquetas revisadas por nombre y una agrupación independiente por semana ISO local coinciden con Analytics en todas las categorías de las 24 semanas: Easy 20, Long 11, Tempo 2, Intervals 8, Race 1 y Other 17. La suma reconcilia con running_activity_count en cada semana y suma 59 en total. Cinco semanas sin Run conservan seis ceros. No se modificó la captura ni el clasificador. Esta validación comprueba el contrato basado en nombres, no la intensidad real ni la integridad del historial; la última semana seguía abierta. Informe y reproducción: local_validation/weekly_structure_report.md y local_validation/validate_weekly_structure.py.

Validación offline de distancia semanal por TrainingType

El segundo incremento se contrastó con la misma captura intacta de 89 actividades, 59 Run y 24 semanas. Se reutilizaron las etiquetas revisadas y se sumaron independientemente los literales de distancia con Decimal por semana ISO local y tipo. Los totales fuente son Easy 140582,6 m, Long 132624,6 m, Tempo 13375,3 m, Intervals 65105,5 m, Race 6201,0 m y Other 110697,9 m: 468586,9 m en total. Analytics coincide dentro de precisión float por categoría y semana; las 24 semanas reconcilian con running_distance_meters y conservan sus conteos. La diferencia máxima semanal de reconciliación es 3,64 × 10⁻¹² m y la global 5,82 × 10⁻¹¹ m en valor absoluto, sin redondear los cálculos. La auditoría usa tolerancia relativa 1e-12 y absoluta 1e-9 m. Se verificó el SHA-256 original sin cambios. Informe y reproducción: local_validation/weekly_structure_distance_report.md y local_validation/validate_weekly_structure.py. Siguen vigentes las limitaciones de integridad del historial y semana abierta.

Validación offline de moving time por TrainingType y cierre de Weekly Structure V1

El último incremento se contrastó con una suma independiente de segundos enteros sobre la misma captura: Easy 57941 s, Long 51859 s, Tempo 5463 s, Intervals 26283 s, Race 2334 s y Other 42894 s; total 186774 s. Las seis categorías de las 24 semanas coinciden exactamente con el oráculo y reconcilian con running_moving_time_seconds. Count y distance continúan reconciliando, y sus resultados por categoría y semana permanecen idénticos a la validación anterior. El SHA-256 original de la captura y el de las etiquetas no cambian. Con tests y validación superados, Weekly Structure V1 quedó cerrada en activity count, distance y moving time. La posterior decisión de producto declara Weekly Analytics V1 COMPLETE con el alcance definido en este documento. Informe y reproducción: local_validation/weekly_structure_time_report.md y local_validation/validate_weekly_structure.py.

Evidencia de cierre de Weekly Analytics V1

Se conserva la evidencia existente, sin ejecutar nuevos tests para esta actualización documental:

* 417 tests aprobados.
* 96,76 % de cobertura global.
* 24 semanas reales reconciliadas.
* 59 Run.
* 468.586,9 m.
* 186.774 segundos.

Los conteos y segundos reconcilian exactamente; la distancia, dentro de la precisión float documentada, sin redondeos para forzar igualdad. La captura original permanece intacta según la validación registrada. Esta evidencia respalda el alcance aprobado sobre datos suministrados, no la integridad del historial ni una integración end-to-end completa.

Validación offline del cambio absoluto de distancia semanal

Se validaron 23 pares consecutivos entre las 24 observaciones semanales existentes de la captura, sin filtrar por cierre calendario ni crear semanas ausentes. Los cambios coinciden con diferencias independientes entre totales fuente agrupados por semana ISO local y sumados con Decimal. La máxima diferencia numérica es 3,64 × 10⁻¹² m, dentro de la tolerancia de auditoría relativa 1e-12 y absoluta 1e-9 m, sin redondear producción. El SHA-256 original permanece intacto. Ejemplos fuente: 27 abril → 4 mayo, +13623,9 m; 20 → 27 abril, −12434,6 m; 17 → 24 agosto, 0 m. Esta validación comprueba aritmética entre observaciones, no completitud ni cierre de semanas. Informe y reproducción: local_validation/weekly_distance_change_report.md y local_validation/validate_weekly_distance_change.py.

Validación offline de cambios absolutos de conteo y moving time

Los 23 pares consecutivos de las mismas 24 observaciones reconciliaron exactamente con diferencias de conteos y sumas de segundos calculados independientemente desde las Run fuente. Ejemplos: 27 abril → 4 mayo, +3 actividades y +5792 s; 20 → 27 abril, −2 actividades y −4978 s; 11 → 18 mayo, 0 actividades de cambio; 17 → 24 agosto, 0 s de cambio. Los 23 resultados de distancia se conservaron idénticos al incremento anterior y el SHA-256 original de la captura no cambió. Esta comprobación no evalúa cierre calendario ni completitud. Informe: local_validation/weekly_volume_change_report.md; reproducción mediante local_validation/validate_weekly_distance_change.py, ampliada para comprobar las tres métricas.

Validación offline de cambios porcentuales de volumen

El 1 de octubre de 2026 se comprobaron los mismos 23 pares consecutivos de la captura original mediante un cálculo independiente con Decimal sobre los totales fuente. Cada una de las tres métricas tiene 19 porcentajes definidos y 4 None por base cero; todos coinciden con el oráculo. Ejemplos: conteo 1 → 4 produce 300.0 %, 3 → 1 produce aproximadamente −66,6667 %, 3 → 3 produce 0.0 % y 0 → 4 produce None. La muestra no contiene 0 % con base positiva para distancia o tiempo; esos casos se cubren en tests. Los pares 0 → 0 producen None. Los cambios absolutos permanecen idénticos y el SHA-256 original de la captura se conserva. No se evalúan cierre calendario, completitud ni relevancia. Informe: local_validation/weekly_percentage_change_report.md; reproducción mediante local_validation/validate_weekly_distance_change.py, ampliada para ambas clases de cálculo.

Validación offline de normalización de historial semanal

Las 24 observaciones existentes producen exactamente la misma secuencia cronológica al suministrarlas en orden normal, inverso y en una permutación determinista. Se conservan identidad, todos los campos y estructura por tipo, sin mutar las entradas. Al retirar en memoria el 29 de junio quedan 23 observaciones y esa semana no se reconstruye; duplicarla produce ValueError. Permanecen las cinco observaciones con cero Run: 1 de junio, 17, 24 y 31 de agosto, y 28 de septiembre. El SHA-256 original permanece intacto. No se afirma completitud ni cierre calendario. Informe y reproducción: local_validation/weekly_history_normalization_report.md y local_validation/validate_weekly_history_normalization.py.

Validación offline de pares semanales consecutivos

Las 24 observaciones existentes producen los mismos 23 pares en orden normal, inverso y una permutación determinista. Las expectativas se construyeron desde fechas fuente mediante búsqueda de sucesores calendario. Retirar el 29 de junio deja 23 observaciones y 21 pares; retirar también el 6 de julio deja 22 observaciones y 20 pares. Desaparecen únicamente las conexiones afectadas, sin puentes a través del hueco. Las cinco observaciones cero participan normalmente; todos los pares producidos en los escenarios son aceptados por las seis comparaciones. Se verificaron identidad de extremos, todos los campos incluida la estructura por tipo, entradas intactas y SHA-256 original sin cambios. No se evalúan completitud ni cierre calendario. Informe y reproducción: local_validation/consecutive_week_pairs_report.md y local_validation/validate_consecutive_week_pairs.py.

Validación offline de resultados temporales de distancia

Las 24 observaciones existentes producen los mismos 23 WeeklyRunningDistanceChange en orden normal, inverso y permutado. Fechas y valores se contrastaron con un oráculo construido desde las fechas y totales semanales de la captura, usando Decimal para la resta fuente. Todos los valores coinciden exactamente con la API escalar; la diferencia máxima respecto a los totales fuente es 3,64 × 10⁻¹² m, dentro de tolerancia de auditoría relativa 1e-12 y absoluta 1e-9 m, sin redondear producción. Retirar 29/06 deja 21 resultados y retirar también 06/07 deja 20, sin puentes. Las cinco observaciones cero conservan sus cambios asociados. Identidad, campos y orden de las entradas permanecen intactos y se conserva el SHA-256 original. No se evalúan cobertura, cierre calendario ni relevancia. Informe y reproducción: local_validation/distance_history_report.md y local_validation/validate_distance_history.py.

Validación offline de resultados temporales porcentuales de distancia

Las mismas 24 observaciones producen 23 resultados en orden normal, inverso y permutado: 19 valores definidos y 4 None por base cero, verificados realmente. Todos coinciden exactamente con la función escalar; el contraste independiente con Decimal desde los totales fuente tiene una diferencia máxima de 5,68 × 10⁻¹⁴ puntos porcentuales, dentro de tolerancia de auditoría relativa 1e-12 y absoluta 1e-10. Retirar 29/06 deja 21 resultados y retirar también 06/07 deja 20, sin puentes ni objetos None para huecos. Los resultados None de transiciones existentes permanecen presentes. No hay 0.0 % definido en la captura; se cubre en tests. Identidad y campos de las entradas permanecen intactos y el SHA-256 coincide con el original. Informe y reproducción: local_validation/distance_percentage_history_report.md y local_validation/validate_distance_percentage_history.py.

Validación offline de resultados temporales de conteo absoluto

Las 24 observaciones existentes producen los mismos 23 WeeklyRunningActivityCountChange con entrada normal, inversa y permutada. Todos los value son int y coinciden exactamente con la función escalar y con diferencias independientes de los conteos fuente, sin tolerancias ni conversiones. Ejemplos: 27/04 → 04/05, +3; 20/04 → 27/04, −2; 11/05 → 18/05, 0; 25/05 → 01/06, −4 hacia una semana cero; 01/06 → 08/06, +4 desde cero. Retirar 29/06 deja 21 resultados y retirar también 06/07 deja 20, sin puentes. Las cinco observaciones cero mantienen sus transiciones; campos, identidad y orden de las entradas y SHA-256 original permanecen intactos. Informe y reproducción: local_validation/activity_count_history_report.md y local_validation/validate_activity_count_history.py.

Validación offline de resultados temporales de conteo porcentual

El 2 de octubre de 2026 se verificaron las mismas 24 observaciones: producen los mismos 23 WeeklyRunningActivityCountPercentageChange en orden normal, inverso y permutado, con 19 valores definidos y 4 None. Cada valor coincide exactamente con la función escalar y con el cálculo independiente 100 * (current - previous) / previous sobre los conteos fuente para base positiva, sin tolerancias ni redondeos. Los cuatro None conservan sus objetos de transición por base cero, incluidos los pares 0 → 0. La captura contiene ejemplos de las cinco clases: +300.0 %, −66.66666666666667 %, 0.0 %, −100.0 % y None. Retirar 29/06 deja 21 resultados y retirar también 06/07 deja 20, sin puentes ni resultados para huecos. Campos, identidad y orden de las entradas permanecen intactos; el SHA-256 original se conserva. No se evalúan cobertura ni cierre calendario. Informe y reproducción: local_validation/activity_count_percentage_history_report.md y local_validation/validate_activity_count_percentage_history.py.

Validación offline de resultados temporales de moving time absoluto

El 2 de octubre de 2026 se verificaron las mismas 24 observaciones: producen los mismos 23 WeeklyRunningMovingTimeChange con entrada normal, inversa y permutada. Todos los valores son int en segundos y coinciden exactamente con la función escalar, con la diferencia directa de moving time semanal y con diferencias independientes de sumas de segundos de las Run fuente agrupadas por semana ISO local. Ejemplos: 27/04 → 04/05, +5792 s; 20/04 → 27/04, −4978 s; 17/08 → 24/08, 0 s (0 → 0); 25/05 → 01/06, −9775 s hacia cero; 01/06 → 08/06, +10392 s desde cero. Retirar 29/06 deja 21 resultados y retirar también 06/07 deja 20, sin puentes. Las cinco semanas cero conservan sus transiciones, con enteros y sin None. Campos, identidad y orden de las entradas permanecen intactos y el SHA-256 original no cambia. No se evalúan cobertura ni cierre calendario. Informe y reproducción: local_validation/moving_time_history_report.md y local_validation/validate_moving_time_history.py.

Validación offline de resultados temporales de moving time porcentual

El 2 de octubre de 2026 se verificaron las mismas 24 observaciones: producen los mismos 23 WeeklyRunningMovingTimePercentageChange en orden normal, inverso y permutado, con 19 valores definidos de tipo float y 4 None por base cero. Cada valor coincide exactamente con la función escalar y, para base positiva, con 100 * (current - previous) / previous sobre sumas independientes de segundos de las Run fuente agrupadas por semana ISO local. Error máximo: 0.0 puntos porcentuales, sin redondeos. Ejemplos: 27/04 → 04/05, +155.28150134048258 %; 20/04 → 27/04, −57.16582452916858 %; 25/05 → 01/06, −100.0 %; 01/06 → 08/06, None. No existe 0.0 % definido en la captura; permanece cubierto en tests. Los cuatro None conservan sus transiciones válidas, también en 0 → 0. Retirar 29/06 deja 21 resultados y retirar también 06/07 deja 20, sin puentes ni resultados para huecos. Campos, identidad y orden de las entradas y SHA-256 original permanecen intactos. Esta evidencia forma parte del cierre auditado de Trends V1 y no certifica cobertura ni cierre calendario. Informe y reproducción: local_validation/moving_time_percentage_history_report.md y local_validation/validate_moving_time_percentage_history.py.

Auditoría final conjunta y cierre formal de Trends V1

La auditoría final concluyó READY TO CLOSE, sin blockers funcionales. Se revisaron el flujo de composición, las seis APIs escalares y temporales, los seis modelos y la frontera de responsabilidades. Los ocho validadores de historial se ejecutaron nuevamente y un contraste conjunto independiente agrupó las Run fuente por semana ISO local, con Decimal para distancia y enteros para conteo y segundos. Las 24 WeeklyAnalysis producen 23 transiciones en cada API: los tres absolutos tienen 23 valores definidos y cada porcentaje tiene 19 valores definidos y 4 None que conservan sus transiciones. La entrada normal, inversa y permutada es equivalente. Retirar 29/06 deja 21 resultados y retirar también 06/07 deja 20, sin puentes sobre huecos. Se verificaron igualdad exacta con los escalares, contraste independiente, observaciones cero conservadas, ausencia de redondeos de producción y ausencia de mutaciones de campos, identidad u orden.

Conteo y moving time coinciden exactamente con el oráculo; distancia absoluta y porcentual presentan diferencias máximas de 3,64 × 10⁻¹² m y 5,68 × 10⁻¹⁴ puntos porcentuales, dentro de las tolerancias de auditoría existentes. El SHA-256 original de la captura permanece intacto: 69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac. En aquel cierre documental de Trends, anterior al primer Insight, la suite pasó con 683 tests; se conservó la cobertura auditada del 97,40 % global y el 100 % en los seis módulos de Trends y los seis modelos temporales. No se modifica código funcional ni se repite la captura remota para este cierre.

TRENDS V1 — COMPLETE. Aquel cierre no incluía el primer Insight, implementado y validado posteriormente. Coach, UI y las capacidades futuras de Trends permanecen pendientes.

⸻

Validación offline del primer Insight: Persistent Weekly Running Distance Increase

El 2 de octubre de 2026 se validó el detector exclusivamente con local_validation/strava_snapshot_2026-09-28.json, sin descargar nuevos datos de Strava. Las 24 WeeklyAnalysis reconstruidas con Analytics producen EXACTAMENTE 1 Insight:

* Ventana: 2026-06-22 → 2026-06-29 → 2026-07-06 → 2026-07-13.
* Distancias exactas en metros: (10057.0, 31246.6, 35607.5, 36571.5).
* Conteos Run: (2, 4, 4, 4).
* Cambios exactos de Trends en metros: (21189.6, 4360.9000000000015, 964.0), con las fechas de las tres transiciones correspondientes. Se conserva el float de Trends, sin ajustarlo a una representación decimal redondeada.

Entrada normal, inversa y permutada producen el mismo único resultado. Retirar únicamente el 29/06 en memoria produce 0 Insights; retirar únicamente el 06/07 también produce 0. No se crean puentes. Se comprobaron fechas, distancias, conteos y cambios, además de ausencia de mutaciones en valores, orden, identidades y estructura por tipo de las entradas. Los tests específicos verifican también la conservación de los objetos de Trends.

El SHA-256 original permanece intacto antes y después: 69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac. La comprobación utilizó una ejecución temporal offline sin añadir un validador persistente al repositorio. Esta evidencia valida el patrón sobre los registros suministrados, sin certificar integridad del historial ni interpretar descanso, fisiología o recomendaciones. La implementación no modificó Analytics, Trends ni WeeklyAnalysis.

⸻

Validación offline final conjunta y cierre de Insights V1 — 7 de octubre de 2026

Se reutilizó exclusivamente local_validation/strava_snapshot_2026-09-28.json, sin solicitudes de red ni datos nuevos. El SHA-256 antes y después es 69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac. Las 89 actividades exportadas contienen 59 Run y 468586.9 m. Analytics reconstruye exactamente las 24 observaciones ya suministradas, del 20/04 al 28/09, sin crear semanas: 23 transiciones consecutivas, cinco observaciones cero-Run y una semana final abierta al extraer.

Resultados exactos sobre el mismo historial:

* PersistentWeeklyRunningDistanceIncrease: 1 resultado, 22/06 → 13/07; distancias (10057.0, 31246.6, 35607.5, 36571.5) m, conteos (2, 4, 4, 4), cambios (21189.6, 4360.9000000000015, 964.0) m con las tres transiciones fechadas originales de Trends.
* PersistentWeeklyRunningDistanceDecrease: 0 resultados. 27/07 → 17/08 presenta (41238.7, 21190.3, 19115.9, 0.0) m y (4, 2, 2, 0) Run: el cuarto dato no es elegible y no se reinterpreta como disminución persistente válida.
* ObservedRunningAfterZeroRunWeeks: 1 resultado; first_zero_week_date = 2026-08-17, observed_zero_week_count = 3, running_week_date = 2026-09-07, running_week_activity_count = 2, running_week_distance_meters = 15495.9. Las semanas 17/08, 24/08 y 31/08 contienen cero Run suministradas y forman un único episodio maximal.

Una agrupación independiente de registros Run por semana ISO local verificó los totales y enumeró todas las ventanas/episodios. No se encontraron falsos positivos ni negativos. Los conteos y moving time coinciden exactamente; distancia coincide exactamente con los totales float de la captura y difiere como máximo 3.637978807091713e-12 m de las sumas Decimal independientes, dentro de las tolerancias existentes de auditoría, sin tolerancia ni redondeo en detección. Las transiciones iguales entre semanas cero no generan Increase/Decrease; la semana aislada cero del 01/06 y la semana final cero sin observación siguiente no generan episodio. Solo existe un episodio que cumple el contrato en esta captura; la separación de múltiples episodios se valida mediante los tests existentes.

Se contrastaron 27 variantes: orden normal, inverso, permutado y retirada individual en memoria de cada una de las 24 semanas. Todas coinciden con el oráculo independiente. No se rellenaron huecos ni se crearon puentes. Retirar 24/08, 31/08 o 07/09 elimina el episodio; retirar 17/08 conserva correctamente un episodio nuevo de dos ceros desde 24/08. Retirar cualquier miembro de Increase elimina ese resultado. Valores, orden, identidades y resúmenes TrainingType permanecen intactos; los objetos reales de Trends retenidos como evidencia conservan identidad y valores.

Tras la auditoría, la suite completa configurada pasó con 846 tests. Cobertura combinada 97.79086892488954 % (664/679), statements 98.37251356238698 % (544/553), branches 95.23809523809524 % (120/126); ambos módulos detectores y los tres modelos de Insight tienen 100 %. No se modificó código de producción ni contratos y no se encontró ningún defecto pendiente. Evidencia detallada y tabla completa de observaciones: local_validation/insights_v1_report.md.

INSIGHTS V1 — COMPLETE con exactamente PersistentWeeklyRunningDistanceIncrease, PersistentWeeklyRunningDistanceDecrease y ObservedRunningAfterZeroRunWeeks. El cierre valida los contratos sobre observaciones suministradas, no cobertura/completitud ni cierre calendario. No acredita inactividad real, descanso, fisiología ni retorno conductual; no interpreta ni recomienda. AI Coach V1 design es la siguiente fase, sin implementación de Coach en este cierre.

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

Weekly Analytics V1 ✅ COMPLETE

Activities → WeeklyAnalysis (volumen y composición por TrainingType sobre Run suministradas)

↓

Trends V1 ✅ COMPLETE

Dos WeeklyAnalysis consecutivos → cambios absolutos y porcentuales de distancia, conteo y moving time (implementados). Normalización de observaciones semanales (lunes únicos y orden ascendente) implementada. Generación de pares consecutivos implementada. Cambios absolutos y porcentuales de distancia sobre historial con resultados fechados implementados. Los cambios absolutos y porcentuales de conteo sobre historial también están implementados. Moving time absoluto y porcentual sobre historial están implementados. Las seis APIs temporales de volumen están auditadas y Trends V1 está COMPLETE; selección automática de semanas aptas queda como posible ampliación posterior; Activity u otras fuentes podrán ser necesarias.

↓

Insights V1 ✅ COMPLETE

Persistent Weekly Running Distance Increase ✅ — implementado y validado, incluida validación offline.

Persistent Weekly Running Distance Decrease ✅ — implementado y validado mediante tests automatizados.

ObservedRunningAfterZeroRunWeeks ✅ — tercer Insight implementado y validado mediante tests automatizados.

Analytics + Trends → tres aumentos o disminuciones estrictas entre cuatro observaciones elegibles; Analytics + historial → episodio maximal de al menos dos semanas cero-Run seguido de una observación con Run, por conteo exclusivamente. Los tres Insights planificados están implementados y validados conjuntamente offline. Insights V1 está COMPLETE; la siguiente etapa es AI Coach V1 design, sin implementación automática.

↓

AI Coach ⏳ Pendiente

Athlete context + Analytics + Insights + Goal → interpretación y recomendaciones

↓

Training Planning

Creación y adaptación progresiva de planes de entrenamiento.

Capacidades futuras reclasificadas

* Analytics: longest run y métricas de calendario —active running days, días sin Run, sesiones consecutivas, distribución diaria y densidad definida objetivamente— serán posibles ampliaciones si una necesidad concreta de Trends/Insights las requiere. Longest run no equivale a TrainingType.Long. Los días sin registros Run no se presentarán como descanso real; rest days requiere información y una definición adicionales.
* Analytics derivado: el ritmo agregado podrá calcularse a partir de distancia y moving time si hay una necesidad concreta, sin almacenar un campo redundante. Easy / Quality permanece pendiente de definición y posible derivación; las etiquetas actuales no acreditan intensidad fisiológica.
* Trends: V1 está COMPLETE sobre observaciones suministradas. TrainingType trends, ventanas, medias móviles y tratamiento automático de semanas abiertas/incompletas o disponibilidad de datos son posibles ampliaciones posteriores. Las comparaciones temporales por TrainingType solo se incorporarán si Insights demuestra una necesidad concreta; no son requisito previo de Insights V1.
* Insights: además de los tres patrones planificados ya implementados, se mantienen como posibilidades futuras la detección de cambios relevantes, concentración, anomalías y otros patrones. Los patrones cronológicos podrán cruzar domingo/lunes y necesitar actividades individuales de una ventana mayor.
* Coach: interpretación contextual, valoración de recuperación adecuada y recomendaciones.

Esta reclasificación conserva las posibilidades del roadmap sin incorporarlas al contrato de Weekly Analytics V1 ni comprometer su implementación inmediata.

⸻

💡 Insights implementados y posibilidades futuras

Implementados y validados mediante tests: Persistent Weekly Running Distance Increase, Persistent Weekly Running Distance Decrease y ObservedRunningAfterZeroRunWeeks, con los contratos específicos descritos anteriormente. Los tres disponen de validación offline conjunta. Insights V1 está COMPLETE; AI Coach V1 design es el próximo paso.

Las siguientes posibilidades siguen pendientes de definición o implementación; no son requisitos obligatorios para cerrar Insights V1:

* Otros patrones de volumen.
* Evolución de la tirada larga.
* Concentración de sesiones exigentes.
* Sesiones exigentes consecutivas.
* Cambios importantes en frecuencia de entrenamiento.
* Cambios en proporción Easy / Quality.
* Cambios de rendimiento en entrenamientos comparables.
* Datos anómalos o potencialmente poco fiables.

Ejemplo válido:

En cuatro observaciones semanales consecutivas con conteo Run positivo, 24 → 27 → 30 → 33 km presenta tres aumentos consecutivos. Este ejemplo conceptual no añade un porcentaje acumulado al contrato implementado.

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
* Ampliaciones posteriores a Trends V1: TrainingType trends, ventanas, medias móviles, reporte de huecos/segmentos y selección temporal por cobertura o cierre calendario. No son capacidades pendientes del alcance cerrado ni requisitos automáticos de Insights V1.
* Tooling Allure: CLI externa no instalada e informe HTML sin validar. En 78 casos parametrizados que contienen funciones, los IDs históricos varían entre procesos por sus representaciones; estabilizarlos queda como deuda de tooling, sin afectar resultados ni clasificación.
* Insights V1 está COMPLETE con los tres Insights aprobados, implementados y validados mediante tests y auditoría offline conjunta. AI Coach V1 design es la siguiente fase; no existe Coach implementado.
* No existe Coach.

Estos elementos deben priorizarse según las necesidades del roadmap, no necesariamente por su orden técnico.

⸻

➡️ Próximo paso

Insights V1 — COMPLETE. Persistent Weekly Running Distance Increase, Persistent Weekly Running Distance Decrease y ObservedRunningAfterZeroRunWeeks constituyen el alcance cerrado: implementados, probados y validados conjuntamente offline. El próximo trabajo es diseñar AI Coach V1: definir su alcance, entradas, interpretación contextual y criterios de evaluación. No se implementa Coach todavía ni se inicia otro Insight automáticamente. Weekly Analytics V1 y Trends V1 están COMPLETE; AI Coach permanece pendiente. Longest run, TrainingType, Easy/Quality, anomalías y rendimiento comparable siguen siendo posibilidades futuras, no requisitos obligatorios de cierre. TrainingType trends solo se planteará si una necesidad concreta demuestra que requiere comparaciones temporales por tipo.

Weekly Analytics V1 está COMPLETE y Weekly Structure V1 está cerrada en activity count, distance y moving time. No falta ninguna métrica adicional para el alcance aprobado.

Las seis operaciones solo exigen dos lunes consecutivos y devuelven diferencias absolutas o porcentuales de volumen, con None para porcentajes de base cero. La frontera aprobada de V1 deja cierre calendario, cobertura y selección automática de semanas aptas como posibles ampliaciones posteriores, sin confundir cero con ausencia de datos. La normalización de historial y la generación de pares están implementadas y no resuelven esas decisiones. Los seis resultados fechados de volumen están implementados, auditados y formalmente cerrados en Trends V1. Reporte de huecos y segmentos son ampliaciones posteriores; no se inicia automáticamente ningún otro incremento de Trends, Analytics, Insights o Coach.

El gap de detailed Strava activity → TrainingAnalysis y la ausencia de persistencia histórica de actividades permanecen documentados. No bloquean el cierre del resumen semanal sobre datos suministrados, pero deberán abordarse cuando las capacidades que dependan de ellos lo requieran.

⸻

Last updated: 7 October 2026
