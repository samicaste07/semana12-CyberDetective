# Respuestas — Misión 6: Plugin Detective

## 1. Skill frente a plugin

**Por qué `incident-investigator` es un skill.** Lo que aporta es *conocimiento
procedimental contextual*:

- **cuándo** actuar (la `description`);
- **cómo** investigar (el procedimiento);
- **con qué criterio** (las reglas de `references/`);
- **cómo** reportar (el formato de salida).

El agente lo carga bajo demanda solo cuando la petición encaja; si no, solo ocupa la
línea de su `description`. No necesita ejecutarse ante eventos del entorno (eso sería
un hook) ni dar acceso a un sistema externo (eso sería MCP). Es instrucción + recursos.

**Qué podría empaquetarse en un plugin de Claude Code para distribuirlo:**

| Componente | Ejemplo para este caso |
|---|---|
| Manifiesto | `.claude-plugin/plugin.json` con nombre, versión, autor y descripción. Opcionalmente, un `marketplace.json` para instalarlo con `/plugin install`. |
| Skill | `skills/incident-investigator/` (este mismo `SKILL.md` + `references/` + `scripts/`). |
| Comando | `commands/investigate.md` → `/investigate <csv>`, que invoca el skill de forma explícita y guarda `hallazgos.md`. |
| Hook | `PreToolUse` sobre `Write`/`Edit` que bloquea cualquier escritura en `logs_*.csv` (protege el original). `PostToolUse` o `Stop` que busca `token=` sin `[REDACTED]` en los informes y falla si lo encuentra. |
| Subagente | `agents/evidence-verifier.md`: revisa el informe y recomprueba cada fila citada contra el CSV. |
| MCP (opcional) | Un servidor MCP de solo lectura que exponga un SIEM o almacén de logs real. No se usaría con estos datos sintéticos. |

El plugin **distribuye y versiona** el conjunto. El skill sigue siendo la pieza que
contiene el criterio.

## 2. Ralph Loop (máx. 3 iteraciones)

Idea: repetir el análisis **solo** para corregir errores detectados por
**comprobaciones verificables** (deterministas). En ningún caso se buscan
«más hallazgos».

**Comprobaciones (checks) sobre `hallazgos.md`:**

1. Cada fila citada existe en el CSV (2 ≤ fila ≤ nº de líneas) y sus `ip/user/event/result` coinciden con lo que afirma la alerta.
2. Cada alerta cumple su umbral recontado: R1 ≥ 6 en ≤ 5 min; R2 ≥ 5 usuarios; R3 contiene `token=`; R4 con `approved=false`.
3. No aparece ningún valor tras `token=` distinto de `[REDACTED]`.
4. Hay coincidencia con `scripts/analyze_logs.py --json`: mismas alertas y mismas filas.
5. El hash SHA-256 del CSV no cambió.

**Bucle:**

```
for i in 1..3:
    ejecutar skill → hallazgos.md
    resultados = correr checks 1–5
    si todos pasan: PARAR (éxito)
    si los fallos son idénticos a la iteración anterior: PARAR (sin progreso)
    reintentar pasando SOLO la lista de checks fallidos
    (p. ej. «fila 18 no es admin/failed»), sin permitir añadir filas no verificables
si tras 3 iteraciones falla algún check: PARAR y entregar el informe marcado
    «NO VERIFICADO», con los checks fallidos
```

**Criterio de parada explícito:** todos los checks en verde, **o** 3 iteraciones,
**o** dos iteraciones seguidas con los mismos fallos.

**Cómo se evita fabricar evidencia:**

- El CSV es de solo lectura (check 5 y hook `PreToolUse`).
- La retroalimentación solo contiene fallos de checks, nunca sugerencias de nuevos ataques.
- Una alerta que no supera el check se **elimina o se rebaja** a «señal contextual»; nunca se «arregla» cambiando la fila citada por otra no comprobada.
- El informe final conserva el registro de iteraciones y checks.
