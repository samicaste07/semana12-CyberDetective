# Reglas de detección — incident-investigator

Fuente de verdad para umbrales y convenciones. Aplica a cualquier CSV con columnas
`timestamp, ip, user, event, result, detail`. Los resultados son **alertas
justificadas**, no conclusiones forenses.

## Convenciones generales

| Convención | Detalle |
|---|---|
| Números de fila | Fila del **CSV original**: encabezado = 1, primer registro = 2. Asignar **antes** de ordenar/filtrar. |
| Orden | Ordenar por `timestamp` (orden estable) antes de revisar ventanas. |
| Ventana | Dura **≤ 5 minutos incluyendo ambos extremos**: `t_fin − t_inicio ≤ 5 min`. Ej.: 01:14:00 y 01:19:00 están en la misma ventana; 01:14:00 y 01:19:01 no. |
| Coincidencia | Contar solo filas cuyo `event` **y** `result` coinciden **exactamente** (sensible a mayúsculas, sin espacios extra). `login/failed` ≠ `healthcheck/success` ≠ `access/denied`. |
| Mismo origen | «Misma IP» = cadena `ip` idéntica. «Mismo usuario» = cadena `user` idéntica. |
| Duplicados | Filas idénticas en todas las columnas **no** se eliminan automáticamente: el log puede tener granularidad de minuto y dos intentos reales pueden coincidir. Cuenta todas las filas y **declara la limitación**, indicando cuántas filas son idénticas y si el resultado cambiaría al deduplicar. No inventes una regla de deduplicación. |
| `detail` | Texto libre: contexto, no prueba. Excepción: la presencia literal de `token=` o `approved=false` sí es el criterio de las reglas R3 y R4. |
| Secretos | Nunca imprimir el valor. Sustituir todo lo que sigue a `token=` (hasta `;`, espacio o fin) por `[REDACTED]`. |
| IP | Rangos de documentación RFC 5737; no consultar ni atribuir. |

## R1 — Fuerza bruta probable

- **Condición:** ≥ **6** filas `event=login`, `result=failed` con la **misma `ip`**
  y el **mismo `user`** dentro de una ventana de ≤ 5 min.
- **Cómo evaluarlo:** para cada par (ip, user), ordena sus fallos y desliza una
  ventana; reporta la ventana máxima (primer y último timestamp, todas las filas).
- **Anotación separada (no es otra alerta):** si existe un `login/success` del
  mismo (ip, user) en los **5 minutos siguientes** al último fallo de la ventana
  (`0 ≤ t_success − t_ultimo_fallo ≤ 5 min`), anótalo como «éxito posterior» con
  su fila. Un éxito posterior **no prueba** compromiso de la cuenta.
- **Severidad orientativa:** Media; **Alta** si hay éxito posterior.

## R2 — Password spraying probable

- **Condición:** filas `login/failed` desde la **misma `ip`** contra **≥ 5 usuarios
  distintos** dentro de una ventana de ≤ 5 min.
- **Reportar:** IP, lista de usuarios, filas, ventana. Indica si alguno de esos
  usuarios tuvo `login/success` desde esa IP en los 5 min siguientes.
- **Severidad orientativa:** Media (Alta si hay éxito posterior desde esa IP).

## R3 — Token potencialmente expuesto

- **Condición:** `detail` contiene la subcadena `token=` (cualquier `event`/`result`).
- **Reportar:** fila, timestamp, ip, user, event, y `detail` con el valor como
  `token=[REDACTED]`. No afirmar que el token sea válido ni que se haya usado.
- **Severidad orientativa:** Alta (exposición de credencial en logs).

## R4 — Escalada no autorizada según el registro

- **Condición:** `event=role_change`, `result=success` y `detail` contiene
  `approved=false`.
- **Reportar:** fila, usuario, rol origen→destino si aparece en `detail`, ip.
  Puede añadirse como **señal contextual** cualquier evento previo del mismo
  usuario/IP (p. ej. `access/denied`), sin convertirlo en alerta.
- **Redacción obligatoria:** «el registro indica un cambio de rol no aprobado»;
  **no** inferir culpabilidad, intención ni quién lo ejecutó.
- **Severidad orientativa:** Alta.

## Falsos positivos y no-alertas

| Caso | Por qué no es alerta |
|---|---|
| < 6 `login/failed` del mismo (ip, user) en 5 min (p. ej. **3 fallos aislados**) | No alcanza el umbral de R1. Reportar como descartado. Un éxito posterior tras pocos errores es compatible con un usuario que se equivocó de contraseña. |
| Fallos de una IP contra < 5 usuarios distintos en 5 min | No alcanza el umbral de R2. |
| `healthcheck` (cualquier `result`) | No es `login/failed`; monitorización programada. No cuenta para R1/R2 aunque sea repetitivo. |
| `access/denied` | No es `login/failed`. Puede ser señal contextual, no alerta por sí solo. |
| `role_change/success` con `approved=true` o sin `approved=` | No cumple R4 (si falta el campo, declararlo como limitación). |
| Mismos fallos a mano con `detail` alarmante | El texto de `detail` no cambia el conteo. |

## Severidad orientativa (resumen)

| Regla | Base | Agravante |
|---|---|---|
| R1 Fuerza bruta | Media | Alta con éxito posterior ≤ 5 min |
| R2 Spraying | Media | Alta con éxito posterior desde la IP |
| R3 Token | Alta | — |
| R4 Escalada | Alta | — |

## Limitaciones que siempre hay que considerar

- Granularidad del `timestamp` (minuto vs. segundo) y empates de orden.
- Filas idénticas (posibles duplicados de ingesta o intentos reales).
- Ausencia de contexto (políticas, aprobaciones fuera del log, NAT/IP compartidas).
- Un log sintético no permite conclusiones sobre personas reales.
