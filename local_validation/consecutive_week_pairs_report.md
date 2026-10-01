# Validación de pares semanales consecutivos

Fecha: 1 de octubre de 2026.

Se utilizaron las 24 fechas de observación existentes en la captura local del
28 de septiembre y sus WeeklyAnalysis reconstruidos mediante Analytics. El
oráculo independiente busca el sucesor calendario de cada fecha fuente; para
las eliminaciones retira las conexiones afectadas de esa expectativa.
No se evalúan cobertura ni cierre calendario.

| Escenario | Observaciones | Pares verificados |
| --- | ---: | ---: |
| Orden normal | 24 | 23 |
| Orden inverso | 24 | Los mismos 23 |
| Permutación determinista | 24 | Los mismos 23 |
| Retirar 2026-06-29 | 23 | 21 |
| Retirar 2026-06-29 y 2026-07-06 | 22 | 20 |
| Vacío | 0 | 0 |
| Singleton | 1 | 0 |

Al retirar el 29 de junio desaparecen 22/06 → 29/06 y 29/06 → 06/07;
no aparece 22/06 → 06/07. Al retirar también el 6 de julio desaparece además
06/07 → 13/07; no aparece 22/06 → 13/07. El resto de conexiones se conserva.

Las observaciones con cero Run del 1 de junio y 17, 24 y 31 de agosto
participan cada una en dos pares originales; la del 28 de septiembre participa
en uno por ser el último extremo suministrado. Ninguna se filtra por sus métricas.

Todos los pares de los cinco escenarios con múltiples observaciones son
aceptados por las seis comparaciones existentes. Esta ejecución es exclusivamente
una comprobación de compatibilidad en la auditoría, no una capacidad nueva de
producción para calcular series.

Verificados los mismos objetos en cada extremo, todos los campos incluida
running_structure_by_type, y el orden y contenido intactos de las entradas.

SHA-256 antes y después, coincidente con el original:
`69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

Tests: 26 nuevos, 116 de Trends aprobados, 533 en la suite completa.
Cobertura global de líneas y ramas: 97,16 %; history.py: 100 %.

Reproducción desde la raíz:

```sh
.venv/bin/python -m local_validation.validate_consecutive_week_pairs local_validation/strava_snapshot_2026-09-28.json
```

La captura solo se lee; las eliminaciones se realizan sobre colecciones en memoria.
