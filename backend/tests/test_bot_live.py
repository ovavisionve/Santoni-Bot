#!/usr/bin/env python3
"""
Test en vivo del bot - TODAS las preguntas reales de usuarios, agente por agente.
Incluye las que fallaron + nuevas del cuestionario de validación.

Uso:
  python3 tests/test_bot_live.py                              # todos los agentes
  python3 tests/test_bot_live.py --agente compras_insumos     # solo un agente
  python3 tests/test_bot_live.py --agente rrhh
  python3 tests/test_bot_live.py --agente finanzas
  python3 tests/test_bot_live.py --url http://192.168.1.26    # URL custom

Desde servidor:
  docker compose exec backend python3 tests/test_bot_live.py --url http://localhost:8000
"""

import sys
import json
import time
import urllib.request
import urllib.error
import argparse

# ── Config ──────────────────────────────────────────────────────────────
USERNAME = "admin"
PASSWORD = "SantoniAdmin2026!"
TIMEOUT  = 180

# ANSI colors
G = "\033[92m"  # green
R = "\033[91m"  # red
Y = "\033[93m"  # yellow
B = "\033[1m"   # bold
C = "\033[96m"  # cyan
N = "\033[0m"   # reset


def api(base_url, method, path, body=None, token=None):
    url = f"{base_url}{path}"
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


def login(base_url):
    print(f"Conectando a {base_url} como {USERNAME}...")
    r = api(base_url, "POST", "/api/auth/login", {
        "username": USERNAME,
        "password": PASSWORD,
        "totp_code": None,
    })
    if "_error" in r:
        print(f"{R}ERROR login: {r}{N}")
        sys.exit(1)
    token = r.get("access_token", "")
    if not token:
        print(f"{R}ERROR: No se recibió token. Respuesta: {r}{N}")
        sys.exit(1)
    print(f"{G}Login OK{N}\n")
    return token


def get_latest_conversation_id(base_url, token):
    """Fetch the most recent conversation id (useful after a timeout)."""
    r = api(base_url, "GET", "/api/chat/conversations", token=token)
    if isinstance(r, list) and r:
        return r[0].get("id")
    return None


def chat(base_url, token, message, conversation_id=None):
    body = {"message": message, "conversation_id": conversation_id, "file_id": None}
    r = api(base_url, "POST", "/api/chat/", body, token)
    if "_error" in r:
        # On timeout/error, try to recover conversation_id from server
        # (the server may have created the conversation before timing out)
        cid = conversation_id
        if cid is None:
            cid = get_latest_conversation_id(base_url, token)
        return "ERROR", f"HTTP error: {r}", cid, None
    agent = r.get("agent_used", "???")
    text = r.get("message", "")
    cid = r.get("conversation_id", conversation_id)
    # Extract confidence score from metadata if available
    meta = r.get("metadata") or {}
    score = meta.get("confidence_score") or r.get("confidence_score")
    return agent, text, cid, score


# ── Bad patterns (indicate failure) ───────────────────────────────────
BAD_GENERIC = [
    "no tengo acceso",
    "no tienes permisos",
    "soy un modelo de lenguaje",
    "no puedo acceder a datos confidenciales",
    "no puedo acceder a información",
]
BAD_COMPRAS = BAD_GENERIC + [
    "no se encontraron compras para este producto",
]
BAD_RRHH = BAD_GENERIC + []
BAD_FINANZAS = BAD_GENERIC + []
BAD_VENTAS = BAD_GENERIC + []


# ══════════════════════════════════════════════════════════════════════
# TESTS POR AGENTE
# ══════════════════════════════════════════════════════════════════════

