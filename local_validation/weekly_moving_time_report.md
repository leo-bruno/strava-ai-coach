# Validación offline de running_moving_time_seconds

Fecha: 29 de septiembre de 2026.

Captura: `strava_snapshot_2026-09-28.json`, representación normalizada de Activity devuelta por StravaClient, no respuestas HTTP originales. `moving_time_seconds` conserva el campo `moving_time` validado por el mapper. No se ha convertido, estimado, sustituido ni modificado ningún valor.

SHA-256 antes y después: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

Se agruparon independientemente los registros Run por año/semana ISO de start_date convertido a Europe/Madrid, sin reutilizar límites ni funciones de agregación de Analytics. Se sumaron los segundos fuente y se compararon con Activities → WeeklyAnalysis. No se deduplicaron registros.

**Resultado:** 89 actividades, 59 Run, 24 semanas coincidentes, 0 diferencias. Total fuente y total semanal: **186774 segundos**. Cinco semanas sin Run devuelven 0. La captura permanece idéntica byte a byte.

## Reproducción

Desde la raíz del repositorio:

```sh
.venv/bin/python -m local_validation.validate_weekly_moving_time local_validation/strava_snapshot_2026-09-28.json
```

El detalle local se conserva en `weekly_moving_time_results.json` (ignorado por Git, igual que la captura).

| Lunes local | Run | Segundos fuente | Segundos Analytics |
|---|---:|---:|---:|
| 2026-04-20 | 3 | 8708 | 8708 |
| 2026-04-27 | 1 | 3730 | 3730 |
| 2026-05-04 | 4 | 9522 | 9522 |
| 2026-05-11 | 3 | 8554 | 8554 |
| 2026-05-18 | 3 | 6542 | 6542 |
| 2026-05-25 | 4 | 9775 | 9775 |
| 2026-06-01 | 0 | 0 | 0 |
| 2026-06-08 | 4 | 10392 | 10392 |
| 2026-06-15 | 4 | 12204 | 12204 |
| 2026-06-22 | 2 | 4234 | 4234 |
| 2026-06-29 | 4 | 12876 | 12876 |
| 2026-07-06 | 4 | 14466 | 14466 |
| 2026-07-13 | 4 | 14133 | 14133 |
| 2026-07-20 | 4 | 10167 | 10167 |
| 2026-07-27 | 4 | 16365 | 16365 |
| 2026-08-03 | 2 | 8802 | 8802 |
| 2026-08-10 | 2 | 8098 | 8098 |
| 2026-08-17 | 0 | 0 | 0 |
| 2026-08-24 | 0 | 0 | 0 |
| 2026-08-31 | 0 | 0 | 0 |
| 2026-09-07 | 2 | 6214 | 6214 |
| 2026-09-14 | 2 | 6872 | 6872 |
| 2026-09-21 | 3 | 15120 | 15120 |
| 2026-09-28 | 0 | 0 | 0 |

## Límites de la validación

El intervalo de la captura es [20 abril, 5 octubre de 2026), Europe/Madrid. La última semana, iniciada el 28 de septiembre, seguía abierta al extraer. Los ceros describen ausencia de registros seleccionados, no demuestran descanso ni historial completo. La captura contiene valores ya mapeados: esta auditoría verifica la agregación sobre esos valores, sin volver a consultar Strava. DST y fronteras exactas se comprueban mediante tests deterministas.

## Tests

- Weekly Analytics: 78 passed.
- Mapper de Activity: 39 passed.
- Suite completa configurada: 383 passed; cobertura global 97 %, nuevo cálculo 100 %.
- Tests adicionales de la utilidad de captura: 7 passed.
