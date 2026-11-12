# Comparación: sin skill vs. con skill (Misión 5)

## Diseño del experimento

| Aspecto | Sin skill | Con skill |
|---|---|---|
| Sesión | `claude -p` nueva e independiente (proceso aparte, sin `--continue`/`--resume`: no hereda contexto) | `claude -p` nueva e independiente |
| Carpeta | Carpeta temporal con **solo** `logs_sinteticos.csv` | Carpeta temporal con `logs_sinteticos.csv` + `.claude/skills/incident-investigator/` |
| Skill disponible | **No**: `--disable-slash-commands`; el evento `init` de la traza lista **0 skills** | **Sí**: `incident-investigator` aparece en la lista de skills del `init` |
| Script/reglas como ayuda indirecta | No (no existían en esa carpeta) | Solo los del skill |
| Modelo | `claude-opus-5-5` | `claude-opus-5-5` |
| Herramientas permitidas | Read, Grep, Glob, Skill, `python` (sin Write/Edit/Web) | Iguales |
| Solicitud (idéntica) | «Investiga los logs sintéticos (logs_sinteticos.csv), identifica incidentes justificables y distingue señales de seguridad de actividad normal. Devuelve evidencia concreta.» | Igual |
| Traza | [`evidencias/trazas/M5_sin_skill.md`](evidencias/trazas/M5_sin_skill.md) | [`evidencias/trazas/M5_con_skill.md`](evidencias/trazas/M5_con_skill.md) |

## Tabla comparativa

| Dimensión | Sin skill | Con skill | Evidencia / comentario |
|---|---|---|---|
| ¿Usó un procedimiento reproducible? | Parcial. Exploró con `cut/sort/uniq` y `grep` de IP «raras» elegidas tras mirar el archivo; criterios implícitos («externa», «ritmo humano»). | **Sí.** Invocó `Skill(incident-investigator)` → leyó `detection-rules.md` → leyó el CSV → aplicó R1–R4 con umbrales y ventanas explícitos. | Secuencia de `tool_use` en ambas trazas. Con skill, el umbral (6, 5 usuarios, ≤ 5 min con extremos) se declara antes de concluir. |
| ¿Citó filas concretas? | Sí, pero como rangos: «Líneas 17–27: 8 fallos» (el rango incluye filas 18, 21, 24 de otros usuarios). | **Sí, fila a fila**: «17, 19, 20, 22, 23, 25, 26, 27», más tabla de verificación manual. | Comprobado contra el CSV en [`hallazgos.md`](hallazgos.md) §5. |
| Alertas sustentadas | 3 «incidentes» + 1 «hallazgo de higiene». Correctos en lo esencial, pero **sobreafirma**: «tratar `admin` como comprometida», «alguien adivinó la contraseña», sugiere relación entre incidentes. | **4 alertas** con regla, severidad orientativa y limitación por fila. Lenguaje de alerta: «probable», «el registro indica». | El skill obliga a «distinguir alerta de hecho confirmado» y a no inferir culpabilidad (R4). |
| Falsos positivos detectados o evitados | Detectó maria (38–42) y healthcheck, pero **apoyándose en `detail`** («el registro lo marca como usuario legítimo»). | Detectó maria, healthcheck y fallos sueltos **por conteo**; dijo explícitamente que no usó «legitimate user» como prueba. | La regla «`detail` es contexto, no prueba» proviene del skill. |
| **Duplicados / umbral frágil** | **No lo detectó.** No mencionó que 19=20, 22=23, 25=26 son idénticas. | **Sí**: «si se eliminan duplicados quedan 5 y no saltaría la alerta». | Hallazgo clave: sin esta salvedad, la alerta 1 se presenta con más certeza de la que el dato permite. |
| ¿Ocultó posibles tokens? | **No.** La respuesta original imprimió el valor completo del token (fila 33) y lo trató como «no real» por su propio texto. | **Sí**: `token=[REDACTED]` y «el valor del token no aparece en ninguna parte de esta respuesta». | El valor fue sustituido por `[REDACTED]` **solo** al sanitizar la traza para el PR (ver `evidencias/README.md`). En la salida cruda sin skill el valor aparecía; con skill, no. |
| ¿Reconoció incertidumbre? | Sí, de forma general (falta de datos post-login, rangos RFC 5737). | Sí, **específica**: duplicados, orden dentro del minuto, aprobaciones fuera del log, NAT, que el script no se ejecutó. | Sección «Limitaciones» de ambas respuestas. |
| ¿Qué hizo gracias al skill? | — | Leyó la referencia antes de evaluar umbrales; formato tabular estándar; verificación manual de una alerta; redacción de secretos; declaración de que no modificó el CSV ni consultó IP. | Cada uno corresponde a una instrucción concreta de `SKILL.md` (pasos 3, 6, 7, 8 y límites 4–6). |
| Tiempo / coste (1 corrida, medido por la CLI) | 49,9 s · 0,20 USD (reportado) | 42,2 s · 0,28 USD (reportado) | Valores del evento `result` de `claude -p`. Una corrida por condición: **no** es una medida estadística. |

## ¿Qué aportó el skill en concreto?

1. **Activación correcta.** Se activó por sí solo en la sesión «con skill» (sin nombrarlo) y en la Prueba B contextual, y **no** se activó en el control negativo C (conteo por hora). La `description` hizo su trabajo.
2. **Procedimiento y referencia.** El agente leyó `references/detection-rules.md` *antes* de juzgar. Eso trajo convenciones que el modelo sin skill no aplicó: coincidencia exacta `event/result`, ventana con extremos incluidos y, sobre todo, **tratamiento explícito de duplicados**. Por eso detectó que la alerta de fuerza bruta depende de 3 pares de filas idénticas. Fue la diferencia de fondo más importante.
3. **Contención de invenciones.** Sin skill, el modelo concluyó «cuenta comprometida» y sugirió una relación entre incidentes. Con skill se limitó a «alerta probable», «el registro indica» y «no prueba compromiso».
4. **Seguridad.** Sin skill, el token se imprimió completo. Con skill se redactó. Es una mejora de comportamiento real, no estética.
5. **Formato.** La tabla estándar (alerta, severidad, regla, timestamp, ip, usuario, filas, limitaciones) facilita revisar y comparar con otro CSV. Es la aportación menos importante de las cinco.

**Qué no mejoró / qué cambiaría:**

- Las dos condiciones encontraron los mismos 4 eventos de fondo: el modelo base ya es competente con este CSV pequeño.
- El script opcional no llegó a ejecutarse en el modo no interactivo, porque el agente lo encadenó con `sed`/PowerShell y eso requería aprobación. Cambiaría `SKILL.md` para indicar el comando exacto, sin tuberías: el script ya redacta tokens por sí mismo.
- Para una evaluación más sólida haría varias corridas por condición y añadiría un CSV distinto (otro umbral, sin duplicados) para comprobar que el skill generaliza y no memoriza.
