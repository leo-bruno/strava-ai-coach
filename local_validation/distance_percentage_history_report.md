# Validación de porcentajes temporales de distancia

Fecha: 1 de octubre de 2026.

Se reconstruyeron únicamente las 24 observaciones con fechas ya existentes en
la captura del 28 de septiembre. El oráculo usa fechas fuente y porcentajes
calculados independientemente con Decimal sobre sus totales semanales.

| Entrada | Resultados |
| --- | ---: |
| Normal | 23 |
| Inversa | Los mismos 23 |
| Permutación determinista | Los mismos 23 |
| Sin 29/06/2026 | 21 |
| Sin 29/06/2026 ni 06/07/2026 | 20 |

Se verificaron 19 valores definidos y 4 None. Cada resultado coincide exactamente
con weekly_running_distance_percentage_change. La diferencia máxima frente al
oráculo es 5.684341886080802e-14 puntos porcentuales; tolerancia exclusivamente
de auditoría relativa 1e-12 y absoluta 1e-10. Producción no redondea.

| Transición | value (%) |
| --- | ---: |
| 27/04 → 04/05 | 135.1818777162588 |
| 20/04 → 27/04 | -55.233467183113596 |
| 25/05 → 01/06 | -100.0 |
| 01/06 → 08/06 | None |
| 17/08 → 24/08 | None |
| 24/08 → 31/08 | None |
| 31/08 → 07/09 | None |

No existe 0.0 % definido en esta captura; está cubierto en tests. Las transiciones
0 → 0 producen objetos con None, no 0.0. Las bases cero conservan sus cuatro
resultados. En cambio, los huecos introducidos eliminan conexiones sin crear
objetos: no aparecen 22/06 → 06/07 ni 22/06 → 13/07.

Campos de WeeklyAnalysis, estructura por tipo, identidad y orden de las entradas
permanecen intactos. SHA-256 antes y después, coincidente con el original:
`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

Tests: 18 nuevos de API y 7 del modelo. Pasan 153 tests de Trends y 7 del modelo;
581 en la suite completa. Cobertura global de líneas y ramas 97,24 %; distance.py
y el nuevo modelo alcanzan el 100 %.

Reproducción desde la raíz:

```sh
.venv/bin/python -m local_validation.validate_distance_percentage_history local_validation/strava_snapshot_2026-09-28.json
```

La captura solo se lee; las variantes se construyen en memoria. Esta validación
no certifica cobertura, completitud ni cierre calendario.
