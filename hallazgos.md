# Hallazgos — investigación de `logs_sinteticos.csv`

Generado con el skill `incident-investigator` (Prueba A, traza en
[`evidencias/trazas/A_explicita.md`](evidencias/trazas/A_explicita.md)) y **verificado a mano**
contra el CSV original (sección 5). El script opcional
`incident-investigator/scripts/analyze_logs.py` se ejecutó aparte como verificación
cruzada y da las mismas 4 alertas y los mismos descartes.

> Son **alertas justificadas por regla**, no conclusiones forenses. No se atribuye
> culpabilidad ni autoría. El CSV no fue modificado
> (SHA-256 `7d8219e9f8c9dd995be0c2dc038f4f7e67f0f12446b4fdc07fadf508befb5da8`, igual al entregado).

## 1. Resumen del archivo

| Campo | Valor |
|---|---|
| Archivo | `logs_sinteticos.csv` |
| Filas de datos | 93 (filas 2–94; encabezado = fila 1) |
| Rango temporal | 2026-11-05 01:01 → 02:29 (UTC−05:00) |
| Granularidad | minuto (sin segundos) |
| Columnas verificadas | `timestamp, ip, user, event, result, detail` |
| Eventos | 56 `login/success`, 28 `login/failed`, 6 `healthcheck/success`, 1 `debug/warning`, 1 `access/denied`, 1 `role_change/success` |
| Reglas | R1–R4 de [`incident-investigator/references/detection-rules.md`](incident-investigator/references/detection-rules.md) |

## 2. Tabla de alertas

| # | alerta | severidad orientativa | regla | timestamp (inicio–fin) | ip | usuario(s) | filas/evidencia | limitaciones |
|---|---|---|---|---|---|---|---|---|
| 1 | Fuerza bruta probable **+ éxito posterior** | Alta | R1 | 01:14 – 01:18 | 198.51.100.77 | admin | Filas **17, 19, 20, 22, 23, 25, 26, 27** = 8 `login/failed` en 4 min (umbral 6). Éxito posterior: **fila 28** `login/success` 01:19 (1 min tras el último fallo) | 3 pares de filas idénticas (19=20, 22=23, 25=26). Con granularidad de minuto no se puede saber si son duplicados de ingesta o intentos reales. Si se deduplicaran quedarían **5** fallos (< 6) y la regla **no** se cumpliría. El éxito posterior no prueba compromiso de la cuenta. |
| 2 | Password spraying probable | Media | R2 | 02:01 – 02:03 | 203.0.113.89 | ana, carlos, luisa, diego, maria, sofia | Filas **67, 68, 70, 71, 73, 74** = `login/failed` contra **6 usuarios distintos** en 2 min (umbral 5) | Ningún `login/success` desde esa IP en los 5 min siguientes. Los éxitos de carlos (fila 69) y luisa (fila 72) vienen de 192.0.2.10, otra IP: no cuentan. |
| 3 | Token potencialmente expuesto | Alta | R3 | 01:27 | 192.0.2.44 | api_service | **Fila 33**: `debug/warning`, `detail` = `token=[REDACTED]; debug output` | No se puede saber si el token es válido ni si se usó. |
| 4 | Escalada no autorizada **según el registro** | Alta | R4 | 01:50 | 203.0.113.42 | guest | **Fila 59**: `role_change/success`, `role=user->admin; approved=false` | El registro no indica quién ejecutó el cambio ni si hubo aprobación fuera del log. No se infiere culpabilidad. |

## 3. Señales contextuales (no son alertas)

| Señal | Filas | Por qué no es alerta |
|---|---|---|
| `guest` desde 203.0.113.42 recibe `access/denied` a `resource=/admin` un minuto antes de la alerta 4 | 57 | `access/denied` no es ninguna regla; solo da contexto temporal a la fila 59. |
| `detail` = "login after multiple failures" | 28 | Texto libre: no se usa como prueba. La alerta 1 se sostiene en el conteo de `event/result`. |

## 4. Falsos positivos descartados

