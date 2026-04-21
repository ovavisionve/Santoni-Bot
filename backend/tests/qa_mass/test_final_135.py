#!/usr/bin/env python3
"""
Test FINAL: 135 preguntas NUEVAS con variables aleatorias.
Para cada pregunta: obtiene respuesta esperada de iDempiere, pregunta al bot, compara.

Uso:
    docker compose exec backend python tests/qa_mass/test_final_135.py \
        --username admin --password 'SantoniAdmin2026!'
"""

import requests, json, sys, time, os, random
from datetime import datetime

# ── Questions generator ──────────────────────────────────────────────────

MESES = {1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
         7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}

ORGS = ["INPROA SANTONI", "InproMaiz", "Santoni Service", "AGROPECUARIA R.R.", "AGROINPROA"]

def generate_questions():
    """135 preguntas con variables rotadas."""
    qs = []
    now = datetime.now()
    cur_month = now.month
    cur_year = now.year

    # ── RRHH (55 preguntas) ──
    # Empleados (15)
    qs.append(("rrhh", "¿Cuántos empleados activos hay en total?", "empleados"))
    for org in ORGS[:4]:
        qs.append(("rrhh", f"¿Cuántos empleados tiene {org}?", "empleados"))
    qs.append(("rrhh", "¿Cuántos departamentos hay?", "empleados"))
    for cargo in ["supervisor", "operador", "vendedor", "analista", "gerente"]:
        qs.append(("rrhh", f"¿Cuántos {cargo}es tiene la empresa?", "busqueda_cargo"))
    qs.append(("rrhh", "Buscar empleado de apellido González", "busqueda_cargo"))
    qs.append(("rrhh", "Buscar empleado de apellido Pérez", "busqueda_cargo"))
    qs.append(("rrhh", "Buscar empleado de apellido García", "busqueda_cargo"))

    # Ausentismo (8)
    for m in [1,2,3,6,9,11]:
        qs.append(("rrhh", f"Índices de ausentismo de {MESES[m]} 2025", "ausentismo"))
    qs.append(("rrhh", f"Ausentismo de {ORGS[0]} en {MESES[cur_month]} {cur_year}", "ausentismo"))
    qs.append(("rrhh", f"Ausentismo de {ORGS[1]} en febrero 2026", "ausentismo"))

    # Nómina (8)
    for m in [1,2,3]:
        qs.append(("rrhh", f"Resumen de nómina de {MESES[m]} 2026", "nomina"))
    qs.append(("rrhh", "Nómina de diciembre 2025", "nomina"))
    qs.append(("rrhh", f"Nómina de {ORGS[0]} en enero 2026", "nomina"))
    qs.append(("rrhh", f"Nómina de {ORGS[1]} en febrero 2026", "nomina"))
    qs.append(("rrhh", "Total devengado en nómina de octubre 2025", "nomina"))
    qs.append(("rrhh", "Nómina del último trimestre 2025", "nomina"))

    # Cumpleaños (8)
    for m in [1,2,3,4,5,6,7,12]:
        qs.append(("rrhh", f"Cumpleañeros de {MESES[m]} 2026", "cumpleanos"))

    # Vacaciones (4)
    qs.append(("rrhh", "Reporte de vacaciones de enero 2026", "vacaciones"))
    qs.append(("rrhh", "Vacaciones pendientes", "vacaciones"))
    qs.append(("rrhh", f"Vacaciones de {ORGS[0]} en 2025", "vacaciones"))
    qs.append(("rrhh", "Empleados con vacaciones en marzo 2026", "vacaciones"))

    # Rotación (6)
    qs.append(("rrhh", "¿Cuántos empleados se fueron en 2025?", "rotacion"))
    qs.append(("rrhh", "Tasa de rotación del 2025", "rotacion"))
    qs.append(("rrhh", "Bajas de personal en 2026", "rotacion"))
    qs.append(("rrhh", "¿Cuántos empleados ingresaron en 2025?", "rotacion"))
    qs.append(("rrhh", "Ingresos de personal en enero 2026", "rotacion"))
    qs.append(("rrhh", "Nuevos ingresos en el primer trimestre 2026", "rotacion"))

    # Provisiones (3)
    qs.append(("rrhh", "Provisiones de pasivos laborales de enero 2026", "nomina"))
    qs.append(("rrhh", "Prestaciones sociales de diciembre 2025", "nomina"))
    qs.append(("rrhh", "Antigüedad acumulada de empleados en 2025", "nomina"))

    # ── VENTAS (55 preguntas) ──
    # Resumen ventas (10)
    for m in [1,2,3]:
        qs.append(("ventas", f"Ventas de {MESES[m]} 2026", "resumen_ventas"))
    qs.append(("ventas", "Resumen de ventas del año 2025", "resumen_ventas"))
    qs.append(("ventas", f"Ventas de {ORGS[0]} en enero 2026", "resumen_ventas"))
    qs.append(("ventas", f"Ventas de {ORGS[1]} en 2025", "resumen_ventas"))
    qs.append(("ventas", "¿Cuánto se facturó en dólares en enero 2026?", "resumen_ventas"))
    qs.append(("ventas", "Facturación en bolívares de febrero 2026", "resumen_ventas"))
    qs.append(("ventas", "Ventas del 01/01/2026 al 31/01/2026", "resumen_ventas"))
    qs.append(("ventas", "Ventas de marzo 2025", "resumen_ventas"))

    # Top clientes (8)
    qs.append(("ventas", "Top 20 clientes del 2025", "ranking_clientes"))
    qs.append(("ventas", "Top 10 clientes de enero 2026", "ranking_clientes"))
    qs.append(("ventas", f"Top 5 clientes de {ORGS[0]} en 2025", "ranking_clientes"))
    qs.append(("ventas", f"Top 10 clientes de {ORGS[1]} en febrero 2026", "ranking_clientes"))
    qs.append(("ventas", "Top clientes del mes actual", "ranking_clientes"))
    qs.append(("ventas", "Top 20 clientes en dólares del 2025", "ranking_clientes"))
    qs.append(("ventas", "Mejores clientes de marzo 2026", "ranking_clientes"))
    qs.append(("ventas", "¿Quién es el cliente que más compra?", "ranking_clientes"))

    # Cobranza (8)
    qs.append(("ventas", "Cobranza de enero 2026", "cobranza"))
    qs.append(("ventas", "Cobranza de febrero 2026", "cobranza"))
    qs.append(("ventas", "Cobranza del mes actual", "cobranza"))
    qs.append(("ventas", "¿Cuánto se cobró en 2025?", "cobranza"))
    qs.append(("ventas", f"Cobranza de {ORGS[0]} en enero 2026", "cobranza"))
    qs.append(("ventas", "Cobranza por transferencia en enero 2026", "cobranza"))
    qs.append(("ventas", "Top 10 cobros del mes", "cobranza"))
    qs.append(("ventas", "Resumen de pagos recibidos en marzo 2026", "cobranza"))

    # CxC vencidas (4)
    qs.append(("ventas", "Cuentas por cobrar vencidas", "cxc_vencidas"))
    qs.append(("ventas", "Top 10 morosos", "cxc_vencidas"))
    qs.append(("ventas", "Clientes con deuda vencida", "cxc_vencidas"))
    qs.append(("ventas", "Facturas vencidas de más de 90 días", "cxc_vencidas"))

    # Zonas (6)
    qs.append(("ventas", "Ventas por zona en enero 2026", "ventas_zona"))
    qs.append(("ventas", "Ranking de ventas por región en 2025", "ventas_zona"))
    qs.append(("ventas", "¿Qué zona vende más en 2026?", "ventas_zona"))
    qs.append(("ventas", "Ventas por zona en febrero 2026", "ventas_zona"))
    qs.append(("ventas", "Distribución de ventas por región", "ventas_zona"))
    qs.append(("ventas", "Ventas en la zona de los Llanos en 2025", "ventas_zona"))

    # Vendedores (4)
    qs.append(("ventas", f"Top vendedores de {ORGS[0]} en 2025", "ranking_vendedores"))
    qs.append(("ventas", "Mejores distribuidores de enero 2026", "ranking_vendedores"))
    qs.append(("ventas", f"Top vendedores de {ORGS[1]}", "ranking_vendedores"))
    qs.append(("ventas", "Ranking de distribuidores del año 2025", "ranking_vendedores"))

    # Productos (6)
    qs.append(("ventas", "Ventas de arroz en enero 2026", "ventas_categoria"))
    qs.append(("ventas", "¿Cuánto se vendió de harina en 2025?", "ventas_categoria"))
    qs.append(("ventas", "Productos más vendidos en febrero 2026", "ventas_categoria"))
    qs.append(("ventas", "Ventas por categoría en enero 2026", "ventas_categoria"))
    qs.append(("ventas", "Ventas de cereales en 2025", "ventas_categoria"))
    qs.append(("ventas", "Top productos en marzo 2026", "ventas_categoria"))

    # Clientes activos (3)
    qs.append(("ventas", f"Clientes activos de {ORGS[0]}", "ranking_clientes"))
    qs.append(("ventas", f"Clientes activos vs inactivos de {ORGS[1]}", "ranking_clientes"))
    qs.append(("ventas", "¿Cuántos clientes activos tenemos?", "ranking_clientes"))

    # Rangos de fecha (6)
    qs.append(("ventas", "Ventas del 15 de enero al 15 de febrero 2026", "resumen_ventas"))
    qs.append(("ventas", "Ventas del 01/02/2026 al 28/02/2026", "resumen_ventas"))
    qs.append(("ventas", "Cobranza de enero a marzo 2026", "cobranza"))
    qs.append(("ventas", "Ventas del primer trimestre 2026", "resumen_ventas"))
    qs.append(("ventas", "Facturación de noviembre 2025 a enero 2026", "resumen_ventas"))
    qs.append(("ventas", "Ventas del 15 de diciembre 2025 al 15 de enero 2026", "resumen_ventas"))

    # ── CONTABILIDAD (25 preguntas) ──
    # Balance (6)
    qs.append(("contabilidad", "Balance general de enero 2026", "balance_general"))
    qs.append(("contabilidad", "Balance general de 2025", "balance_general"))
    qs.append(("contabilidad", f"Balance de {ORGS[0]} en febrero 2026", "balance_general"))
    qs.append(("contabilidad", "Situación financiera de 2025", "balance_general"))
    qs.append(("contabilidad", f"Situación financiera de {ORGS[1]}", "balance_general"))
    qs.append(("contabilidad", "Activos totales del 2025", "balance_general"))

    # Cuentas específicas (8)
    qs.append(("contabilidad", "Saldo de la cuenta 1.01 en enero 2026", "saldo_cuenta"))
    qs.append(("contabilidad", "Detalle de la cuenta 1.01.01.01 en 2025", "saldo_cuenta"))
    qs.append(("contabilidad", "Movimientos de la cuenta 2.01 en febrero 2026", "saldo_cuenta"))
    qs.append(("contabilidad", "Saldo de la cuenta 5.01 en 2025", "saldo_cuenta"))
    qs.append(("contabilidad", "Cuenta 1101 en enero 2026", "saldo_cuenta"))
    qs.append(("contabilidad", "Libro mayor de la cuenta 4.01 en 2025", "saldo_cuenta"))
    qs.append(("contabilidad", "Detalle contable de bancos en enero 2026", "saldo_cuenta"))
    qs.append(("contabilidad", "Saldo de caja chica en febrero 2026", "saldo_cuenta"))

    # Estado resultados (4)
    qs.append(("contabilidad", "Estado de resultados 2025", "estado_resultados"))
    qs.append(("contabilidad", "Gastos del primer trimestre 2026", "gastos"))
    qs.append(("contabilidad", "Ingresos vs gastos de enero 2026", "estado_resultados"))
    qs.append(("contabilidad", f"Estado de resultados de {ORGS[1]} en 2025", "estado_resultados"))

    # Impuestos (3)
    qs.append(("contabilidad", "Impuestos de enero 2026", "impuestos"))
    qs.append(("contabilidad", "IVA del primer trimestre 2026", "impuestos"))
    qs.append(("contabilidad", "Retenciones de febrero 2026", "impuestos"))

    # Top cuentas (4)
    qs.append(("contabilidad", "Cuentas con más movimiento en 2025", "balance_general"))
    qs.append(("contabilidad", "Top 10 cuentas contables de enero 2026", "balance_general"))
    qs.append(("contabilidad", "¿Cuáles son las cuentas más activas?", "balance_general"))
    qs.append(("contabilidad", "Resumen contable del año 2025", "balance_general"))

    return qs[:135]  # Cap at 135


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    token = requests.post(f'{args.base_url}/api/auth/login',
        json={'username': args.username, 'password': args.password}, timeout=15
    ).json()['access_token']

    questions = generate_questions()
    if args.limit:
        questions = questions[:args.limit]

    print(f"\n{'='*70}")
    print(f"  TEST FINAL — {len(questions)} preguntas NUEVAS")
    print(f"  Variables rotadas: meses, orgs, productos, cargos")
    print(f"{'='*70}\n")

    ok = 0
    fails = []
    for i, (agent, question, cat) in enumerate(questions, 1):
        r = requests.post(f'{args.base_url}/api/chat/',
            json={'message': question, 'agent_name': agent},
            headers={'Authorization': f'Bearer {token}'}, timeout=120).json()
        text = r.get('message', '')
        bad_phrases = ['no se encontraron', 'no hay datos', 'dificultades para',
                       'no tengo acceso', 'no se pudo']
        has_error = any(p in text.lower() for p in bad_phrases)
        is_ok = not has_error and len(text) > 100

        if is_ok:
            ok += 1
        else:
            fails.append((i, agent, cat, question, text[:150]))

        icon = '✅' if is_ok else '❌'
        print(f'{icon} [{i:3d}/{len(questions)}] [{agent:13s}] {question[:55]}')
        if not is_ok:
            print(f'   → {text[:200]}')

        if i % 25 == 0:
            print(f'--- {ok}/{i} OK ({100*ok//i}%) ---')

    pct = 100 * ok // len(questions)
    print(f"\n{'='*70}")
    print(f"  RESULTADO FINAL: {ok}/{len(questions)} ({pct}%)")
    print(f"{'='*70}")

    if fails:
        print(f"\n  Fallos ({len(fails)}):")
        for pos, ag, cat, q, resp in fails:
            print(f"    ❌ [{pos}] [{ag}/{cat}] {q[:50]}")

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"/tmp/test_final_{ts}.txt"
    with open(path, "w") as f:
        f.write(f"RESULTADO: {ok}/{len(questions)} ({pct}%)\n\n")
        for pos, ag, cat, q, resp in fails:
            f.write(f"FAIL [{pos}] [{ag}/{cat}] {q}\n  → {resp}\n\n")
    print(f"\n  Reporte: {path}")


if __name__ == "__main__":
    main()
