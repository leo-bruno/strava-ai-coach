# Validación offline de moving time por TrainingType y cierre de Weekly Structure V1

Fecha: 29 de septiembre de 2026.

## Método

Captura normalizada existente: `strava_snapshot_2026-09-28.json`; 89 actividades, 59 Run y 24 semanas en Europe/Madrid. El oráculo reutiliza las etiquetas independientes revisadas por nombre, agrupa por semana ISO local y suma directamente los enteros moving_time_seconds. No usa el clasificador, los límites ni los agregadores de producción para obtener los valores esperados. No hay conversiones de unidades, elapsed_time ni estimaciones.

En paralelo se repiten la suma independiente de conteos y la suma Decimal de distancia fuente. Se compararon además conteo y distancia por categoría y semana con el resultado guardado del incremento anterior: permanecen idénticos.

SHA-256 original de la captura, verificado sin cambios: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

SHA-256 de las etiquetas, sin cambios: `271dd222ee727c42ed48f7119abfb08538f3422b1e3f27010ffdaf9d632f7206`.

## Resultados

| Tipo | Conteo | Distancia fuente (m) | Segundos independientes | Segundos Analytics |
|---|---:|---:|---:|---:|
| Easy | 20 | 140582.6 | 57941 | 57941 |
| Long | 11 | 132624.6 | 51859 | 51859 |
| Tempo | 2 | 13375.3 | 5463 | 5463 |
| Intervals | 8 | 65105.5 | 26283 | 26283 |
| Race | 1 | 6201.0 | 2334 | 2334 |
| Other | 17 | 110697.9 | 42894 | 42894 |

Total: 59 Run, 468586,9 m de distancia fuente y **186774 segundos**. Conteo y moving time reconcilian exactamente por categoría, por semana y globalmente. Distancia reconcilia con tolerancia relativa 1e-12 y absoluta 1e-9 m, sin redondeos en producción. Diferencia máxima semanal de distancia: 3,637978807091713e-12 m; diferencia global absoluta: 5,820766091346741e-11 m, iguales al incremento anterior.

| Semana local | Run | Segundos por categorías | running_moving_time_seconds | Tres reconciliaciones |
|---|---:|---:|---:|---|
| 2026-04-20 | 3 | 8708 | 8708 | OK |
| 2026-04-27 | 1 | 3730 | 3730 | OK |
| 2026-05-04 | 4 | 9522 | 9522 | OK |
| 2026-05-11 | 3 | 8554 | 8554 | OK |
| 2026-05-18 | 3 | 6542 | 6542 | OK |
| 2026-05-25 | 4 | 9775 | 9775 | OK |
| 2026-06-01 | 0 | 0 | 0 | OK |
| 2026-06-08 | 4 | 10392 | 10392 | OK |
| 2026-06-15 | 4 | 12204 | 12204 | OK |
| 2026-06-22 | 2 | 4234 | 4234 | OK |
| 2026-06-29 | 4 | 12876 | 12876 | OK |
| 2026-07-06 | 4 | 14466 | 14466 | OK |
| 2026-07-13 | 4 | 14133 | 14133 | OK |
| 2026-07-20 | 4 | 10167 | 10167 | OK |
| 2026-07-27 | 4 | 16365 | 16365 | OK |
| 2026-08-03 | 2 | 8802 | 8802 | OK |
| 2026-08-10 | 2 | 8098 | 8098 | OK |
| 2026-08-17 | 0 | 0 | 0 | OK |
| 2026-08-24 | 0 | 0 | 0 | OK |
| 2026-08-31 | 0 | 0 | 0 | OK |
| 2026-09-07 | 2 | 6214 | 6214 | OK |
| 2026-09-14 | 2 | 6872 | 6872 | OK |
| 2026-09-21 | 3 | 15120 | 15120 | OK |
| 2026-09-28 | 0 | 0 | 0 | OK |

Las 24 semanas pasan. Las cinco semanas sin Run mantienen seis categorías con las tres métricas cero. La captura y las etiquetas no se modificaron.

## Reproducción

```sh
.venv/bin/python -m local_validation.validate_weekly_structure local_validation/strava_snapshot_2026-09-28.json local_validation/weekly_structure_name_labels.json
```

El detalle completo queda en `weekly_structure_time_results.json`, ignorado por Git junto con la captura y las etiquetas. Los resultados históricos de conteo y distancia se conservan.

## Tests y cierre

- 219 tests específicos: 112 de Weekly Analytics y modelos semanales, más 107 del clasificador.
- Suite completa: 417 tests aprobados. Cobertura global de líneas y ramas: 96.76 % (97 % redondeado). Estructura, constructor y modelos semanales: 100 %.
- Se ampliaron los tests existentes para comprobar tiempo por tipo en categorías ausentes, Other, semanas vacías, límites/DST/cambio de año, duplicados, distancia cero con tiempo positivo, reconciliación e inmutabilidad. Tres casos añadidos: dos distribuciones de tiempos enteros (incluido cero con distancia positiva) y la inmutabilidad del nuevo campo.
- El mock existente sigue verificando una única clasificación por entrada seleccionada; las tres medidas contribuyen a esa misma categoría y las entradas permanecen intactas.
- Weekly Structure V1 queda completa en activity count, distance y moving time. Weekly Analytics V1 continúa en desarrollo.
- Persisten las limitaciones de historial suministrado, duplicados conservados, clasificación basada en nombres y última semana abierta. Ceros no prueban descanso ni historial completo. No se añadió interpretación ni ninguna capacidad fuera del incremento.