TESTS_COMPRAS_INSUMOS = [
    # ── Resumen y follow-ups de moneda ──
    {
        "name": "COMPRAS: Resumen + follow-up dólares/gastos",
        "queries": [
            ("¿Cuánto se compró de insumos este mes?", "compras_insumos", BAD_COMPRAS),
            ("Y en dólares?", "compras_insumos", BAD_COMPRAS),
            ("En gastos?", "compras_insumos", BAD_COMPRAS),
            ("administrativos", "compras_insumos", BAD_COMPRAS),
        ],
    },
    # ── Órdenes pendientes ──
    {
        "name": "COMPRAS: Órdenes pendientes",
        "queries": [
            ("Órdenes de compra pendientes por recepción de insumos del mes de febrero",
             "compras_insumos", BAD_COMPRAS),
        ],
    },
    # ── Inventario y códigos ──
    {
        "name": "COMPRAS: Inventario cajas de cartón",
        "queries": [
            ("quisiera saber cuantas cajas de carton quedan en inventario",
             "compras_insumos", BAD_GENERIC),
            ("tienes el codigo de las cajas de carton para cereales",
             "compras_insumos", BAD_COMPRAS),
            ("cual es el codigo de caja de carton para cereales",
             "compras_insumos", BAD_COMPRAS),
            ("dame el inventario actual de ese producto en inproa santoni",
             "compras_insumos", BAD_GENERIC),
        ],
    },
    # ── Proveedores y láminas ──
    {
        "name": "COMPRAS: Proveedores láminas hierro negro",
        "queries": [
            ("que proveedores venden laminas de hierro negro",
             "compras_insumos", BAD_COMPRAS),
            ("busca en el sistema el historial de compras de laminas de hierro negro",
             "compras_insumos", BAD_COMPRAS),
        ],
    },
    # ── Productos por código ──
    {
        "name": "COMPRAS: Historial por código de producto",
        "queries": [
            ("quiero el historial de compra del siguiente producto REP-LAMI-0037",
             "compras_insumos", BAD_COMPRAS),
            ("quien fue el ultimo proveedor del siguiente producto REP-LAMI-0037 en la empresa inproa santoni",
             "compras_insumos", BAD_COMPRAS),
            ("quien fue el ultimo proveedor del siguiente producto REP-TUER-0115 en la empresa inproa santoni",
             "compras_insumos", BAD_COMPRAS),
        ],
    },
    # ── Gasoil con rango de fechas ──
    {
        "name": "COMPRAS: Gasoil con rango de fecha",
        "queries": [
            ("que cantidad de gasoil se ha comprado en la empresa Inproa santoni desde el 01-01-26 hasta el 23-02-26",
             "compras_insumos", BAD_COMPRAS),
        ],
    },
    # ── Cuestionario de validación (cada pregunta independiente) ──
    {
        "name": "COMPRAS: Cuestionario - cajas cartón enero",
        "queries": [
            ("¿Cuántas cajas de cartón compramos en enero 2026?",
             "compras_insumos", BAD_COMPRAS),
        ],
    },
    {
        "name": "COMPRAS: Cuestionario - harina de avena",
        "queries": [
            ("Precio de las últimas 6 compras de harina de avena",
             "compras_insumos", BAD_COMPRAS),
        ],
    },
    {
        "name": "COMPRAS: Cuestionario - inventario total",
        "queries": [
            ("¿Cuál es el inventario actual de todos los insumos?",
             "compras_insumos", BAD_GENERIC),
        ],
    },
    {
        "name": "COMPRAS: Cuestionario - top proveedores",
        "queries": [
            ("top 10 proveedores por monto de compra",
             "compras_insumos", BAD_COMPRAS),
        ],
    },
]