| Caso | Filas | Por qué **no** es alerta |
|---|---|---|
| maria desde 192.0.2.25: 3 fallos y luego éxito | 38, 39, 41 (+ éxito 42) | Solo **3** `login/failed` del mismo (ip, user) en 2 min: la regla R1 exige **≥ 6** en ≤ 5 min. Ver explicación abajo. |
| healthbot desde 192.0.2.200, 6 eventos seguidos | 78, 80, 81, 82, 83, 84 | Son `healthcheck/success`, **no** `login/failed` (coincidencia exacta de `event` y `result`). Es monitorización programada; no cuenta para R1 ni R2 aunque sea repetitivo. |
| Fallos sueltos `ordinary login` desde 192.0.2.10–.13 | 3, 7, 14, 24, 31, 34, 46, 47, 51, 60, 87 | Ningún par (ip, user) supera 2 fallos en 5 min; ninguna IP falla contra ≥ 5 usuarios en 5 min (p. ej. 192.0.2.12 falla contra 3 usuarios a lo largo de ~40 min). |

### Por qué los 3 fallos aislados **no** son fuerza bruta

Las filas 38 (01:35), 39 (01:36) y 41 (01:37) son `192.0.2.25, maria, login, failed`.
Son 3 eventos, la mitad del umbral de R1 (6 en ≤ 5 min desde la misma IP al mismo
usuario). Después, la fila 42 (01:38) es un `login/success` de la misma IP y usuario,
un patrón compatible con alguien que escribió mal su contraseña tres veces. El texto
"mistyped password" / "legitimate user" de `detail` **no** se usa para descartarlo:
lo descarta el conteo. Si el umbral se bajara a 3 se dispararían falsos positivos
sobre usuarios normales; por eso la regla fija 6.

## 5. Verificación manual contra el CSV original

Comprobado **a mano** con `cat -n logs_sinteticos.csv` (el número que imprime `cat -n`
coincide con el número de fila del CSV, encabezado = 1), sin confiar en el texto del modelo:

**Alerta 1 (R1):**

| Fila | timestamp | ip | user | event | result |
|---|---|---|---|---|---|
| 17 | 01:14 | 198.51.100.77 | admin | login | failed |
| 19 | 01:15 | 198.51.100.77 | admin | login | failed |
| 20 | 01:15 | 198.51.100.77 | admin | login | failed |
| 22 | 01:16 | 198.51.100.77 | admin | login | failed |
| 23 | 01:16 | 198.51.100.77 | admin | login | failed |
| 25 | 01:17 | 198.51.100.77 | admin | login | failed |
| 26 | 01:17 | 198.51.100.77 | admin | login | failed |
| 27 | 01:18 | 198.51.100.77 | admin | login | failed |
| 28 | 01:19 | 198.51.100.77 | admin | login | **success** |

- Conteo: 8 filas `login/failed` ≥ 6 ✔. Ventana: 01:18 − 01:14 = 4 min ≤ 5 ✔.
- Éxito posterior: 01:19 − 01:18 = 1 min ≤ 5 ✔ → severidad Alta.
- Las filas 18, 21 y 24 intercaladas son de otras IP/usuarios (192.0.2.13 carlos, 192.0.2.12 maria ×2) y **no** se cuentan.

**Alerta 2 (R2):** filas 67 (ana), 68 (carlos), 70 (luisa), 71 (diego), 73 (maria),
74 (sofia), todas `203.0.113.89, login, failed`, entre 02:01 y 02:03 → 6 usuarios
distintos ≥ 5 ✔, ventana 2 min ✔.

## 6. Limitaciones e incertidumbre

- **Duplicados (alerta 1):** el resultado de R1 depende de si las filas idénticas son
  intentos reales. Las reglas indican no inventar una deduplicación; se cuentan todas
  y se declara que con deduplicación la alerta no se sostendría.
- **Granularidad de minuto:** el orden dentro de un mismo minuto es el del archivo.
- **Sin contexto externo:** no hay políticas, aprobaciones fuera del log, ni información
  de NAT/IP compartidas. `guest` no tiene `login` registrado antes del cambio de rol.
- **IP de documentación (RFC 5737):** no se consultaron ni se tratan como infraestructura real.
- **Datos sintéticos:** no permiten conclusiones sobre personas reales.
