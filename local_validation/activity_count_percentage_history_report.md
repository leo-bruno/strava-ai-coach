# Validación offline del porcentaje de activity count sobre historial

Fecha: 2 de octubre de 2026.

## Alcance y reproducción

Se reutilizó la captura local `strava_snapshot_2026-09-28.json`. Se reconstruyeron
las 24 WeeklyAnalysis mediante el constructor existente a partir de las actividades
originales y la timezone de la captura. Los conteos reconstruidos coinciden con
los totales semanales fuente. No se recuperaron datos nuevos ni se modificó la captura.

```sh
.venv/bin/python -m local_validation.validate_activity_count_percentage_history local_validation/strava_snapshot_2026-09-28.json
.venv/bin/python -m pytest src/trends src/models/weekly_running_activity_count_percentage_change_unit_test.py -q
.venv/bin/python -m pytest --cov=src --cov-report=term -q
```

## Resultados

| Entrada | Resultados |
| --- | ---: |
| Normal: 24 observaciones, 23 pares | 23 |
| Inversa | 23, idénticos |
| Permutada determinísticamente | 23, idénticos |
| Sin 29/06/2026 | 21 |
| Sin 29/06/2026 ni 06/07/2026 | 20 |

Los 23 resultados son WeeklyRunningActivityCountPercentageChange: 19 tienen
value definido de tipo float y 4 tienen value=None. Todos coinciden exactamente
con weekly_running_activity_count_percentage_change. Para base positiva, el
contraste independiente `100 * (current - previous) / previous` sobre los conteos
fuente coincide exactamente: error máximo 0.0 puntos porcentuales. No se usan
tolerancias ni redondeos.

| Clase | Transición de 2026 | Conteos | value |
| --- | --- | --- | --- |
| Positivo | 27/04 → 04/05 | 1 → 4 | 300.0 |
| Negativo | 20/04 → 27/04 | 3 → 1 | -66.66666666666667 |
| Sin cambio con base positiva | 11/05 → 18/05 | 3 → 3 | 0.0 |
| Descenso a cero | 25/05 → 01/06 | 4 → 0 | -100.0 |
| Base cero | 01/06 → 08/06 | 0 → 4 | None |

Las otras tres transiciones con None son 17/08 → 24/08 (0 → 0),
24/08 → 31/08 (0 → 0) y 31/08 → 07/09 (0 → 2).
Todas conservan su objeto resultado. None significa exclusivamente porcentaje
indefinido por base cero; una semana ausente no genera un resultado.

Las expectativas de pares se construyeron independientemente desde las fechas
fuente buscando sucesores a siete días. Al retirar 29/06 desaparecen
22/06 → 29/06 y 29/06 → 06/07, sin crear 22/06 → 06/07. Al retirar además
06/07 desaparece 06/07 → 13/07, sin crear 22/06 → 13/07. Los pares restantes
conservan sus fechas y valores esperados.

Se verificaron todos los campos de las WeeklyAnalysis originales, incluida la
estructura por tipo, y la identidad y orden de cada entrada, sin mutaciones.
Las cinco observaciones cero participan normalmente. La salida es una tuple.

SHA-256 original, antes y después:

`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`

## Tests y estado del producto

27 tests nuevos: 8 del modelo y 19 de la API. Cubren campos y tipos, igualdad,
inmutabilidad, ausencia de lógica en el modelo, vacío/singleton, todas las clases
de porcentaje, fechas, tuple y tipo concreto, varias transiciones, None presente,
precisión sin redondeos, igualdad escalar, orden, huecos, errores de normalización,
repetibilidad y ausencia de mutaciones.

Pasan los 191 tests de Trends y los 8 del nuevo modelo (199 en total).
La suite completa configurada pasa con 631 tests. Cobertura global combinada de
líneas y ramas: 97,32 %; módulo activity_count, nuevo modelo y todos los módulos
de Trends: 100 %.

Trends V1 sigue PARCIAL. Solo quedan moving time absoluto y porcentual sobre
historial. No se introducen nuevas decisiones arquitectónicas. La validación
confirma aritmética sobre observaciones suministradas; no certifica completitud,
cobertura ni cierre calendario, y una semana cero no acredita descanso real.
