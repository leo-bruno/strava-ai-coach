# Conciliación de Strava — captura del 28 septiembre 2026

## Resultado

**59 Run, 468,5869 km.** El total anterior era 428,0531 km: cuatro carreras añadidas explican exactamente los 40,5338 km adicionales. Los 55 IDs anteriores se conservan con los mismos seis campos de Activity; no hay carreras eliminadas ni modificadas en esos campos.

**Investigación cerrada el 29 de septiembre de 2026, sin defecto encontrado en Weekly Analytics.** La suma exacta de las actividades API y la suma exacta de sus totales semanales coinciden en **468,5869 km**. Las 59 Run quedan asignadas a sus semanas sin pérdidas ni duplicación durante la agregación; se preservan todos los registros de la captura.

La diferencia residual respecto a la UI de Strava se clasifica como una diferencia no explicada de presentación/precisión, no como un error demostrado de nuestros cálculos. La precisión visible no permite determinar el algoritmo interno de Strava. No se intentará reproducirlo: Weekly Analytics debe calcular sus métricas con los valores exactos proporcionados por la API.

## Captura y límites

- Inicio incluido: 20 abril 2026 00:00 Europe/Madrid (19 abril 22:00 UTC).
- Final excluido: 5 octubre 2026 00:00 Europe/Madrid (4 octubre 22:00 UTC).
- Extracción: 2026-09-28T15:25:19.895754+00:00 a 2026-09-28T15:25:23.892996+00:00 (17:25:19–17:25:23 en Madrid).
- El intervalo sigue abierto. La semana del 28 septiembre no es completa.
- Páginas recibidas: 30, 30, 29, 0; la página corta no terminó la descarga.
- 89 actividades, ninguna fuera del intervalo y ningún ID repetido. No se aplicó deduplicación.
- Se utilizó StravaClient sin modificaciones. La captura conserva los campos de Activity devueltos por el cliente, no las respuestas HTTP originales. No se consultaron detalles, laps ni streams.
- No contiene credenciales. SHA-256 de la captura: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

## Diferencias por ID

| Fecha local | ID | Nombre | km añadidos |
|---|---|---|---:|
| 2026-04-20 08:46:29 | 18180725095 | Carrera de mañana | 6.5228 |
| 2026-04-23 06:24:48 | 18221366123 | Carrera intervalos por la mañana | 6.9660 |
| 2026-04-25 08:08:16 | 18247343117 | Carrera de mañana | 9.0240 |
| 2026-09-26 07:29:55 | 20332464889 | 18km Carrera larga progresiva | 18.0210 |

Tres carreras de abril: 22,5128 km. Carrera del 26 septiembre: 18,0210 km. Total adicional: 40,5338 km.

## Resultados semanales

| Lunes local | km | Run | Estado al extraer | Contraste independiente |
|---|---:|---:|---|---|
| 2026-04-20 | 22.5128 | 3 | Cerrada | OK |
| 2026-04-27 | 10.0782 | 1 | Cerrada | OK |
| 2026-05-04 | 23.7021 | 4 | Cerrada | OK |
| 2026-05-11 | 21.4078 | 3 | Cerrada | OK |
| 2026-05-18 | 17.3167 | 3 | Cerrada | OK |
| 2026-05-25 | 25.6957 | 4 | Cerrada | OK |
| 2026-06-01 | 0.0000 | 0 | Cerrada | OK |
| 2026-06-08 | 25.8883 | 4 | Cerrada | OK |
| 2026-06-15 | 28.9899 | 4 | Cerrada | OK |
| 2026-06-22 | 10.0570 | 2 | Cerrada | OK |
| 2026-06-29 | 31.2466 | 4 | Cerrada | OK |
| 2026-07-06 | 35.6075 | 4 | Cerrada | OK |
| 2026-07-13 | 36.5715 | 4 | Cerrada | OK |
| 2026-07-20 | 26.2812 | 4 | Cerrada | OK |
| 2026-07-27 | 41.2387 | 4 | Cerrada | OK |
| 2026-08-03 | 21.1903 | 2 | Cerrada | OK |
| 2026-08-10 | 19.1159 | 2 | Cerrada | OK |
| 2026-08-17 | 0.0000 | 0 | Cerrada | OK |
| 2026-08-24 | 0.0000 | 0 | Cerrada | OK |
| 2026-08-31 | 0.0000 | 0 | Cerrada | OK |
| 2026-09-07 | 15.4959 | 2 | Cerrada | OK |
| 2026-09-14 | 17.0960 | 2 | Cerrada | OK |
| 2026-09-21 | 39.0948 | 3 | Cerrada | OK |
| 2026-09-28 | 0.0000 | 0 | Abierta | OK |

