#!/usr/bin/env python3
"""Verificador auxiliar (opcional) para el skill incident-investigator.

Aplica las reglas de references/detection-rules.md sobre un CSV compatible
(timestamp, ip, user, event, result, detail). Solo lectura, solo biblioteca
estándar, sin red. Nunca imprime valores de token: usa [REDACTED].

Uso:
    python analyze_logs.py ruta/al.csv [--json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

REQUIRED = ["timestamp", "ip", "user", "event", "result", "detail"]
WINDOW = timedelta(minutes=5)
BRUTE_THRESHOLD = 6
SPRAY_USERS = 5
SECRET_RE = re.compile(r"(token|password|secret|apikey|key)=([^;\s]*)", re.IGNORECASE)


def redact(text: str) -> str:
    return SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)


def load(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            sys.exit(f"Columnas faltantes: {missing}")
        rows = []
        # encabezado = fila 1, primer dato = fila 2
        for row_no, rec in enumerate(reader, start=2):
            rec = {k: (v or "").strip() for k, v in rec.items()}
            rec["row"] = row_no
            rec["ts"] = datetime.fromisoformat(rec["timestamp"])
            rows.append(rec)
    rows.sort(key=lambda r: (r["ts"], r["row"]))  # orden estable
    return rows


def is_(r: dict, event: str, result: str) -> bool:
    return r["event"] == event and r["result"] == result


def best_window(items: list[dict], key=lambda xs: len(xs)) -> list[dict]:
    """Ventana deslizante [i..j] con t_j - t_i <= 5 min que maximiza key."""
    best: list[dict] = []
    j = 0
    for i in range(len(items)):
        j = max(j, i)
        while j + 1 < len(items) and items[j + 1]["ts"] - items[i]["ts"] <= WINDOW:
            j += 1
        cand = items[i : j + 1]
        if key(cand) > key(best):
            best = cand
    return best


def analyze(rows: list[dict]) -> dict:
    alerts, discarded = [], []
    fails = [r for r in rows if is_(r, "login", "failed")]

    # R1 fuerza bruta
    by_pair: dict[tuple, list] = defaultdict(list)
    for r in fails:
        by_pair[(r["ip"], r["user"])].append(r)
    for (ip, user), items in by_pair.items():
        win = best_window(items)
        if len(win) >= BRUTE_THRESHOLD:
            last = win[-1]["ts"]
            succ = [r for r in rows if is_(r, "login", "success") and r["ip"] == ip
                    and r["user"] == user and timedelta(0) <= r["ts"] - last <= WINDOW]
            dup = Counter((r["timestamp"], r["ip"], r["user"], r["event"], r["result"], r["detail"]) for r in win)
            alerts.append({
                "rule": "R1 fuerza bruta probable", "ip": ip, "users": [user],
                "start": win[0]["timestamp"], "end": win[-1]["timestamp"],
                "rows": [r["row"] for r in win], "count": len(win),
                "success_after_rows": [r["row"] for r in succ],
                "identical_rows": sum(c for c in dup.values() if c > 1),
                "count_if_deduplicated": len(dup),
            })
        elif len(win) >= 2:
            discarded.append({"reason": f"{len(win)} login/failed (ip={ip}, user={user}) en ventana < umbral {BRUTE_THRESHOLD}",
                              "rows": [r["row"] for r in win]})

    # R2 spraying
    by_ip: dict[str, list] = defaultdict(list)
    for r in fails:
        by_ip[r["ip"]].append(r)
    for ip, items in by_ip.items():
        win = best_window(items, key=lambda xs: len({r["user"] for r in xs}))
        users = sorted({r["user"] for r in win})
        if len(users) >= SPRAY_USERS:
            alerts.append({"rule": "R2 password spraying probable", "ip": ip, "users": users,
                           "start": win[0]["timestamp"], "end": win[-1]["timestamp"],
                           "rows": [r["row"] for r in win], "count": len(users)})

    # R3 token
    for r in rows:
        if "token=" in r["detail"]:
            alerts.append({"rule": "R3 token potencialmente expuesto", "ip": r["ip"], "users": [r["user"]],
                           "start": r["timestamp"], "end": r["timestamp"], "rows": [r["row"]],
                           "detail": redact(r["detail"])})

    # R4 escalada
    for r in rows:
        if is_(r, "role_change", "success") and "approved=false" in r["detail"]:
            ctx = [x["row"] for x in rows if x["row"] != r["row"] and x["user"] == r["user"]
                   and timedelta(0) <= r["ts"] - x["ts"] <= WINDOW]
            alerts.append({"rule": "R4 escalada no autorizada según el registro", "ip": r["ip"],
                           "users": [r["user"]], "start": r["timestamp"], "end": r["timestamp"],
                           "rows": [r["row"]], "detail": redact(r["detail"]), "context_rows": ctx})

    hc = [r["row"] for r in rows if r["event"] == "healthcheck"]
    if hc:
        discarded.append({"reason": "healthcheck no es login/failed (monitorización)", "rows": hc})

    return {
        "rows": len(rows), "start": rows[0]["timestamp"] if rows else None,
        "end": rows[-1]["timestamp"] if rows else None,
        "events": dict(Counter(f'{r["event"]}/{r["result"]}' for r in rows)),
        "alerts": alerts, "discarded": discarded,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = analyze(load(a.csv))
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    print(f"Filas de datos: {res['rows']}  Rango: {res['start']} -> {res['end']}")
    print(f"Eventos: {res['events']}\n")
    print("ALERTAS")
    for i, al in enumerate(res["alerts"], 1):
        print(f" {i}. {al['rule']} | ip={al['ip']} | users={','.join(al['users'])} | "
              f"{al['start']} -> {al['end']} | filas={al['rows']}")
        for k in ("count", "success_after_rows", "identical_rows", "count_if_deduplicated", "detail", "context_rows"):
            if k in al:
                print(f"      {k}: {al[k]}")
    print("\nDESCARTADOS / FALSOS POSITIVOS")
    for d in res["discarded"]:
        print(f" - {d['reason']} | filas={d['rows']}")


if __name__ == "__main__":
    main()
