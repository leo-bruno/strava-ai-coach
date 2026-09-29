# Validación offline de Weekly Analytics

Validado el 28 de septiembre de 2026. Sin llamadas a Strava, cambios en producción, duración semanal ni deduplicación.

## Fuente y alcance

- Export: `training_history_2026-05-01_2026-09-24.json`.
- SHA-256: `733c18046bdee1250f0d6134981bd429ed20cfa65f252c64f5ce566f637dcecd`.
- Intervalo declarado: 1 de mayo a 24 de septiembre de 2026, UTC. Exportado el 24 de septiembre a las 13:54:37 UTC.
- Registros observados: 1 de mayo 08:19:51 UTC a 23 de septiembre 16:03:07 UTC.
- 55 registros Run válidos, todos utilizados; 52 pertenecen a 20 semanas completas del intervalo declarado (4 de mayo–20 de septiembre).
- Se asume Europe/Madrid; las 55 fechas locales coinciden con esa conversión. El export no identifica la zona IANA del atleta.
- Para clasificar semanas completas se usa conservadoramente el inicio del 24 de septiembre como final del intervalo; su inclusividad no está documentada. Esto no cambia las 20 semanas completas.

## Resultados

| Semana local | Cobertura | km | Actividades | Contraste |
|---|---|---:|---:|---|
| 2026-04-27 a 2026-05-03 | Parcial | 10.0782 | 1 | OK |
| 2026-05-04 a 2026-05-10 | Completa | 23.7021 | 4 | OK |
| 2026-05-11 a 2026-05-17 | Completa | 21.4078 | 3 | OK |
| 2026-05-18 a 2026-05-24 | Completa | 17.3167 | 3 | OK |
| 2026-05-25 a 2026-05-31 | Completa | 25.6957 | 4 | OK |
| 2026-06-01 a 2026-06-07 | Completa | 0.0000 | 0 | OK |
| 2026-06-08 a 2026-06-14 | Completa | 25.8883 | 4 | OK |
| 2026-06-15 a 2026-06-21 | Completa | 28.9899 | 4 | OK |
| 2026-06-22 a 2026-06-28 | Completa | 10.0570 | 2 | OK |
| 2026-06-29 a 2026-07-05 | Completa | 31.2466 | 4 | OK |
| 2026-07-06 a 2026-07-12 | Completa | 35.6075 | 4 | OK |
| 2026-07-13 a 2026-07-19 | Completa | 36.5715 | 4 | OK |
| 2026-07-20 a 2026-07-26 | Completa | 26.2812 | 4 | OK |
| 2026-07-27 a 2026-08-02 | Completa | 41.2387 | 4 | OK |
| 2026-08-03 a 2026-08-09 | Completa | 21.1903 | 2 | OK |
| 2026-08-10 a 2026-08-16 | Completa | 19.1159 | 2 | OK |
| 2026-08-17 a 2026-08-23 | Completa | 0.0000 | 0 | OK |
| 2026-08-24 a 2026-08-30 | Completa | 0.0000 | 0 | OK |
| 2026-08-31 a 2026-09-06 | Completa | 0.0000 | 0 | OK |
| 2026-09-07 a 2026-09-13 | Completa | 15.4959 | 2 | OK |
| 2026-09-14 a 2026-09-20 | Completa | 17.0960 | 2 | OK |
| 2026-09-21 a 2026-09-27 | Parcial | 21.0738 | 2 | OK |

Total semanas completas: 396,9011 km y 52 actividades. Total del archivo: 428,0531 km y 55 actividades.

## Contraste independiente

1. Se mapearon todos los registros mediante activity_from_strava, sin omitir fallos. No hubo errores.
2. Para cada semana se llamó weekly_analysis_from_activities con la lista completa y una referencia consciente de timezone.
3. El resultado esperado se obtuvo directamente del JSON: fecha local de start_date_local, agrupación por año/semana ISO y lunes obtenido con date.fromisocalendar. No se reutilizaron _week, weekly_running_distance ni weekly_running_activity_count.
4. Las distancias fuente se sumaron con Decimal y los conteos con el número de registros de cada grupo. La tolerancia numérica fue 0,000001 metros; la diferencia máxima observada fue 0,000000000003 metros.
5. Se contrastó cada fecha local con start_date UTC convertido a Europe/Madrid: cero discrepancias. El sufijo Z de start_date_local se trata como representación de hora local, no como un segundo instante UTC.
6. La partición de IDs por semana conserva exactamente todos los registros Run del archivo. El JSON de resultados conserva el detalle por actividad para auditar cada suma.
7. Los 57 tests existentes de límites de semana, distancia, conteo, modelo y constructor pasaron.

Ejemplo, semana del 4 de mayo: 4560,5 + 4560,5 + 6552,5 + 8028,6 = 23702,1 metros; cuatro registros. Coincide con producción.

## Anomalías y límites

- Probable duplicado: IDs 18367551063 y 18679593966, 4 de mayo, separados por un segundo y ambos con 4560,5 metros. Dispositivos distintos según el informe individual existente. Se conservan ambos. Si se confirmara y eliminara uno, esa semana tendría 19,1416 km y tres actividades; no se aplica esa corrección.
- No hay IDs repetidos, actividades excluidas del archivo, distancias cero ni errores de mapeo.
- Semanas del 1 de junio, 17 de agosto, 24 de agosto y 31 de agosto: cero registros; no demuestran descanso ni ausencia real de entrenamiento.
- Semanas del 27 de abril y 21 de septiembre: parciales, separadas de las completas.
- El export declara 76 actividades recuperadas y 55 carreras; solo contiene esas 55 Run. No permite inspeccionar los otros 21 registros ni verificar su clasificación o exclusión original.
- complete=true y failures=[] son declaraciones del exportador, no una verificación independiente del historial de Strava. Completa describe cobertura del calendario declarado, no garantía de todas las actividades del atleta.
- La muestra no atraviesa DST/cambio de año ni prueba por sí sola actividades en las fronteras de semana, deportes excluidos o distancia cero. Esos contratos cuentan con tests sintéticos.
- La independencia del contraste es algorítmica: comparte el mismo export; no hay cotejo con una fuente externa ni recuperación nueva.

## Conclusión y siguiente paso

Flujo Activities → WeeklyAnalysis validado offline para esta muestra y la timezone asumida: 20 semanas completas y dos parciales coinciden en los tres campos. No se declara completa la integración de Strava ni Weekly Analytics V1.

El siguiente incremento puede ser running_moving_time_seconds. Mantener el tiempo de Activity como fuente; el informe individual existente documenta que la suma de laps puede diferir. Conservar los límites conocidos de integridad del historial y duplicados.

## Reproducción

```sh
.venv/bin/python -m local_validation.validate_weekly_history training_history_2026-05-01_2026-09-24.json --timezone Europe/Madrid --output local_validation/weekly_history_results.json
.venv/bin/python -m pytest src/analytics/_week_unit_test.py src/analytics/distance_unit_test.py src/analytics/activity_count_unit_test.py src/analytics/weekly_analysis_unit_test.py src/models/weekly_analysis_unit_test.py -q -p no:cacheprovider
```
