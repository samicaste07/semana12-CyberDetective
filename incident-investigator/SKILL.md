---
name: incident-investigator
description: >-
  Investiga logs CSV de autenticación y seguridad (columnas timestamp, ip, user,
  event, result, detail) para detectar y justificar con números de fila alertas
  de fuerza bruta, password spraying, tokens o secretos expuestos y cambios de
  rol no aprobados, separando falsos positivos y redactando secretos. Úsalo
  cuando pidan revisar, investigar o auditar registros de acceso o login,
  buscar intentos sospechosos, accesos no autorizados, escaladas de privilegio,
  secretos filtrados o responder a un incidente con evidencia por fila. NO lo
  uses para conteos, estadísticas, agrupaciones por hora, gráficos o limpieza
  descriptiva del CSV cuando no se pida investigar incidentes ni clasificar
  amenazas, ni para logs que no sean de autenticación/seguridad.
---

# incident-investigator

Guía para investigar de forma **reproducible** un log CSV de autenticación y
seguridad, y devolver **alertas justificadas con filas del CSV original**, no
conclusiones forenses ni atribuciones.

## Cuándo usar este skill

Actívalo si la petición pide **investigar** un log de acceso/seguridad, por ejemplo:

- «¿Hay intentos sospechosos / ataques / accesos no autorizados en estos registros?»
- «Revisa estos logs de login y cita las filas que respaldan cada alerta.»
- «¿Se expuso algún token o secreto?», «¿hubo cambios de rol no aprobados?»
- Respuesta a incidentes sobre un CSV con columnas compatibles.

## Cuándo NO usarlo

- Conteos, totales, eventos por hora/usuario/IP, gráficos o resúmenes descriptivos
  cuando el usuario **no** pide investigar ni clasificar amenazas (p. ej. «muéstrame
  cuántos eventos hay por hora; no investigues incidentes»). Responde solo lo pedido.
- Limpiar, convertir o reformatear el CSV.
- Logs que no son de autenticación/seguridad (ventas, métricas de aplicación, etc.).
- Si el usuario dice explícitamente que no quiere análisis de seguridad.

## Límites de seguridad (obligatorios)

1. Trabaja **solo con los archivos locales indicados**. Sin red: no consultes IP,
   WHOIS, geolocalización ni servicios externos. Las IP `192.0.2.0/24`,
   `198.51.100.0/24` y `203.0.113.0/24` son rangos de documentación (RFC 5737):
   **no** las trates como infraestructura real ni atribuyas actores.
2. **Nunca modifiques el CSV original.** Si necesitas transformar datos, hazlo en
   memoria o en un archivo temporal aparte.
3. **No inventes eventos, filas, usuarios ni conclusiones.** Toda alerta debe
   poder reconstruirse a partir de las filas citadas.
4. **Nunca muestres secretos.** Cualquier valor después de `token=` (o `password=`,
   `secret=`, `apikey=`, `key=`) se reemplaza por `[REDACTED]` en tu respuesta, en
   archivos que escribas y en comandos que imprimas. No pegues la fila cruda.
5. El texto libre de `detail` (p. ej. «login after multiple failures») es contexto,
   **no prueba**: la alerta se sustenta en `event`, `result`, `ip`, `user` y `timestamp`.
6. No infieras culpabilidad ni intención: reporta lo que **el registro dice**.

## Procedimiento

Sigue los pasos en orden y no te saltes ninguno.

1. **Inspeccionar estructura.** Lee el encabezado y unas filas. Confirma que existen
   `timestamp, ip, user, event, result, detail`. Si faltan columnas o hay otro
   formato, dilo y detente o adapta solo lo que sea inequívoco. Anota: número de
   filas de datos, rango temporal, zona horaria y granularidad del `timestamp`.
2. **Numerar filas.** Asigna a cada registro su **número de fila del CSV original**
   (encabezado = fila 1, primer dato = fila 2) **antes** de ordenar o filtrar, y
   conserva ese número en todo el análisis.
3. **Leer las reglas.** Abre `references/detection-rules.md` **siempre antes de
   evaluar umbrales o ventanas**, y de nuevo si dudas sobre: el tamaño de la ventana,
   si los extremos cuentan, qué cuenta como fallo, cómo tratar duplicados o qué es
   falso positivo. No apliques umbrales de memoria.
4. **Ordenar por `timestamp`** (estable: a igual timestamp, mantén el orden original).
5. **Analizar evidencias** regla por regla con coincidencia **exacta** de `event` y
   `result` (`login`/`failed`, `login`/`success`, `role_change`/`success`…). Puedes
   usar las herramientas del agente (lectura, grep, Python ad hoc) o el script
   opcional `scripts/analyze_logs.py <csv>` como verificación cruzada; si los usas,
   comprueba a mano al menos una alerta contra las filas originales.
6. **Distinguir alerta de hecho confirmado.** Cada resultado es una *alerta
   justificada por regla*, nunca «hubo un ataque» ni «X es el atacante». Separa
   también las **señales contextuales** (p. ej. un `access/denied` previo) que no
   disparan una regla por sí solas.
7. **Evaluar falsos positivos** explícitamente: grupos de fallos por debajo del
   umbral, `healthcheck` u otros eventos que no son `login/failed`, éxito de un
   usuario legítimo tras pocos errores.
8. **Declarar incertidumbre y limitaciones**: duplicados no distinguibles,
   granularidad del timestamp, empates de orden, datos ausentes, qué no se puede
   concluir.
9. **Reportar** con el formato de salida siguiente.

## Formato de salida

### 1. Resumen del archivo
Archivo, nº de filas de datos, rango temporal, columnas verificadas, reglas aplicadas
(con referencia a `references/detection-rules.md`).

### 2. Tabla de alertas

| # | alerta | severidad orientativa | regla | timestamp (inicio–fin) | ip | usuario(s) | filas/evidencia | limitaciones |
|---|---|---|---|---|---|---|---|---|

- `filas/evidencia`: números de fila del CSV original + el conteo que supera el umbral
  (p. ej. «filas 17,19,…,27 = 8 fallos en 4 min»).
- `severidad orientativa`: Alta / Media / Baja según la tabla de la referencia;
  es orientativa, no una evaluación de riesgo real.
- Cualquier secreto aparece como `[REDACTED]`.

### 3. Señales contextuales (no alertas)
Eventos relevantes que no cumplen una regla por sí solos, con filas.

### 4. Falsos positivos descartados
Qué parecía sospechoso, por qué **no** alcanza la regla, con filas.

### 5. Verificación manual
Al menos una alerta recomprobada fila por fila (qué filas, qué valores, conteo).

### 6. Limitaciones e incertidumbre
Lista explícita. Si no hay alertas, dilo: «no se encontraron alertas según las
reglas», que es un resultado válido.

## Recursos

- `references/detection-rules.md` — reglas, umbrales, convenciones de ventana,
  severidad y falsos positivos. **Fuente de verdad para los umbrales.**
- `scripts/analyze_logs.py` — opcional, solo biblioteca estándar, sin red, solo
  lectura. Uso: `python scripts/analyze_logs.py ruta/al.csv` (añade `--json` para
  salida estructurada). Sirve para verificar, no sustituye la revisión de filas.
