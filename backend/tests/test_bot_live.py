#!/usr/bin/env python3
"""
Test en vivo del bot - envía las preguntas reales de Jorge al API.
Muestra agente usado, fragmento de respuesta, y detecta errores.

Uso:
  python3 tests/test_bot_live.py                          # default: http://localhost
  python3 tests/test_bot_live.py http://192.168.1.26      # URL custom

Desde Docker:
  docker compose exec backend python3 tests/test_bot_live.py http://host.docker.internal
"""

import sys
import json
import time
import urllib.request
import urllib.error

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://192.168.1.26"
USERNAME = "admin"
PASSWORD = "SantoniAdmin2026!"
TIMEOUT  = 120  # seconds per request (LLM can be slow)

# ANSI colors
G = "\033[92m"  # green
R = "\033[91m"  # red
Y = "\033[93m"  # yellow
B = "\033[1m"   # bold
N = "\033[0m"   # reset


def api(method, path, body=None, token=None):
    """Simple HTTP helper (no external deps)."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        return {"_error": e.code, "_detail": err_body}
    except Exception as e:
        return {"_error": str(e)}


def login():
    print(f"Conectando a {BASE_URL} como {USERNAME}...")
    r = api("POST", "/api/auth/login", {
        "username": USERNAME,
        "password": PASSWORD,
        "totp_code": None,
    })
    if "_error" in r:
        print(f"{R}ERROR login: {r}{N}")
        sys.exit(1)
    if r.get("totp_required"):
        print(f"{R}ERROR: TOTP requerido. Este script no soporta 2FA.{N}")
        sys.exit(1)
    token = r.get("access_token", "")
    if not token:
        print(f"{R}ERROR: No se recibió token. Respuesta: {r}{N}")
        sys.exit(1)
    print(f"{G}Login OK{N}\n")
    return token


def chat(token, message, conversation_id=None):
    """Send a chat message and return (agent, response_text, conversation_id)."""
    body = {
        "message": message,
        "conversation_id": conversation_id,
        "file_id": None,
    }
    r = api("POST", "/api/chat/", body, token)
    if "_error" in r:
        return "ERROR", f"HTTP error: {r}", conversation_id
    agent = r.get("agent_used", "???")
    text = r.get("message", "")
    cid = r.get("conversation_id", conversation_id)
    return agent, text, cid


# ── Test definitions ────────────────────────────────────────────────────
# Each group = one conversation. Within a group, follow-ups share conversation_id.
# Format: (message, expected_agent_or_None, bad_patterns_list)

BAD = ["no tienes permisos", "no tengo acceso", "no se encontraron compras para este producto"]
BAD_INV = ["no tengo acceso"]

TESTS = [
    # ── Grupo 1: Follow-ups (moneda, gastos) ──
    {
        "name": "FOLLOW-UPS (dólares, gastos)",
        "queries": [
            ("¿Cuánto se compró de insumos este mes?", "compras_insumos", BAD),
            ("Y en dólares?", "compras_insumos", BAD),
            ("En gastos?", "compras_insumos", BAD),
        ],
    },
    # ── Grupo 2: Órdenes pendientes ──
    {
        "name": "ORDENES PENDIENTES",
        "queries": [
            ("Órdenes de compra pendientes por recepción de insumos del mes de febrero",
             "compras_insumos", BAD),
        ],
    },
    # ── Grupo 3: Inventario y códigos ──
    {
        "name": "INVENTARIO Y CÓDIGOS",
        "queries": [
            ("quisiera saber cuantas cajas de carton quedan en inventario",
             "compras_insumos", BAD_INV),
            ("tienes el codigo de las cajas de carton para cereales",
             "compras_insumos", BAD),
            ("cual es el codigo de caja de carton para cereales",
             "compras_insumos", BAD),
        ],
    },
    # ── Grupo 4: Proveedores y láminas ──
    {
        "name": "PROVEEDORES Y LÁMINAS",
        "queries": [
            ("que proveedores venden laminas de hierro negro",
             "compras_insumos", BAD),
            ("busca en el sistema el historial de compras de laminas de hierro negro",
             "compras_insumos", BAD),
        ],
    },
    # ── Grupo 5: Productos por código ──
    {
        "name": "PRODUCTOS POR CÓDIGO",
        "queries": [
            ("quiero el historial de compra del siguiente producto REP-LAMI-0037",
             "compras_insumos", BAD),
            ("quien fue el ultimo proveedor del siguiente producto REP-LAMI-0037 en la empresa inproa santoni",
             "compras_insumos", BAD),
            ("quien fue el ultimo proveedor del siguiente producto REP-TUER-0115 en la empresa inproa santoni",
             "compras_insumos", BAD),
        ],
    },
    # ── Grupo 6: Gasoil y cantidades ──
    {
        "name": "GASOIL Y CANTIDADES",
        "queries": [
            ("que cantidad de gasoil se ha comprado en la empresa Inproa santoni desde el 01-01-26 hasta el 23-02-26",
             "compras_insumos", BAD),
        ],
    },
    # ── Grupo 7: Inventario de producto específico (follow-up) ──
    {
        "name": "INVENTARIO PRODUCTO ESPECÍFICO",
        "queries": [
            ("cual es el codigo de caja de carton para cereales",
             "compras_insumos", BAD),
            ("dame el inventario actual de ese producto en inproa santoni",
             "compras_insumos", BAD_INV),
        ],
    },
]


def run_tests(token):
    total = sum(len(g["queries"]) for g in TESTS)
    ok = 0
    warn = 0
    fail = 0
    results = []

    test_num = 0

    for group in TESTS:
        print(f"{B}── {group['name']} ──{N}")
        conv_id = None  # new conversation per group

        for msg, expected_agent, bad_patterns in group["queries"]:
            test_num += 1
            short_msg = msg[:80] + ("..." if len(msg) > 80 else "")
            print(f"  [{test_num}/{total}] {short_msg}")

            t0 = time.time()
            agent, response, conv_id = chat(token, msg, conv_id)
            elapsed = time.time() - t0

            # Truncate response for display
            resp_short = response.replace("\n", " ")[:200]

            # Check for issues
            issues = []
            status = "OK"

            if agent == "ERROR":
                issues.append(f"ERROR API: {response[:100]}")
                status = "FAIL"
            else:
                # Check agent
                if expected_agent and agent != expected_agent:
                    if "cliente" in msg.lower() and agent == "ventas":
                        pass  # acceptable
                    else:
                        issues.append(f"Agente: {agent} (esperado: {expected_agent})")
                        status = "WARN"

                # Check bad patterns
                resp_lower = response.lower()
                for pat in bad_patterns:
                    if pat.lower() in resp_lower:
                        issues.append(f"Contiene: '{pat}'")
                        status = "FAIL"

                # Check if response is too short (likely empty/error)
                if len(response.strip()) < 20:
                    issues.append(f"Respuesta muy corta ({len(response)} chars)")
                    status = "WARN"

            # Print result
            if status == "OK":
                print(f"    {G}OK{N}   [{agent}] ({elapsed:.1f}s) {resp_short}")
                ok += 1
            elif status == "WARN":
                print(f"    {Y}WARN{N} [{agent}] ({elapsed:.1f}s) {'; '.join(issues)}")
                print(f"         {resp_short}")
                warn += 1
            else:
                print(f"    {R}FAIL{N} [{agent}] ({elapsed:.1f}s) {'; '.join(issues)}")
                print(f"         {resp_short}")
                fail += 1

            results.append((test_num, msg[:60], agent, status, issues))
            time.sleep(1)  # small delay between requests

        print()

    # Summary
    print("=" * 70)
    print(f"  RESULTADOS: {G}{ok} OK{N}, {Y}{warn} WARN{N}, {R}{fail} FAIL{N}  (de {total} preguntas)")
    print("=" * 70)

    if fail > 0 or warn > 0:
        print(f"\n{B}Detalles:{N}")
        for num, msg, agent, status, issues in results:
            if status != "OK":
                color = R if status == "FAIL" else Y
                print(f"  {color}[{num}]{N} {msg}...")
                for i in issues:
                    print(f"       → {i}")

    return fail


if __name__ == "__main__":
    print("=" * 70)
    print("  SANTONIBOT - TEST EN VIVO (API)")
    print("  Preguntas reales de Jorge Chahine")
    print("=" * 70)
    print()

    token = login()
    failures = run_tests(token)
    sys.exit(1 if failures > 0 else 0)
