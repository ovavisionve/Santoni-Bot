#!/usr/bin/env python3
"""
Test de los 12 casos fallidos — ahora via orchestrator (sin agent_name)
para que sql_direct tenga chance de responder.

Uso:
    docker compose exec backend python tests/qa_mass/test_12_via_sqldirect.py \
        --base-url http://localhost:8000 \
        --username admin --password 'SantoniAdmin2026!'
"""

import argparse
import os
import sys
import time

import requests


CASES = [
    (13, "rrhh", "Indícame los índices de ausentismo del mes de enero 2025"),
    (64, "contabilidad", "¿Cuál es el saldo de la cuenta 1101 en febrero 2026?"),
    (142, "ventas", "¿Cuánto se vendió de harinas en febrero 2026?"),
    (146, "ventas", "Comparativo de cobranza vs metas de enero 2026"),
    (149, "ventas", "Clientes activos vs inactivos de InproMaiz"),
    (156, "ventas", "Visitas a clientes del mes de enero 2026"),
    (167, "rrhh", "Provisiones mensuales de pasivos laborales de enero 2025"),
    (169, "rrhh", "Asistencias del día de hoy"),
    (170, "rrhh", "Costo total de rotación del 2025"),
    (171, "rrhh", "Calidad de contratación del último trimestre"),
    (373, "ventas", "Ventas del 15 de diciembre 2024 al 15 de enero 2025"),
    (395, "rrhh", "Nómina de INPROA SANTONI vs InproMaiz en enero 2026"),
]

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
B = "\033[1m"
X = "\033[0m"

_ERROR_PHRASES = [
    "no se encontraron datos", "no hay datos", "no hay registros",
    "dificultades para", "error de conexión", "no tengo acceso",
    "inténtalo de nuevo",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    username = args.username or os.getenv("TEST_USERNAME", "admin")
    password = args.password or os.getenv("TEST_PASSWORD", "")

    # Login
    resp = requests.post(f"{args.base_url}/api/auth/login",
                         json={"username": username, "password": password}, timeout=15)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"\n{B}{'='*70}")
    print(f"  12 CASOS FALLIDOS — via orchestrator (sql_direct habilitado)")
    print(f"{'='*70}{X}\n  Login OK\n")

    passed = 0
    for case_id, agent, question in CASES:
        print(f"  {B}#{case_id}{X} [{agent}] {question[:60]}")
        start = time.time()
        try:
            # CON agent_name → va al agente → si no tiene datos → fallback sql_direct
            resp = requests.post(
                f"{args.base_url}/api/chat/",
                json={"message": question, "agent_name": agent},
                headers={"Authorization": f"Bearer {token}"},
                timeout=180,
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed = time.time() - start
            bot_text = data.get("message", "")
            agent_used = data.get("agent_used", "?")
            text_lower = bot_text.lower()

            has_error = any(p in text_lower for p in _ERROR_PHRASES)
            has_content = len(bot_text) > 100 and not has_error

            if has_content:
                passed += 1
                icon = f"{G}✅{X}"
                preview = bot_text[:200].replace("\n", " ")
                print(f"    {icon} ({elapsed:.1f}s, agent={agent_used}) {preview}...")
            else:
                icon = f"{R}❌{X}"
                preview = bot_text[:200].replace("\n", " ")
                print(f"    {icon} ({elapsed:.1f}s, agent={agent_used}) {preview}...")
        except Exception as exc:
            elapsed = time.time() - start
            print(f"    {R}ERROR{X} ({elapsed:.1f}s): {exc}")
        print()

    print(f"{B}{'='*70}")
    print(f"  RESULTADO: {passed}/{len(CASES)} respondidos con datos")
    print(f"{'='*70}{X}\n")


if __name__ == "__main__":
    main()
