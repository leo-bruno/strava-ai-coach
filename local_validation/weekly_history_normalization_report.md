# Validación de normalización del historial semanal

Fecha: 1 de octubre de 2026.

Se reconstruyeron únicamente las 24 observaciones de WeeklyAnalysis cuyas fechas
ya constan en la captura local del 28 de septiembre, usando las actividades
suministradas y Europe/Madrid. La secuencia cronológica registrada en la captura
sirvió de referencia independiente. No se evalúan cobertura ni cierre calendario.

| Comprobación | Resultado |
| --- | --- |
| Entrada normal | 24 observaciones, orden esperado e identidad conservada |
| Entrada inversa | La misma secuencia de 24 objetos |
| Permutación determinista (índices pares seguidos de impares) | La misma secuencia de 24 objetos |
| Retirada en memoria del 2026-06-29 | 23 observaciones; la fecha permanece ausente |
| Duplicación en memoria del 2026-06-29 | ValueError; entrada intacta |
| Observaciones con cero Run | Se conservan las cinco |
| Campos, estructura por tipo y colecciones de entrada | Sin mutaciones |

Fechas con cero Run: 2026-06-01, 2026-08-17, 2026-08-24, 2026-08-31 y
2026-09-28. Esto describe las observaciones suministradas, no descanso real.

SHA-256 antes y después, coincidente con la evidencia original:
`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

Verificación automatizada: 90 tests de Trends, incluidos 23 nuevos; suite completa
de 507 tests aprobados, cobertura global de líneas y ramas 97,14 %. history.py
alcanza 100 %. Las comparaciones existentes siguen pasando.

Reproducción desde la raíz del repositorio:

```sh
.venv/bin/python -m local_validation.validate_weekly_history_normalization local_validation/strava_snapshot_2026-09-28.json
```

La utilidad solo lee la captura e imprime los resultados. Las modificaciones de
las colecciones para probar eliminación y duplicación se realizan en memoria.
