# Validación offline del cambio absoluto de moving time sobre historial

Fecha: 2 de octubre de 2026.

## Alcance y reproducción

Se reutilizó la captura local `strava_snapshot_2026-09-28.json`, sin modificarla
ni recuperar datos nuevos. Las 24 WeeklyAnalysis se reconstruyeron con el
constructor existente, las actividades originales y la timezone de la captura.
Solo se utilizaron las fechas semanales observadas en esa captura.

```sh
.venv/bin/python -m local_validation.validate_moving_time_history local_validation/strava_snapshot_2026-09-28.json
.venv/bin/python -m pytest src/trends src/models/weekly_running_moving_time_change_unit_test.py -q
.venv/bin/python -m pytest --cov=src --cov-report=term -q
```

La captura no almacena totales semanales de moving time. El oráculo independiente
agrupa las Run fuente por semana ISO local y suma sus moving_time_seconds como
enteros, sin reutilizar selectores ni agregadores de Analytics. Cada total
reconcilia exactamente con la WeeklyAnalysis reconstruida.

## Resultados

| Entrada | Resultados |
| --- | ---: |
| Normal: 24 observaciones, 23 pares | 23 |
| Inversa | 23, idénticos |
| Permutada determinísticamente | 23, idénticos |
| Sin 29/06/2026 | 21 |
| Sin 29/06/2026 ni 06/07/2026 | 20 |

Los 23 resultados son WeeklyRunningMovingTimeChange y todos los value son int
en segundos. Coinciden exactamente con weekly_running_moving_time_change,
con current.running_moving_time_seconds menos previous.running_moving_time_seconds
y con las diferencias de los totales fuente independientes. Error máximo: 0 s.
No hay conversiones a float, otras unidades, redondeos ni None.

| Caso | Transición de 2026 | value en segundos |
| --- | --- | ---: |
| Positivo | 27/04 → 04/05 | 5792 |
| Negativo | 20/04 → 27/04 | -4978 |
| Cero, también 0 → 0 | 17/08 → 24/08 | 0 |
| Hacia semana cero | 25/05 → 01/06 | -9775 |
| Desde semana cero | 01/06 → 08/06 | 10392 |

La muestra incluye las seis clases solicitadas, con cero y 0 → 0 compartiendo
el ejemplo. No contiene un cambio cero entre dos totales positivos; ese caso
permanece cubierto mediante tests.

Las cinco observaciones cero (01/06, 17/08, 24/08, 31/08 y 28/09) mantienen
sus transiciones válidas. Las restantes transiciones relacionadas con cero son
10/08 → 17/08: -8098 s; 24/08 → 31/08: 0 s;
31/08 → 07/09: 6214 s; 21/09 → 28/09: -15120 s.

Las expectativas de pares se construyeron desde las fechas fuente buscando
sucesores a siete días. Retirar 29/06 elimina 22/06 → 29/06 y 29/06 → 06/07,
sin crear 22/06 → 06/07. Retirar también 06/07 elimina además 06/07 → 13/07,
sin crear 22/06 → 13/07. Los resultados restantes conservan fechas y valores.
Una semana ausente produce ausencia de transición, nunca un resultado None.

Se verificaron campos de las WeeklyAnalysis originales, incluida la estructura
por tipo, identidad de objetos y orden de cada entrada, sin mutaciones.
La salida es una tuple.

SHA-256 original, antes y después:

`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`

## Tests y estado del producto

25 tests nuevos: 5 del modelo y 20 de la API. Cubren campos, tipos, igualdad,
inmutabilidad, ausencia de lógica en el modelo, vacío/singleton, varias semanas,
signos, transiciones cero, fechas, tuple, tipo específico, exactitud escalar,
enteros superiores a la precisión exacta de float, orden inverso/desordenado,
huecos sin puentes, errores de normalización, repetibilidad y ausencia de mutaciones.

Pasan los 211 tests de Trends y los 5 del nuevo modelo (216 en total).
La suite completa configurada pasa con 656 tests. Cobertura global combinada
de líneas y ramas: 97,36 %; nuevo modelo y todos los módulos de Trends: 100 %.

Trends V1 sigue PARCIAL. Únicamente quedan WeeklyRunningMovingTimePercentageChange
y su API plural. No se introducen nuevas decisiones arquitectónicas. Se conserva
la limitación de validar aritmética sobre observaciones suministradas sin
certificar cobertura, completitud ni cierre calendario. Una semana cero no
acredita descanso real.
