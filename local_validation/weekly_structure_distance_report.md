# Validación offline de distancia semanal por TrainingType

Fecha: 29 de septiembre de 2026.

Captura normalizada: `strava_snapshot_2026-09-28.json`. Se comprobaron 89 actividades, 59 Run y 24 semanas locales de Europe/Madrid, sin consultas de red ni deduplicación.

## Método independiente y precisión

Se reutilizan las etiquetas por nombre revisadas en el incremento de conteo (`weekly_structure_name_labels.json`), sin regenerarlas con el clasificador. El oráculo agrupa los registros fuente por año/semana ISO local y suma sus distancias con Decimal, leyendo los literales decimales directamente del JSON. No utiliza el clasificador, los límites, selectores ni agregadores de producción para obtener los resultados esperados.

Producción conserva float y acumula la distancia en el mismo recorrido que el conteo, con una clasificación por entrada seleccionada. No introduce redondeos, ajustes, conversiones a Decimal ni validación defensiva. El modelo continúa sin cálculos ni validación.

La comparación de auditoría utiliza tolerancia relativa 1e-12 y absoluta 1e-9 metros. Solo se usan para comprobar igualdad numérica; no alteran los resultados. Los conteos se comparan con igualdad exacta.

SHA-256 original, coincidente con el incremento anterior y conservado después de esta auditoría: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

SHA-256 de las etiquetas, también conservado: `271dd222ee727c42ed48f7119abfb08538f3422b1e3f27010ffdaf9d632f7206`.

## Resultado global

Las 24 semanas coinciden por categoría con la suma independiente; las 24 reconcilian distancia y conteo con WeeklyAnalysis. Se mantienen los 59 registros Run y los conteos aprobados. Las cinco semanas sin Run tienen seis categorías con conteo y distancia cero.

| Tipo | Actividades | Metros fuente (Decimal) | Metros Analytics (float sin redondear) |
|---|---:|---:|---:|
| Easy | 20 | 140582.6 | 140582.6 |
| Long | 11 | 132624.6 | 132624.59999999998 |
| Tempo | 2 | 13375.3 | 13375.3 |
| Intervals | 8 | 65105.5 | 65105.5 |
| Race | 1 | 6201.0 | 6201.0 |
| Other | 17 | 110697.9 | 110697.9 |

Total decimal independiente: **468586.9 m**. Suma de running_distance_meters de las 24 semanas: **468586.9 m**. Suma global de categorías: **468586.89999999997 m**.

Diferencia global categorías menos totales semanales: `-5.820766091346741e-11` m. Máxima diferencia semanal absoluta: `3.637978807091713e-12` m. Son diferencias de representación/acumulación float dentro de la tolerancia, sin correcciones de datos.

## Reconciliación semanal

Cada fila pasó además la comparación de las seis categorías con Decimal. El detalle por tipo y semana está en el JSON local.

| Lunes local | Run | Suma por categorías (m) | running_distance_meters | Diferencia (m) |
|---|---:|---:|---:|---:|
| 2026-04-20 | 3 | 22512.8 | 22512.8 | 0.0 |
| 2026-04-27 | 1 | 10078.2 | 10078.2 | 0.0 |
| 2026-05-04 | 4 | 23702.1 | 23702.1 | 0.0 |
| 2026-05-11 | 3 | 21407.8 | 21407.8 | 0.0 |
| 2026-05-18 | 3 | 17316.699999999997 | 17316.7 | -3.637978807091713e-12 |
| 2026-05-25 | 4 | 25695.7 | 25695.7 | 0.0 |
| 2026-06-01 | 0 | 0.0 | 0.0 | 0.0 |
| 2026-06-08 | 4 | 25888.300000000003 | 25888.300000000003 | 0.0 |
| 2026-06-15 | 4 | 28989.899999999998 | 28989.9 | -3.637978807091713e-12 |
| 2026-06-22 | 2 | 10057.0 | 10057.0 | 0.0 |
| 2026-06-29 | 4 | 31246.6 | 31246.6 | 0.0 |
| 2026-07-06 | 4 | 35607.5 | 35607.5 | 0.0 |
| 2026-07-13 | 4 | 36571.5 | 36571.5 | 0.0 |
| 2026-07-20 | 4 | 26281.2 | 26281.2 | 0.0 |
| 2026-07-27 | 4 | 41238.7 | 41238.7 | 0.0 |
| 2026-08-03 | 2 | 21190.3 | 21190.3 | 0.0 |
| 2026-08-10 | 2 | 19115.9 | 19115.9 | 0.0 |
| 2026-08-17 | 0 | 0.0 | 0.0 | 0.0 |
| 2026-08-24 | 0 | 0.0 | 0.0 | 0.0 |
| 2026-08-31 | 0 | 0.0 | 0.0 | 0.0 |
| 2026-09-07 | 2 | 15495.9 | 15495.9 | 0.0 |
| 2026-09-14 | 2 | 17096.0 | 17096.0 | 0.0 |
| 2026-09-21 | 3 | 39094.8 | 39094.8 | 0.0 |
| 2026-09-28 | 0 | 0.0 | 0.0 | 0.0 |

## Reproducción

Desde la raíz del repositorio:

```sh
.venv/bin/python -m local_validation.validate_weekly_structure local_validation/strava_snapshot_2026-09-28.json local_validation/weekly_structure_name_labels.json
```

El detalle se conserva en `weekly_structure_distance_results.json`. La captura, las etiquetas y ambos resultados históricos permanecen locales e ignorados por Git.

## Tests y limitaciones

- 216 tests específicos pasan: 109 de Weekly Analytics y modelos semanales, más 107 del clasificador existente.
- Suite completa configurada: 414 passed; cobertura global de líneas y ramas 96.75 % (97 % redondeado). Cálculo de estructura, constructor y modelos semanales: 100 %.
- Se ampliaron los tests existentes a distancia y se añadieron cinco casos: distribución fraccionaria entre seis categorías, distancia cero en Easy y Other, reconciliación de varias semanas e inmutabilidad del nuevo campo.
- Se mantienen clasificación única, categorías ausentes, exclusiones, límites locales, DST, cambio de año, duplicados y ausencia de mutaciones.
- El intervalo es [20 abril, 5 octubre de 2026); la última semana seguía abierta al extraer. Ceros no demuestran descanso ni historial completo.
- Las etiquetas describen nombres según el contrato existente; Other sigue explícito. No se infiere intensidad ni se deduplican posibles subidas repetidas.
- Solo se añadió distancia por tipo. Moving time por categoría y las demás capacidades excluidas siguen pendientes.