Cerrada describe el calendario; no garantiza por sí sola la integridad de la cuenta.

## Contraste con los puntos semanales de Strava

Los valores UI proceden de la inspección manual comunicada por el usuario. Diferencia = API − UI, en metros. El símbolo † identifica los puntos que no coinciden con el redondeo convencional del total API a dos decimales.

| Semana local de 2026 | Strava UI km | API exactos km | Diferencia m |
|---|---:|---:|---:|
| 20/4–26/4 | 22.51 | 22.5128 | +2.8 |
| 27/4–3/5 † | 10.07 | 10.0782 | +8.2 |
| 4/5–10/5 | 23.70 | 23.7021 | +2.1 |
| 11/5–17/5 † | 21.40 | 21.4078 | +7.8 |
| 18/5–24/5 † | 17.31 | 17.3167 | +6.7 |
| 25/5–31/5 † | 25.69 | 25.6957 | +5.7 |
| 1/6–7/6 | 0.00 | 0.0000 | 0.0 |
| 8/6–14/6 † | 25.88 | 25.8883 | +8.3 |
| 15/6–21/6 | 28.99 | 28.9899 | −0.1 |
| 22/6–28/6 † | 10.05 | 10.0570 | +7.0 |
| 29/6–5/7 † | 31.24 | 31.2466 | +6.6 |
| 6/7–12/7 † | 35.60 | 35.6075 | +7.5 |
| 13/7–19/7 | 36.57 | 36.5715 | +1.5 |
| 20/7–26/7 | 26.28 | 26.2812 | +1.2 |
| 27/7–2/8 † | 41.23 | 41.2387 | +8.7 |
| 3/8–9/8 | 21.19 | 21.1903 | +0.3 |
| 10/8–16/8 † | 19.11 | 19.1159 | +5.9 |
| 17/8–23/8 | 0.00 | 0.0000 | 0.0 |
| 24/8–30/8 | 0.00 | 0.0000 | 0.0 |
| 31/8–6/9 | 0.00 | 0.0000 | 0.0 |
| 7/9–13/9 † | 15.49 | 15.4959 | +5.9 |
| 14/9–20/9 † | 17.09 | 17.0960 | +6.0 |
| 21/9–27/9 | 39.09 | 39.0948 | +4.8 |
| **Total** | **468.49** | **468.5869** | **+96.9** |

No se proporcionó un punto UI para 28/9–4/10. Esa semana contiene cero Run en la captura del 28 de septiembre y no cambia las sumas API; no se presupone su valor UI ni su resultado al cerrar la semana.

| Comparación de sumas | km |
|---|---:|
| Actividades API exactas | 468.5869 |
| Totales semanales API exactos | 468.5869 |
| Totales semanales API redondeados a dos decimales antes de sumar | 468.61 |
| Puntos semanales visibles de Strava | 468.49 |
| Totales semanales API truncados a dos decimales antes de sumar | 468.48 |

De las 19 semanas con carreras, siete puntos UI coinciden con el redondeo convencional y doce no. Redondear antes de sumar añade 23,1 m a la suma exacta y deja 120 m de diferencia frente a los puntos UI; no explica los 96,9 m. El truncamiento coincide en 18 de las 19 semanas con carreras, pero falla en 15/6–21/6: 28,9899 km se truncarían a 28,98, mientras que la UI muestra 28,99. Ninguna de las dos reglas uniformes reproduce la serie.