TESTS_RRHH = [
    # ── Empleados básicos (estos SÍ funcionaron) ──
    {
        "name": "RRHH: Empleados por departamento y org",
        "queries": [
            ("¿Cuántos empleados hay por departamento?", "rrhh", BAD_RRHH),
            ("indicame el numero de empleados activos en inproa santoni", "rrhh", BAD_RRHH),
            ("cuantos empleados, cuantos obreros y cuantos gerenciales", "rrhh", BAD_RRHH),
        ],
    },
    # ── Ausentismo (falló en la primera sesión de Emelin) ──
    {
        "name": "RRHH: Ausentismo (FALLÓ antes)",
        "queries": [
            ("indicame los indices de ausentismo del mes de enero 2026", "rrhh", BAD_RRHH),
            ("indicame los indices de ausentismo del mes de enero 2026 de la empresa agroinproa",
             "rrhh", BAD_RRHH),
        ],
    },
    # ── Follow-ups (los que más fallaron) ──
    {
        "name": "RRHH: Follow-ups (FALLARON antes)",
        "queries": [
            ("cuantos trabajadores activos tiene la empresa inproa santoni", "rrhh", BAD_RRHH),
            ("estas seguro?", "rrhh", BAD_RRHH),
            ("ok damelo en febrero 2026", "rrhh", BAD_RRHH),
        ],
    },
    # ── Más follow-ups con cambio de org ──
    {
        "name": "RRHH: Follow-up cambio de organización",
        "queries": [
            ("indicame los indices de ausentismo del mes de enero 2026 de la empresa agroinproa",
             "rrhh", BAD_RRHH),
            ("si", "rrhh", BAD_RRHH),
            ("ok damelo de inversiones aga", "rrhh", BAD_RRHH),
        ],
    },
    # ── Nómina (falló) ──
    {
        "name": "RRHH: Nómina y gastos (FALLÓ antes)",
        "queries": [
            ("resumen de nomina de enero 2026", "rrhh", BAD_RRHH),
            ("cual es mi estimado de gastos semanales en el departamento de nomina",
             "rrhh", BAD_RRHH),
        ],
    },
    # ── Búsqueda por cargo ──
    {
        "name": "RRHH: Búsqueda por cargo",
        "queries": [
            ("¿Cuántos choferes tiene la empresa?", "rrhh", BAD_RRHH),
            ("analista de control de calidad", "rrhh", BAD_RRHH),
        ],
    },
    # ── Multi-mes (solo mostró septiembre, no oct/nov) ──
    {
        "name": "RRHH: Multi-mes sept/oct/nov 2025",
        "queries": [
            ("indicame los indices de ausentismos de la empresa INPROA SANTONI, de los meses septiembre, octubre y noviembre del 2025",
             "rrhh", BAD_RRHH),
        ],
    },
    # ── Empleados por depto específico ──
    {
        "name": "RRHH: Depto Talento Humano + follow-ups",
        "queries": [
            ("cuantos empleados hay en el departamento de Talento Humano en todo el grupo empresarial",
             "rrhh", BAD_RRHH),
            ("me podrias dar nombre y apellidos de cada uno, e indicarme a que empresa pertenece?",
             "rrhh", BAD_RRHH),
        ],
    },
    # ── Rotación ──
    {
        "name": "RRHH: Rotación y renuncias",
        "queries": [
            ("cuantas personas han renunciado en los meses de enero 2026 y febrero 2026",
             "rrhh", BAD_RRHH),
            ("cuantos empleados se fueron en 2025", "rrhh", BAD_RRHH),
        ],
    },
]

TESTS_FINANZAS = [
    # ── Saldos bancarios (datos incorrectos en prueba real) ──
    {
        "name": "FINANZAS: Saldos bancarios",
        "queries": [
            ("¿Cuáles son los saldos bancarios actuales?", "finanzas", BAD_FINANZAS),
            ("Cual es el banco con mayor disponibilidad el dia de hoy", "finanzas", BAD_FINANZAS),
        ],
    },
    # ── Ingresos por venta (va a contabilidad, usa fact_acct con cuentas tipo R) ──
    {
        "name": "FINANZAS: Ingresos por venta",
        "queries": [
            ("cuantos fueron los ingresos por venta el dia de ayer",
             "contabilidad", BAD_GENERIC),
        ],
    },
    # ── Liquidaciones bancarias ──
    {
        "name": "FINANZAS: Liquidaciones bancarias",
        "queries": [
            ("cuales fueron las liquidaciones Bancarias del dia 20/02/2026",
             "finanzas", BAD_FINANZAS),
        ],
    },
    # ── Cuentas por cobrar/pagar ──
    {
        "name": "FINANZAS: CxC y CxP",
        "queries": [
            ("¿Cuánto tenemos en cuentas por cobrar vencidas?", "finanzas", BAD_FINANZAS),
            ("¿Cuánto debemos en cuentas por pagar?", "finanzas", BAD_FINANZAS),
        ],
    },
    # ── Préstamos (fue a general) ──
    {
        "name": "FINANZAS: Préstamos (FALLÓ - fue a general)",
        "queries": [
            ("cuotas de prestamos que vencen hoy", "finanzas", BAD_FINANZAS),
        ],
    },
]

