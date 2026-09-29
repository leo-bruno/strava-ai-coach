# Validación offline del conteo semanal por TrainingType

Fecha: 29 de septiembre de 2026.

Captura normalizada: `strava_snapshot_2026-09-28.json`. Se comprobaron 89 actividades, 59 Run y 24 semanas locales de Europe/Madrid, sin red ni deduplicación.

## Método independiente

Se revisaron los 32 nombres distintos de las Run y se asignó una etiqueta esperada a cada nombre exacto en `weekly_structure_name_labels.json`, sin ejecutar el clasificador para generar esas etiquetas. La revisión aplica el contrato determinista existente; no infiere el esfuerzo real del entrenamiento. Un nombre desconocido en la tabla hace fallar la auditoría.

El oráculo agrupa los registros fuente por año/semana ISO de su fecha local y cuenta las etiquetas revisadas. No utiliza el clasificador, las expresiones regulares, los límites ni los selectores de producción. Se compara cada categoría y cada semana contra Activities → WeeklyAnalysis, además de reconciliar el total con running_activity_count.

SHA-256 de la captura antes y después: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

SHA-256 de las etiquetas: `271dd222ee727c42ed48f7119abfb08538f3422b1e3f27010ffdaf9d632f7206`. Ambos archivos permanecen idénticos byte a byte durante la validación.

## Resultado

24/24 semanas coincidentes, 0 diferencias. Las seis categorías están presentes en todas las semanas. Las cinco semanas sin Run tienen seis conteos cero. La suma de categorías coincide con running_activity_count en 24/24 semanas y suma 59 en el conjunto.

| TrainingType | Revisión independiente | Analytics |
|---|---:|---:|
| Easy | 20 | 20 |
| Long | 11 | 11 |
| Tempo | 2 | 2 |
| Intervals | 8 | 8 |
| Race | 1 | 1 |
| Other | 17 | 17 |

| Lunes local | Easy | Long | Tempo | Intervals | Race | Other | Run |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-04-20 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| 2026-04-27 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| 2026-05-04 | 0 | 0 | 0 | 0 | 0 | 4 | 4 |
| 2026-05-11 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| 2026-05-18 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| 2026-05-25 | 0 | 1 | 0 | 0 | 0 | 3 | 4 |
| 2026-06-01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-06-08 | 2 | 1 | 1 | 0 | 0 | 0 | 4 |
| 2026-06-15 | 2 | 1 | 0 | 1 | 0 | 0 | 4 |
| 2026-06-22 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| 2026-06-29 | 2 | 1 | 0 | 1 | 0 | 0 | 4 |
| 2026-07-06 | 2 | 1 | 0 | 1 | 0 | 0 | 4 |
| 2026-07-13 | 2 | 1 | 0 | 1 | 0 | 0 | 4 |
| 2026-07-20 | 2 | 1 | 0 | 0 | 1 | 0 | 4 |
| 2026-07-27 | 2 | 1 | 0 | 1 | 0 | 0 | 4 |
| 2026-08-03 | 1 | 1 | 0 | 0 | 0 | 0 | 2 |
| 2026-08-10 | 1 | 0 | 0 | 1 | 0 | 0 | 2 |
| 2026-08-17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-08-31 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-09-07 | 0 | 1 | 0 | 1 | 0 | 0 | 2 |
| 2026-09-14 | 1 | 0 | 1 | 0 | 0 | 0 | 2 |
| 2026-09-21 | 1 | 1 | 0 | 1 | 0 | 0 | 3 |
| 2026-09-28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Reproducción

Desde la raíz del repositorio:

```sh
.venv/bin/python -m local_validation.validate_weekly_structure local_validation/strava_snapshot_2026-09-28.json local_validation/weekly_structure_name_labels.json
```

La captura, las etiquetas manuales y `weekly_structure_results.json` permanecen locales e ignorados por Git. La utilidad requiere ambos archivos de entrada y puede ejecutarse con otras capturas y sus etiquetas revisadas.

## Tests y limitaciones

- 211 tests específicos pasan: 104 de Weekly Analytics y modelos semanales, más 107 del clasificador existente.
- Suite completa configurada: 409 passed; cobertura global de líneas y ramas 96,72 % (97 % redondeado). Nuevo cálculo, constructor semanal y modelos semanales: 100 %.
- Se añadieron 26 casos: 21 del nuevo cálculo, 4 de inmutabilidad del contrato y 1 de composición/reconciliación; se adaptaron los tests anteriores al campo obligatorio.
- El nombre genérico que menciona «intervalos» permanece en Other porque no coincide con las etiquetas reconocidas por el clasificador. No se amplió ni modificó la clasificación.
- El intervalo es [20 abril, 5 octubre de 2026); la última semana seguía abierta al extraer. Ausencia de Run no demuestra descanso ni integridad del historial.
- La auditoría conserva todos los registros, incluidos posibles duplicados de subida. No mide intensidad fisiológica ni garantiza que el nombre describa la sesión real.
- La muestra no sustituye los tests de DST, fronteras, ambigüedad, duplicados y otros deportes. No se calcularon distancia ni moving time por categoría.
