"""Sanitiza trazas stream-json reales de Claude Code y genera un resumen legible.

Únicas transformaciones aplicadas (sobre cada cadena del JSON):
  * el valor que sigue a `token=` (caracteres [A-Za-z0-9_-]) -> [REDACTED]
  * rutas locales del equipo -> <REPO>, <SIN_SKILL>, <CON_SKILL>, <HOME>
  * del evento `init` se eliminan campos de entorno ajenos a la prueba
    (servidores MCP, plugins, rutas de memoria/socket, listas de comandos...).
El resto de la traza (herramientas invocadas, entradas, resultados, respuesta) se conserva.

Uso: python sanitizar_y_resumir.py <carpeta_raw> <carpeta_salida>
"""
import json, re, sys
from pathlib import Path

DROP = {"mcp_servers", "plugins", "memory_paths", "messaging_socket_path", "scratchpad_path",
        "additional_directories", "powershell_path", "startup_timing", "slash_commands",
        "terminal_slash_commands", "agents", "tools", "capabilities", "apiKeySource", "original_cwd"}
TOKEN = re.compile(r"token=(?!\[REDACTED\])[A-Za-z0-9_\-]+")
SEP = r"[/\\]+"
PATH = re.compile(r"(?:[A-Za-z]:|/[a-z])" + SEP + r"Users" + SEP + r"[^/\\\s\"']+((?:" + SEP + r"[^/\\\s\"'`]+)*)", re.I)

def fix_path(m):
    tail = m.group(1).replace(chr(92), "/")
    for marker, name in (("semana12-CyberDetective", "<REPO>"), ("scratchpad/sin_skill", "<SIN_SKILL>"),
                         ("scratchpad/con_skill", "<CON_SKILL>")):
        i = tail.find(marker)
        if i >= 0:
            return name + tail[i + len(marker):]
    return "<HOME>/…"

def clean(x):
    if isinstance(x, str):
        return PATH.sub(fix_path, TOKEN.sub("token=[REDACTED]", x))
    if isinstance(x, list):
        return [clean(i) for i in x]
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    return x

def summarize(events):
    out = []
    for o in events:
        t = o.get("type")
        if t == "system" and o.get("subtype") == "init":
            sk = o.get("skills", [])
            out.append(f"- **init**: model=`{o.get('model')}`, cwd=`{o.get('cwd')}`, versión Claude Code "
                       f"`{o.get('claude_code_version')}`. ¿`incident-investigator` en la lista de skills "
                       f"disponibles? **{'sí' if 'incident-investigator' in sk else 'no'}** ({len(sk)} skills)")
        elif t == "assistant":
            for c in o["message"]["content"]:
                if c["type"] == "tool_use":
                    inp = json.dumps(c["input"], ensure_ascii=False).replace("`", "'")
                    out.append(f"- **tool_use `{c['name']}`** → `{inp[:240]}`")
        elif t == "user" and isinstance(o["message"].get("content"), list):
            for c in o["message"]["content"]:
                if c.get("type") == "tool_result":
                    cc = c.get("content")
                    s = cc if isinstance(cc, str) else json.dumps(cc, ensure_ascii=False)
                    s = s[:170].replace("\n", " ⏎ ").replace("`", "'")
                    out.append(f"    - resultado: `{s}`")
        elif t == "result":
            out.append(f"- **fin**: turnos={o.get('num_turns')}, duración={o.get('duration_ms')} ms, "
                       f"coste reportado por la CLI={o.get('total_cost_usd')} USD")
            out.append("\n## Respuesta final del agente (texto íntegro)\n\n" + (o.get("result") or ""))
    return "\n".join(out)

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
for p in sorted(src.glob("*.jsonl")):
    events = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("type") == "system" and o.get("subtype") == "init":
            for k in DROP:
                o.pop(k, None)
        events.append(clean(o))
    (dst / p.name).write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")
    (dst / p.with_suffix(".md").name).write_text(
        f"# Traza resumida: {p.stem}\n\nGenerada automáticamente desde `{p.name}` (traza real "
        f"`claude -p --output-format stream-json`, sanitizada).\n\n## Secuencia de herramientas\n\n"
        f"{summarize(events)}\n", encoding="utf-8")
    print("ok", p.name)
