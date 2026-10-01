# Validación offline de cambios absolutos de volumen semanal

Fecha: 29 de septiembre de 2026.

## Método y resultado

La utilidad existente validate_weekly_distance_change se amplió para comprobar las tres APIs explícitas de Trends. Se mantienen las 24 observaciones de la captura y sus 23 pares consecutivos. No se fabrican observaciones, ni se evalúan cierre calendario o completitud.

El oráculo cuenta las Run y suma moving_time_seconds directamente desde registros fuente agrupados por semana ISO local, sin usar los agregadores de Analytics. Resta los totales independientes de cada par. Las diferencias de conteo y tiempo coinciden exactamente en 23/23 pares, con resultados int. Se volvió a comprobar distancia con Decimal y se verificó que sus 23 resultados son idénticos a la auditoría anterior.

SHA-256 original antes y después: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`. La captura permanece intacta.

| Semana anterior | Semana actual | Conteo anterior → actual | Cambio conteo | Segundos anteriores → actuales | Cambio segundos |
|---|---|---|---:|---|---:|
| 2026-04-20 | 2026-04-27 | 3 → 1 | -2 | 8708 → 3730 | -4978 |
| 2026-04-27 | 2026-05-04 | 1 → 4 | 3 | 3730 → 9522 | 5792 |
| 2026-05-04 | 2026-05-11 | 4 → 3 | -1 | 9522 → 8554 | -968 |
| 2026-05-11 | 2026-05-18 | 3 → 3 | 0 | 8554 → 6542 | -2012 |
| 2026-05-18 | 2026-05-25 | 3 → 4 | 1 | 6542 → 9775 | 3233 |
| 2026-05-25 | 2026-06-01 | 4 → 0 | -4 | 9775 → 0 | -9775 |
| 2026-06-01 | 2026-06-08 | 0 → 4 | 4 | 0 → 10392 | 10392 |
| 2026-06-08 | 2026-06-15 | 4 → 4 | 0 | 10392 → 12204 | 1812 |
| 2026-06-15 | 2026-06-22 | 4 → 2 | -2 | 12204 → 4234 | -7970 |
| 2026-06-22 | 2026-06-29 | 2 → 4 | 2 | 4234 → 12876 | 8642 |
| 2026-06-29 | 2026-07-06 | 4 → 4 | 0 | 12876 → 14466 | 1590 |
| 2026-07-06 | 2026-07-13 | 4 → 4 | 0 | 14466 → 14133 | -333 |
| 2026-07-13 | 2026-07-20 | 4 → 4 | 0 | 14133 → 10167 | -3966 |
| 2026-07-20 | 2026-07-27 | 4 → 4 | 0 | 10167 → 16365 | 6198 |
| 2026-07-27 | 2026-08-03 | 4 → 2 | -2 | 16365 → 8802 | -7563 |
| 2026-08-03 | 2026-08-10 | 2 → 2 | 0 | 8802 → 8098 | -704 |
| 2026-08-10 | 2026-08-17 | 2 → 0 | -2 | 8098 → 0 | -8098 |
| 2026-08-17 | 2026-08-24 | 0 → 0 | 0 | 0 → 0 | 0 |
| 2026-08-24 | 2026-08-31 | 0 → 0 | 0 | 0 → 0 | 0 |
| 2026-08-31 | 2026-09-07 | 0 → 2 | 2 | 0 → 6214 | 6214 |
| 2026-09-07 | 2026-09-14 | 2 → 2 | 0 | 6214 → 6872 | 658 |
| 2026-09-14 | 2026-09-21 | 2 → 3 | 1 | 6872 → 15120 | 8248 |
| 2026-09-21 | 2026-09-28 | 3 → 0 | -3 | 15120 → 0 | -15120 |

## Reproducción

```sh
.venv/bin/python -m local_validation.validate_weekly_distance_change local_validation/strava_snapshot_2026-09-28.json
```

El nombre de la utilidad se conserva para mantener la reproducción anterior; ahora verifica distancia, conteo y tiempo. El detalle nuevo está en weekly_volume_change_results.json, ignorado por Git; se conserva el resultado anterior de distancia.

## Tests y alcance

- 30 tests de Trends aprobados: los 18 existentes de distancia y 12 nuevos para las APIs enteras.
- Suite completa: 447 tests aprobados; cobertura global 96.93 % (97 % redondeado), todos los módulos de Trends al 100 %.
- La matriz temporal exhaustiva existente se mantiene en los tests públicos de distancia. Cada API nueva verifica ambos motivos de rechazo sin repetir toda esa matriz; no se prueban detalles internos del helper.
- Los tests nuevos cubren aumentos, reducciones, igualdad, ceros, exactitud/tipo entero, valores superiores a la precisión entera de float, repetibilidad y ausencia de mutaciones.
- Las tres APIs comparten solamente una utilidad interna de lunes consecutivos. WeeklyAnalysis permanece intacto, sin modelos adicionales ni framework genérico.
- Este incremento describe diferencias entre datos suministrados. No determina relevancia, descanso real, cierre calendario o cobertura histórica. Porcentajes, series, ventanas, TrainingType trends e Insights quedan fuera.