TESTS_VENTAS = [
    {
        "name": "VENTAS: Rankings de clientes",
        "queries": [
            ("¿Cuáles son los top 20 clientes por ventas del 2025?", "ventas", BAD_VENTAS),
            ("Top 10 clientes de InproMaiz en enero 2026", "ventas", BAD_VENTAS),
        ],
    },
    {
        "name": "VENTAS: Facturación y cobranza",
        "queries": [
            ("cuanto se vendio en enero 2026", "ventas", BAD_VENTAS),
            ("¿Cuánto se facturó en dólares en febrero 2026?", "ventas", BAD_VENTAS),
            ("dame la cobranza del mes pasado", "ventas", BAD_VENTAS),
        ],
    },
    {
        "name": "VENTAS: CxC vencidas (va a finanzas)",
        "queries": [
            ("cuentas por cobrar vencidas", "finanzas", BAD_FINANZAS),
        ],
    },
    {
        "name": "VENTAS: Follow-ups org y moneda",
        "queries": [
            ("¿Cuáles son los top 20 clientes por ventas del 2025?", "ventas", BAD_VENTAS),
            ("y de InproMaiz?", "ventas", BAD_VENTAS),
            ("y en dólares?", "ventas", BAD_VENTAS),
        ],
    },
]

TESTS_CONTABILIDAD = [
    {
        "name": "CONTABILIDAD: Balance y cuentas",
        "queries": [
            ("Muéstrame el balance general de enero 2026", "contabilidad", BAD_GENERIC),
            ("¿Cuál es el saldo de la cuenta 1101 en febrero 2026?", "contabilidad", BAD_GENERIC),
            ("estado de resultados de 2025", "contabilidad", BAD_GENERIC),
        ],
    },
    {
        "name": "CONTABILIDAD: Ingresos por venta",
        "queries": [
            ("cuanto fue el ingreso por venta en febrero 2026", "contabilidad", BAD_GENERIC),
        ],
    },
]

TESTS_PRODUCCION = [
    {
        "name": "PRODUCCION: Órdenes y resumen",
        "queries": [
            ("¿Cuánto se produjo en enero 2026?", "produccion", BAD_GENERIC),
            ("ordenes de produccion de febrero 2026", "produccion", BAD_GENERIC),
        ],
    },
]

TESTS_COMPRAS_PRODUCTORES = [
    {
        "name": "COMPRAS PRODUCTORES: Arroz y maíz",
        "queries": [
            ("¿Cuánto arroz paddy se compró en 2025?", "compras_productores", BAD_GENERIC),
            ("¿Cuántos productores de arroz hay registrados?", "compras_productores", BAD_GENERIC),
            ("Precio promedio del kilo de arroz en 2025", "compras_productores", BAD_GENERIC),
            ("pagos pendientes a productores de arroz", "compras_productores", BAD_GENERIC),
        ],
    },
]

AGENT_MAP = {
    "compras_insumos": TESTS_COMPRAS_INSUMOS,
    "rrhh": TESTS_RRHH,
    "finanzas": TESTS_FINANZAS,
    "ventas": TESTS_VENTAS,
    "contabilidad": TESTS_CONTABILIDAD,
    "produccion": TESTS_PRODUCCION,
    "compras_productores": TESTS_COMPRAS_PRODUCTORES,
}


