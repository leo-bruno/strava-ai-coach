# Validación offline del cambio absoluto de distancia semanal

Fecha: 29 de septiembre de 2026.

API: `src.trends.distance.weekly_running_distance_change(previous, current) -> float`. Devuelve current menos previous, en metros sin redondear. Exige lunes consecutivos separados por siete días calendario; rechaza fechas inválidas con ValueError. No evalúa cierre calendario, completitud, relevancia ni dirección.

## Método y resultado

Se utilizaron exclusivamente las 24 fechas de observaciones semanales ya registradas en `strava_snapshot_2026-09-28.json`. La utilidad local reconstruye sus WeeklyAnalysis y compara únicamente pares existentes separados por siete días. La ordenación para recorrer la muestra pertenece a esta utilidad de auditoría, no a la API de producción. No se crean observaciones para semanas ausentes ni se filtra por cierre calendario.

El oráculo agrupa las Run fuente por año/semana ISO local y suma sus literales de distancia con Decimal, sin reutilizar los límites ni sumas semanales de Analytics. Las diferencias esperadas se calculan restando esos totales fuente. También se contrastan los totales de ambas observaciones.

**23/23 pares coincidentes**, con tolerancia relativa 1e-12 y absoluta 1e-9 m. Diferencia máxima absoluta frente al oráculo: 3,637978807091713e-12 m. Producción no redondea ni ajusta los resultados.

SHA-256 original, verificado antes y después y coincidente con la auditoría anterior: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`. Captura intacta.

| Semana anterior | Semana actual | Metros anteriores fuente | Metros actuales fuente | Cambio independiente (m) | Cambio float (m) |
|---|---|---:|---:|---:|---:|
| 2026-04-20 | 2026-04-27 | 22512.8 | 10078.2 | -12434.6 | -12434.599999999999 |
| 2026-04-27 | 2026-05-04 | 10078.2 | 23702.1 | 13623.9 | 13623.899999999998 |
| 2026-05-04 | 2026-05-11 | 23702.1 | 21407.8 | -2294.3 | -2294.2999999999993 |
| 2026-05-11 | 2026-05-18 | 21407.8 | 17316.7 | -4091.1 | -4091.0999999999985 |
| 2026-05-18 | 2026-05-25 | 17316.7 | 25695.7 | 8379.0 | 8379.0 |
| 2026-05-25 | 2026-06-01 | 25695.7 | 0 | -25695.7 | -25695.7 |
| 2026-06-01 | 2026-06-08 | 0 | 25888.3 | 25888.3 | 25888.300000000003 |
| 2026-06-08 | 2026-06-15 | 25888.3 | 28989.9 | 3101.6 | 3101.5999999999985 |
| 2026-06-15 | 2026-06-22 | 28989.9 | 10057.0 | -18932.9 | -18932.9 |
| 2026-06-22 | 2026-06-29 | 10057.0 | 31246.6 | 21189.6 | 21189.6 |
| 2026-06-29 | 2026-07-06 | 31246.6 | 35607.5 | 4360.9 | 4360.9000000000015 |
| 2026-07-06 | 2026-07-13 | 35607.5 | 36571.5 | 964.0 | 964.0 |
| 2026-07-13 | 2026-07-20 | 36571.5 | 26281.2 | -10290.3 | -10290.3 |
| 2026-07-20 | 2026-07-27 | 26281.2 | 41238.7 | 14957.5 | 14957.499999999996 |
| 2026-07-27 | 2026-08-03 | 41238.7 | 21190.3 | -20048.4 | -20048.399999999998 |
| 2026-08-03 | 2026-08-10 | 21190.3 | 19115.9 | -2074.4 | -2074.399999999998 |
| 2026-08-10 | 2026-08-17 | 19115.9 | 0 | -19115.9 | -19115.9 |
| 2026-08-17 | 2026-08-24 | 0 | 0 | 0 | 0.0 |
| 2026-08-24 | 2026-08-31 | 0 | 0 | 0 | 0.0 |
| 2026-08-31 | 2026-09-07 | 0 | 15495.9 | 15495.9 | 15495.9 |
| 2026-09-07 | 2026-09-14 | 15495.9 | 17096.0 | 1600.1 | 1600.1000000000004 |
| 2026-09-14 | 2026-09-21 | 17096.0 | 39094.8 | 21998.8 | 21998.800000000003 |
| 2026-09-21 | 2026-09-28 | 39094.8 | 0 | -39094.8 | -39094.8 |

## Reproducción

```sh
.venv/bin/python -m local_validation.validate_weekly_distance_change local_validation/strava_snapshot_2026-09-28.json
```

El detalle local se conserva en `weekly_distance_change_results.json`, ignorado por Git igual que la captura.

## Tests y límites

- Trends: 18 tests aprobados, incluidos aumentos, reducciones, ceros, fracciones, fechas inválidas, cambio de año, períodos con DST, ausencia de mutaciones y repetibilidad.
- Suite completa: 435 tests aprobados; cobertura global de líneas y ramas 96.84 % (97 % redondeado). Nuevo módulo: 100 %.
- La validación comprueba exclusivamente aritmética entre observaciones existentes. No afirma que las semanas estén completas o cerradas, ni evalúa cobertura histórica. Una observación cero no acredita descanso.
- WeeklyAnalysis no cambia. No se introducen modelos, dependencias, porcentajes, cambios de conteo/tiempo, ventanas, secuencias en producción ni reglas de Insights.
