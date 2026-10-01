# Validación offline de cambios porcentuales de volumen

Fecha: 1 de octubre de 2026.

## Contrato y método

Las tres APIs públicas terminadas en _percentage_change validan primero los lunes consecutivos con el mismo _validate_consecutive_weeks de los cambios absolutos. Después usan _percentage_change: 100 * (current - previous) / previous para base positiva; None para base cero, incluso 0 → 0. None significa porcentaje indefinido por base cero, no ausencia de datos ni cambio cero. No se redondea ni se aplican tolerancias en producción.

La utilidad de auditoría existente se amplió para las tres métricas. El oráculo agrupa las Run originales por semana ISO local, suma distancia con Decimal y conteos/segundos con enteros, y calcula independientemente (current / previous - 1) * 100 con Decimal. No reutiliza la fórmula ni validación temporal de producción para generar los valores esperados. Las únicas observaciones son las 24 ya existentes; se comprueban sus 23 pares consecutivos sin evaluar cierre o completitud.

SHA-256 original verificado sin cambios: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

## Resultado

Las tres métricas pasan en 23/23 pares: cada una tiene 19 porcentajes definidos y 4 None por base cero. None se compara por identidad; los floats se contrastan con tolerancia relativa 1e-12 y absoluta 1e-10 puntos porcentuales, exclusivamente en la auditoría. Los cambios absolutos se verifican también y permanecen idénticos a la auditoría anterior.

| Semana anterior | Semana actual | Distancia (%) | Conteo (%) | Moving time (%) |
|---|---|---:|---:|---:|
| 2026-04-20 | 2026-04-27 | -55.233467183113596 | -66.66666666666667 | -57.16582452916858 |
| 2026-04-27 | 2026-05-04 | 135.1818777162588 | 300.0 | 155.28150134048258 |
| 2026-05-04 | 2026-05-11 | -9.679733019437094 | -25.0 | -10.165931526990128 |
| 2026-05-11 | 2026-05-18 | -19.110324274329912 | 0.0 | -23.521159691372457 |
| 2026-05-18 | 2026-05-25 | 48.38681734972599 | 33.333333333333336 | 49.41913787832467 |
| 2026-05-25 | 2026-06-01 | -100.0 | -100.0 | -100.0 |
| 2026-06-01 | 2026-06-08 | None | None | None |
| 2026-06-08 | 2026-06-15 | 11.980701706948693 | 0.0 | 17.4364896073903 |
| 2026-06-15 | 2026-06-22 | -65.30860748053632 | -50.0 | -65.30645689937725 |
| 2026-06-22 | 2026-06-29 | 210.69503828179379 | 100.0 | 204.1095890410959 |
| 2026-06-29 | 2026-07-06 | 13.956398456152034 | 0.0 | 12.348555452003728 |
| 2026-07-06 | 2026-07-13 | 2.707294811486344 | 0.0 | -2.3019493985897967 |
| 2026-07-13 | 2026-07-20 | -28.13748410647635 | 0.0 | -28.061982593929102 |
| 2026-07-20 | 2026-07-27 | 56.91330685052431 | 0.0 | 60.96193567424019 |
| 2026-07-27 | 2026-08-03 | -48.615499518656016 | -50.0 | -46.21448212648946 |
| 2026-08-03 | 2026-08-10 | -9.789384765671075 | 0.0 | -7.998182231311065 |
| 2026-08-10 | 2026-08-17 | -100.0 | -100.0 | -100.0 |
| 2026-08-17 | 2026-08-24 | None | None | None |
| 2026-08-24 | 2026-08-31 | None | None | None |
| 2026-08-31 | 2026-09-07 | None | None | None |
| 2026-09-07 | 2026-09-14 | 10.325957188675716 | 0.0 | 10.588992597360798 |
| 2026-09-14 | 2026-09-21 | 128.67805334581192 | 50.0 | 120.023282887078 |
| 2026-09-21 | 2026-09-28 | -100.0 | -100.0 | -100.0 |

Distancia y moving time no tienen en esta muestra pares con base positiva y valores iguales; su resultado 0.0 se verifica mediante tests deterministas. Conteo sí ofrece 0.0 real, por ejemplo 3 → 3 del 11 al 18 de mayo. Los pares 0 → 0 del 17 al 24 y del 24 al 31 de agosto producen None, no 0 %. El par 1 → 8 junio ofrece base cero con valor posterior positivo en las tres métricas.

## Reproducción

```sh
.venv/bin/python -m local_validation.validate_weekly_distance_change local_validation/strava_snapshot_2026-09-28.json
```

La utilidad mantiene su nombre histórico y comprueba ahora cambios absolutos y porcentuales. El resultado nuevo está en weekly_percentage_change_results.json, ignorado por Git; los resultados históricos y la captura se conservan.

## Tests y límites

- 37 casos nuevos mediante las tres APIs públicas: semántica, tipo float/None, fracciones sin redondear, base positiva pequeña, rechazo temporal incluso antes de devolver None, ausencia de mutaciones y repetibilidad.
- Trends: 67 tests aprobados. Suite completa: 484 aprobados; cobertura global 97.04 % (97 % redondeado), los cinco módulos de Trends al 100 %.
- WeeklyAnalysis y los tests de cambios absolutos permanecen sin cambios. No hay modelos nuevos, selección de métricas configurable, series, ventanas, dirección ni interpretación.