La semana 27/4–3/5 contiene una sola actividad, ID 18329563458 del 1 de mayo, con 10.078,2 m en la API frente a 10,07 km visibles en el punto semanal. Localiza la comparación de 8,2 m, pero no demuestra que Strava almacene una distancia distinta. No disponemos de valores UI por actividad con precisión suficiente para atribuir un error a una actividad concreta.

### Distinción entre 86,9 m y 96,9 m

- Respecto al total general mostrado: 468,5869 − 468,5000 = 0,0869 km = **86,9 m**.
- Respecto a la suma de puntos semanales visibles: 468,5869 − 468,4900 = 0,0969 km = **96,9 m**.

Los 86,9 m del informe anterior no eran un error aritmético: procedían de otra comparación, también conservada en la captura mediante display_km y display_minus_run_total_km. Que 468,49 redondee a 468,5 es consistente con la pantalla, pero no demuestra que Strava calcule el total general sumando los puntos ya formateados.

## Otros deportes

| sport_type | Actividades | km |
|---|---:|---:|
| Elliptical | 10 | 0.0000 |
| Run | 59 | 468.5869 |
| Walk | 1 | 1.1931 |
| WeightTraining | 17 | 0.0000 |
| Workout | 2 | 0.0000 |

No hay TrailRun ni VirtualRun. Walk aportaría 1,1931 km si se incluyera, por lo que no explica el exceso de 86,9 metros de Run. No se presupone que la vista Carrera incluya ninguno de estos deportes.

## Verificación y limitaciones

- Cada semana se calculó mediante weekly_analysis_from_activities con las actividades del intervalo y se contrastó por separado mediante agrupación ISO de fechas locales y suma Decimal. Las 24 semanas coinciden en lunes, distancia y conteo, y sus totales conservan las 59 carreras.
- La comparación por ID conserva multiplicidad. La suma de las contribuciones por ID coincide con la diferencia global de metros.
- El contraste independiente comienza en los datos descargados que entrega StravaClient; no valida de forma independiente su mapper ni la medición física de Strava.
- Se conservan los dos posibles duplicados del 4 mayo, IDs 18367551063 y 18679593966. No hay evidencia para eliminarlos de esta comparación.
- Las semanas sin registros no prueban descanso. No se ha auditado en vivo el scope concedido ni la semántica exacta del gráfico de Strava.
- Las peticiones paginadas no son una transacción atómica: cambios durante la extracción podrían afectar a la cobertura. La extracción terminó sin errores y no repitió IDs.
- En la validación del 28 de septiembre pasaron 369 tests: 362 existentes más 7 de la utilidad local. Incluyen páginas cortas, fallos, páginas repetidas, límites exactos, deportes, duplicados y protección frente a sobrescritura. El cierre documental no implica una nueva ejecución de esa suite.

## Reproducir

Ejecutar desde la raíz del repositorio, usando un nombre nuevo de salida para conservar esta captura:

```sh
.venv/bin/python -m local_validation.capture_strava_history --start 2026-04-20 --end-exclusive 2026-10-05 --timezone Europe/Madrid --per-page 30 --previous training_history_2026-05-01_2026-09-24.json --output local_validation/strava_snapshot_NUEVA_FECHA.json --strava-display-km 468.5
.venv/bin/python -m pytest src local_validation/capture_strava_history_unit_test.py -q -p no:cacheprovider
```

La captura incluye todas las actividades, IDs por semana, sumas esperadas, paginación, fechas de extracción y diferencias respecto al export anterior. La utilidad se ejecuta manualmente y no implementa sincronización en producción.

## Cierre y siguiente incremento

La reconciliación queda cerrada por decisión de producto, sin defecto encontrado en la agregación semanal sobre esta captura. La diferencia de presentación/precisión de Strava permanece sin explicación interna confirmada y no se continuará intentando reproducir su UI. Se mantienen las limitaciones de integridad y alcance descritas en este informe.

El siguiente incremento acordado de Weekly Analytics V1 es únicamente running_moving_time_seconds: sumar el tiempo en movimiento de las mismas actividades Run. Sigue pendiente y no se ha iniciado en este cierre documental; no se han modificado código de producción, métricas ni capturas.
