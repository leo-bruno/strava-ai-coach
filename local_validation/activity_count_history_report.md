# Validación de conteo absoluto sobre historial

Fecha: 1 de octubre de 2026.

Se reconstruyeron WeeklyAnalysis únicamente para las 24 fechas de observación
existentes en la captura del 28 de septiembre. El oráculo utiliza fechas fuente
y restas enteras entre los conteos semanales registrados, sin recurrir a la nueva
API para construir expectativas.

| Entrada | Resultados |
| --- | ---: |
| Normal | 23 |
| Inversa | Los mismos 23 |
| Permutación determinista | Los mismos 23 |
| Sin 29/06/2026 | 21 |
| Sin 29/06/2026 ni 06/07/2026 | 20 |

Todos los value son int y coinciden exactamente con la función escalar y con
el cálculo independiente. Diferencia máxima: 0 actividades, sin tolerancias.
No se crean puentes 22/06 → 06/07 ni 22/06 → 13/07 tras retirar observaciones.

| Transición | Cambio en actividades |
| --- | ---: |
| 27/04 → 04/05 | +3 |
| 20/04 → 27/04 | -2 |
| 11/05 → 18/05 | 0 |
| 25/05 → 01/06 (hacia cero) | -4 |
| 01/06 → 08/06 (desde cero) | +4 |
| 17/08 → 24/08 (cero a cero) | 0 |

Las cinco observaciones con cero Run participan normalmente en sus siete
transiciones distintas. No se introducen None ni conversiones a float.
Se conservaron campos, estructura por tipo, identidad y orden de las entradas.

SHA-256 antes y después, coincidente con el original:
`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

Tests: 19 nuevos de API y 4 del modelo; 172 tests de Trends y 4 del modelo
aprobados. Suite completa: 604 aprobados. Cobertura global de líneas y ramas:
97,29 %; activity_count.py y el nuevo modelo: 100 %.

Reproducción desde la raíz:

```sh
.venv/bin/python -m local_validation.validate_activity_count_history local_validation/strava_snapshot_2026-09-28.json
```

La captura solo se lee. No se evalúan cobertura, completitud ni cierre calendario.
