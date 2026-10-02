# Validación offline del porcentaje de moving time sobre historial

Fecha: 2 de octubre de 2026.

## Alcance y reproducción

Se reutilizó la captura local `strava_snapshot_2026-09-28.json`, sin modificarla
ni recuperar datos nuevos. Se reconstruyeron las mismas 24 WeeklyAnalysis con
el constructor existente, las actividades originales y la timezone de la captura,
utilizando únicamente las fechas semanales observadas.

```sh
.venv/bin/python -m local_validation.validate_moving_time_percentage_history local_validation/strava_snapshot_2026-09-28.json
.venv/bin/python -m pytest src/trends src/models/weekly_running_moving_time_percentage_change_unit_test.py -q
.venv/bin/python -m pytest --cov=src --cov-report=term -q
```

El oráculo independiente agrupa las Run fuente por semana ISO local y suma
moving_time_seconds como enteros, sin reutilizar selectores ni agregadores de
Analytics. Cada total coincide exactamente con la WeeklyAnalysis reconstruida.

## Resultados

| Entrada | Resultados |
| --- | ---: |
| Normal: 24 observaciones, 23 pares | 23 |
| Inversa | 23, idénticos |
| Permutada determinísticamente | 23, idénticos |
| Sin 29/06/2026 | 21 |
| Sin 29/06/2026 ni 06/07/2026 | 20 |

Los 23 resultados son WeeklyRunningMovingTimePercentageChange: 19 valores float
definidos y 4 None. Cada value coincide exactamente con la función escalar
weekly_running_moving_time_percentage_change. Para base positiva, el contraste
independiente `100 * (current - previous) / previous` sobre los totales fuente
coincide exactamente: error máximo 0.0 puntos porcentuales, sin tolerancias ni
redondeos. El resultado es un porcentaje, no segundos.

| Clase | Transición de 2026 | value |
| --- | --- | --- |
| Positivo | 27/04 → 04/05 | 155.28150134048258 |
| Negativo | 20/04 → 27/04 | -57.16582452916858 |
| 0.0 con base positiva | No existe en la captura; cubierto en tests | 0.0 |
| Descenso a cero | 25/05 → 01/06 | -100.0 |
| Base cero | 01/06 → 08/06 | None |

Los otros tres None corresponden a 17/08 → 24/08 y 24/08 → 31/08 (0 → 0),
y 31/08 → 07/09 (0 → positivo). Todos mantienen su objeto resultado.
None significa exclusivamente porcentaje indefinido por base cero; no significa
hueco, dato desconocido, error ni ausencia de cambio. Las cinco observaciones
cero conservan sus transiciones válidas.

Las expectativas de pares se construyeron independientemente desde las fechas
fuente buscando sucesores a siete días. Retirar 29/06 elimina 22/06 → 29/06
y 29/06 → 06/07, sin crear 22/06 → 06/07. Retirar además 06/07 elimina
06/07 → 13/07, sin crear 22/06 → 13/07. Los pares restantes mantienen fechas
y valores esperados; el hueco no produce objeto alguno, tampoco uno con None.

Se verificaron los campos de las WeeklyAnalysis originales, incluida su
estructura por tipo, identidad de objetos y orden de cada entrada, sin mutaciones.
La salida es una tuple y los tres órdenes de entrada producen resultados iguales.

SHA-256 original, antes y después:

`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`

## Tests y estado del producto

27 tests nuevos: 8 del modelo y 19 de la API. Cubren campos, tipos, igualdad,
inmutabilidad, ausencia de lógica del modelo, vacío/singleton, varias semanas,
las seis clases de porcentaje, resultado None presente, fechas, tuple y tipo
específico, igualdad escalar, ausencia de redondeos, orden inverso/desordenado,
huecos, errores de normalización, repetibilidad y ausencia de mutaciones.

Pasan los 230 tests de Trends y los 8 del nuevo modelo (238 en total).
La suite completa configurada pasa con 683 tests. Cobertura global combinada
de líneas y ramas: 97,40 %; todos los módulos de Trends y los seis modelos
temporales de volumen: 100 %.

Los seis resultados temporales de volumen están implementados y cuentan con
tests y validación offline por incremento: distancia, conteo y moving time,
absolutos y porcentuales. Trends V1 sigue PARCIAL: quedan pendientes la auditoría
final del conjunto y el cierre formal. Esta validación no realiza esa auditoría.

No hay nuevas decisiones arquitectónicas. Se mantienen las limitaciones de
operar sobre observaciones suministradas sin certificar cobertura, completitud
ni cierre calendario. Una semana cero no acredita descanso real.