def run_tests(base_url, token, test_groups):
    total = sum(len(g["queries"]) for g in test_groups)
    ok = warn = fail = 0
    results = []
    test_num = 0

    for group in test_groups:
        print(f"\n{B}{C}══ {group['name']} ══{N}")
        conv_id = None

        for msg, expected_agent, bad_patterns in group["queries"]:
            test_num += 1
            short_msg = msg[:80] + ("..." if len(msg) > 80 else "")
            print(f"  [{test_num}/{total}] {short_msg}")

            t0 = time.time()
            agent, response, conv_id, score = chat(base_url, token, msg, conv_id)
            elapsed = time.time() - t0

            resp_short = response.replace("\n", " ")[:200]
            score_str = f" score={score:.2f}" if score else ""

            issues = []
            status = "OK"

            if agent == "ERROR":
                issues.append(f"ERROR API: {response[:100]}")
                status = "FAIL"
            else:
                if expected_agent and agent != expected_agent:
                    if agent == "orchestrator":
                        issues.append(f"ACCESO DENEGADO (esperado: {expected_agent})")
                        status = "FAIL"
                    elif agent == "general":
                        issues.append(f"Fue a GENERAL (esperado: {expected_agent})")
                        status = "FAIL"
                    else:
                        issues.append(f"Agente: {agent} (esperado: {expected_agent})")
                        status = "WARN"

                resp_lower = response.lower()
                for pat in bad_patterns:
                    if pat.lower() in resp_lower:
                        issues.append(f"Contiene: '{pat}'")
                        status = "FAIL"

                if len(response.strip()) < 20:
                    issues.append(f"Respuesta muy corta ({len(response)} chars)")
                    status = "WARN"

            if status == "OK":
                print(f"    {G}OK{N}   [{agent}]{score_str} ({elapsed:.1f}s)")
                print(f"         {resp_short}")
                ok += 1
            elif status == "WARN":
                print(f"    {Y}WARN{N} [{agent}]{score_str} ({elapsed:.1f}s) {'; '.join(issues)}")
                print(f"         {resp_short}")
                warn += 1
            else:
                print(f"    {R}FAIL{N} [{agent}]{score_str} ({elapsed:.1f}s) {'; '.join(issues)}")
                print(f"         {resp_short}")
                fail += 1

            results.append((test_num, msg[:60], agent, status, issues, score))
            time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print(f"  RESULTADOS: {G}{ok} OK{N}, {Y}{warn} WARN{N}, {R}{fail} FAIL{N}  (de {total} preguntas)")
    print("=" * 70)

    if fail > 0 or warn > 0:
        print(f"\n{B}Detalle de problemas:{N}")
        for num, msg, agent, status, issues, score in results:
            if status != "OK":
                color = R if status == "FAIL" else Y
                sc = f" (score={score:.2f})" if score else ""
                print(f"  {color}[{num}]{N} {msg}... → [{agent}]{sc}")
                for i in issues:
                    print(f"       {color}→{N} {i}")

    return fail


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SantoniBot - Test en vivo por agente")
    parser.add_argument("--url", default="http://192.168.1.26", help="Base URL del bot")
    parser.add_argument("--agente", "--agent", default=None,
                        help="Agente específico: compras_insumos, rrhh, finanzas, ventas, contabilidad, produccion, compras_productores")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    if args.agente:
        if args.agente not in AGENT_MAP:
            print(f"{R}Agente '{args.agente}' no existe. Opciones: {', '.join(AGENT_MAP.keys())}{N}")
            sys.exit(1)
        test_groups = AGENT_MAP[args.agente]
        label = args.agente.upper()
    else:
        test_groups = []
        for groups in AGENT_MAP.values():
            test_groups.extend(groups)
        label = "TODOS LOS AGENTES"

    total_q = sum(len(g["queries"]) for g in test_groups)

    print("=" * 70)
    print(f"  SANTONIBOT - TEST EN VIVO")
    print(f"  {label} ({total_q} preguntas)")
    print(f"  URL: {base_url}")
    print("=" * 70)

    token = login(base_url)
    failures = run_tests(base_url, token, test_groups)
    sys.exit(1 if failures > 0 else 0)
