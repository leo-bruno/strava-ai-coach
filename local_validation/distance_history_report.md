# Validación de resultados temporales de distancia absoluta

Fecha: 1 de octubre de 2026.

Las 24 WeeklyAnalysis se reconstruyeron exclusivamente para las fechas de
observación ya registradas en la captura del 28 de septiembre. El oráculo usa
esas fechas y sus totales fuente: sucesores calendario y restas con Decimal.
No se evalúan cobertura ni cierre calendario.

| Entrada | Resultados |
| --- | ---: |
| Normal | 23 |
| Inversa | Los mismos 23 |
| Permutación determinista | Los mismos 23 |
| Sin 29/06/2026 | 21 |
| Sin 29/06/2026 ni 06/07/2026 | 20 |

Fechas de origen/destino y orden coinciden exactamente con las expectativas.
No aparecen puentes 22/06 → 06/07 ni 22/06 → 13/07 tras las eliminaciones.
Cada value es float e idéntico al resultado de weekly_running_distance_change.
La diferencia máxima frente a la resta de totales fuente es
3.637978807091713e-12 m, dentro de la tolerancia exclusivamente de auditoría:
relativa 1e-12, absoluta 1e-9 m. Producción no redondea ni usa tolerancias.

Ejemplos de valores float devueltos, en metros:

| Transición | value |
| --- | ---: |
| 20/04 → 27/04 | -12434.599999999999 |
| 27/04 → 04/05 | 13623.899999999998 |
| 17/08 → 24/08 | 0.0 |

Las cinco observaciones con cero Run coinciden con las de distancia cero y
participan en siete transiciones distintas. Se conservan descensos a cero,
aumentos desde cero y los dos cambios cero del 17/08 → 24/08 y 24/08 → 31/08.

Se verificaron identidad y todos los campos de las observaciones originales,
incluida running_structure_by_type, así como el orden intacto de las entradas.
Los resultados son nuevos objetos de datos; no contienen WeeklyAnalysis.

SHA-256 original verificado antes y después:
`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

Tests: 19 nuevos de API y 4 del modelo; 135 tests de Trends y 4 del modelo
aprobados. Suite completa: 556 aprobados. Cobertura global de líneas y ramas:
97,21 %; distance.py y el modelo: 100 %.

Reproducción desde la raíz:

```sh
.venv/bin/python -m local_validation.validate_distance_history local_validation/strava_snapshot_2026-09-28.json
```

La captura solo se lee; eliminaciones y permutaciones se realizan en memoria.
