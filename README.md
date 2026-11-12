# semana12-CyberDetective

Participación Semana 12 — Programación Asistida de Aplicaciones (USFQ).
Agent Skill **`incident-investigator`** para investigar logs CSV sintéticos de autenticación y
seguridad con alertas justificadas por fila.

| Entregable | Descripción |
|---|---|
| [`incident-investigator/SKILL.md`](incident-investigator/SKILL.md) | Skill: description, activación / no activación, procedimiento, formato de salida, límites. |
| [`incident-investigator/references/detection-rules.md`](incident-investigator/references/detection-rules.md) | Reglas R1–R4, convenciones de ventana, duplicados, severidad y falsos positivos. |
| [`incident-investigator/scripts/analyze_logs.py`](incident-investigator/scripts/analyze_logs.py) | Opcional: verificador de solo lectura (stdlib, sin red, redacta tokens). |
| `.claude/skills/incident-investigator/` | Copia instalada para Claude Code (idéntica). |
| [`hallazgos.md`](hallazgos.md) | Informe con evidencia por fila y verificación manual. |
| [`comparacion.md`](comparacion.md) | Experimento sin skill / con skill en sesiones independientes. |
| [`respuestas.md`](respuestas.md) | Skill vs. plugin y Ralph Loop. |
| [`evidencias/`](evidencias/README.md) | Trazas reales de Claude Code (A explícita, B contextual, C negativo, M5) y capturas. |
| `logs_sinteticos.csv` | Original, sin modificar (SHA-256 `7d8219e9…b5da8`). |

Uso del verificador:

```bash
python incident-investigator/scripts/analyze_logs.py logs_sinteticos.csv
```
