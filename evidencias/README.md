# Evidencias de activación

## Instalación (Claude Code)

Claude Code descubre los skills de proyecto en `.claude/skills/<nombre>/SKILL.md`.

- La copia que se evalúa está en `incident-investigator/`.
- La copia instalada es idéntica y está en `.claude/skills/incident-investigator/`. Se puede comprobar con `diff -r incident-investigator .claude/skills/incident-investigator`.
- Versión de la CLI usada: `2.1.318`. Modelo: `claude-opus-5-5`.

Cada prueba se ejecutó como una **sesión nueva e independiente** con la CLI no interactiva,
guardando la traza completa de eventos:

```bash
claude -p "<prompt>" --model claude-opus-5-5 \
  --allowedTools "Read,Grep,Glob,Skill,Bash(python *),Bash(python3 *)" \
  --disallowedTools "Write,Edit,WebFetch,WebSearch" \
  --output-format stream-json --verbose > trazas/<prueba>.jsonl
```

Las trazas `*.jsonl` son la salida real de la CLI. Los `*.md` son resúmenes generados por
[`sanitizar_y_resumir.py`](sanitizar_y_resumir.py), que **solo** hace lo siguiente:

- sustituye el valor de `token=` por `[REDACTED]`;
- sustituye las rutas locales del equipo por `<REPO>`, `<SIN_SKILL>`, `<CON_SKILL>` y `<HOME>`;
- elimina del evento `init` los campos de entorno ajenos a la prueba (servidores MCP, plugins, rutas de memoria, etc.).

No se editó ningún otro contenido.

## Resultados

| Prueba | Prompt | ¿Skill disponible? (`init.skills`) | ¿Se activó? | Qué se **vio** en la traza | Archivo |
|---|---|---|---|---|---|
| **A — explícita** | «Utiliza incident-investigator para investigar logs_sinteticos.csv y entrega hallazgos con filas de evidencia.» | Sí | **Sí** | 1.ª herramienta: `Skill {"skill":"incident-investigator"}` → `Launching skill`. Después, `Read .claude/skills/incident-investigator/references/detection-rules.md`. | [activacion_explicita.md](activacion_explicita.md) · [trazas/A_explicita.md](trazas/A_explicita.md) |
| **B — contextual** | «Revisa estos registros de autenticación… ¿Ves intentos sospechosos, cambios no aprobados o posibles secretos expuestos? Cita las filas…» (sin nombrar el skill) | Sí | **Sí** | 1.ª herramienta: `Skill {"skill":"incident-investigator"}`, invocada sin que el prompt la nombre. Luego `Read …/detection-rules.md`. | [activacion_contextual.md](activacion_contextual.md) · [trazas/B_contextual.md](trazas/B_contextual.md) |
| **C — control negativo** | «Muéstrame cuántos eventos hay por hora en este CSV; no investigues incidentes ni clasifiques amenazas.» | Sí | **No** ✔ | Solo `Glob` + `Bash` (conteo con Python). Ninguna llamada a `Skill` ni lectura de `SKILL.md`/`detection-rules.md`. Respuesta: 63 eventos (01 h) y 30 (02 h), comprobado con `awk`. | [control_negativo.md](control_negativo.md) · [trazas/C_negativo.md](trazas/C_negativo.md) |
| M5 sin skill | Prompt de la Misión 5 | **No** (0 skills, `--disable-slash-commands`) | — | Exploración libre con `cut/sort/grep`. | [trazas/M5_sin_skill.md](trazas/M5_sin_skill.md) |
| M5 con skill | Prompt de la Misión 5 | Sí | **Sí** (sin nombrarlo) | `Skill` → `Read detection-rules.md` → `Read CSV`. | [trazas/M5_con_skill.md](trazas/M5_con_skill.md) |

### Lo que vi y lo que infiero

- **Visto:** la secuencia de `tool_use` de cada traza: la llamada a la herramienta `Skill`, su resultado `Launching skill: incident-investigator` y la lectura explícita de `references/detection-rules.md`, con su ruta. Que el modelo nombre el skill en su respuesta **no** se usa como prueba.
- **Inferido:**
  - Que el contenido de `SKILL.md` entró en el contexto al activarse. La herramienta `Skill` lo inyecta y la traza solo muestra «Launching skill».
  - Que esto produjo el comportamiento posterior: leer la referencia, el formato de tabla y redactar el token. Esa es exactamente la instrucción del `SKILL.md`, y no aparece en la sesión sin skill.
- En A y B, el agente intentó ejecutar el script opcional como verificación cruzada. El modo no interactivo pidió una aprobación que nadie podía dar, porque encadenó el comando con `sed`/PowerShell. Por eso el análisis de esas sesiones es manual. El script se ejecutó aparte y coincide (ver `hallazgos.md`).

## Misión 4 — ¿hizo falta ajustar la `description`?

**No.** B activó el skill sin nombrarlo y C no lo activó, que era el resultado deseado,
así que no se cumplió ninguna de las dos condiciones de ajuste y no se repitió la prueba.
La `description` ya incluía desde el principio:

- **qué hace** y **sobre qué materiales**: CSV con las columnas `timestamp, ip, user, event, result, detail`;
- **señales positivas**: investigar, auditar, intentos sospechosos, escalada, secretos filtrados, evidencia por fila;
- **límites**: «NO lo uses para conteos, estadísticas, agrupaciones por hora, gráficos… ni para logs que no sean de autenticación/seguridad».

La frase «agrupaciones por hora» del bloque NO se escribió pensando en el control negativo.
Es la razón más probable de que C no lo activara, aunque es una inferencia: no se probó
una variante sin esa frase.

## Capturas de pantalla

Como complemento de las trazas textuales, las capturas de sesiones interactivas de Claude
Code (Prueba A, B y C repetidas en la app) se guardan en esta carpeta con estos nombres:

- `activacion_explicita.png`
- `activacion_contextual.png`
- `control_negativo.png`
