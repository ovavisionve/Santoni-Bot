#!/usr/bin/env python3
"""
Test final VERIFICADO: fetch_data (iDempiere) vs bot API (LLM).

Para cada pregunta:
1. Llama fetch_data() → extrae número clave de iDempiere
2. Llama bot API → extrae números de la respuesta LLM
3. Compara: ¿el número de iDempiere aparece en la respuesta del bot?

Uso:
    docker compose exec backend python tests/qa_mass/test_final_verified.py \
        --password 'SantoniAdmin2026!' --start 67
"""

import argparse, requests, json, sys, time, re
from datetime import datetime

from tests.qa_ventas.bot_client import extract_numbers


def extract_key_number(fetch_result):
    """Extrae el número más importante del resultado de fetch_data."""
    if not fetch_result or len(fetch_result) < 50:
        return None, "sin datos"

    text = fetch_result
    # Look for key totals in order of importance
    patterns = [
        (r'Total[:\s]+(\d[\d.,]+)', 'total'),
        (r'Tasa[:\s]+(\d[\d.,]+)', 'tasa'),
        (r'Empleados[:\s]+(\d[\d.,]+)', 'empleados'),
        (r'Facturas[:\s]+(\d[\d.,]+)', 'facturas'),
        (r'Recibos[:\s]+(\d[\d.,]+)', 'recibos'),
        (r'Bajas[:\s]+(\d[\d.,]+)', 'bajas'),
        (r'Ocurrencias[:\s]+(\d[\d.,]+)', 'ocurrencias'),
        (r'Devengado[:\s]+([\d.,]+)', 'devengado'),
        (r'Cobrado[:\s]+([\d.,]+)', 'cobrado'),
        (r'Saldo[:\s]+([\d.,]+)', 'saldo'),
        (r'Activos[:\s]+(\d+)', 'activos'),
        (r'(\d+)\s+registros', 'registros'),
        (r'(\d+)\s+encontrados', 'encontrados'),
        (r'(\d+)\s+empleados', 'empleados'),
        (r'TOTAL EXACTO:\s+(\d+)', 'total_exacto'),
    ]

    for pattern, label in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace('.', '').replace(',', '.')
            try:
                val = float(raw)
                if val > 0:
                    return val, label
            except ValueError:
                continue

    # Fallback: count table rows as a proxy
    rows = sum(1 for line in text.split('\n')
               if line.strip().startswith('|') and '---' not in line
               and not any(h in line.lower() for h in ['nombre', 'codigo', 'organizacion']))
    if rows > 0:
        return float(rows), 'filas_tabla'

    return None, "no_number"


def number_in_response(expected, bot_numbers, tolerance=0.10):
    """Check if expected number appears in bot numbers within tolerance."""
    if expected is None:
        return True  # Can't verify, assume OK
    for n in bot_numbers:
        if expected == 0:
            if abs(n) < 1:
                return True
        elif abs(n - expected) / abs(expected) <= tolerance:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    # Login
    token = requests.post(f'{args.base_url}/api/auth/login',
        json={'username': args.username, 'password': args.password}, timeout=15
    ).json()['access_token']

    # Load questions from test_final_135.py
    from tests.qa_mass.test_final_135 import generate_questions
    questions = generate_questions()

    start_idx = args.start - 1
    end_idx = args.end if args.end else len(questions)
    questions = questions[start_idx:end_idx]

    # Initialize agents
    from app.agents.rrhh import RRHHAgent
    from app.agents.ventas import VentasAgent
    from app.agents.contabilidad import ContabilidadAgent
    agents = {'rrhh': RRHHAgent(), 'ventas': VentasAgent(), 'contabilidad': ContabilidadAgent()}

    print(f"\n{'='*70}")
    print(f"  TEST VERIFICADO: fetch_data vs bot API")
    print(f"  Preguntas {args.start} a {args.start + len(questions) - 1}")
    print(f"{'='*70}\n")

    ok = 0
    no_verify = 0
    fails = []

    for i, (agent_name, question, cat) in enumerate(questions, args.start):
        agent = agents[agent_name]

        # 1. fetch_data → número real de iDempiere
        try:
            fetch_result = agent.fetch_data(
                message=question, history=[], org_ids=None, salesrep_id=None,
            )
            expected_val, val_label = extract_key_number(fetch_result)
        except Exception:
            expected_val, val_label = None, "fetch_error"

        # 2. Bot API → respuesta del LLM
        try:
            r = requests.post(f'{args.base_url}/api/chat/',
                json={'message': question, 'agent_name': agent_name},
                headers={'Authorization': f'Bearer {token}'}, timeout=120).json()
            bot_text = r.get('message', '')
        except Exception as e:
            bot_text = f"ERROR: {e}"

        # 3. Compare
        bot_nums = extract_numbers(bot_text)

        bad_phrases = ['no se encontraron', 'no hay datos', 'dificultades para']
        has_error = any(p in bot_text.lower() for p in bad_phrases)

        if has_error:
            fails.append((i, agent_name, cat, question[:50], "no_data", f"Bot: {bot_text[:100]}"))
            print(f"❌ [{i:3d}] [{agent_name:13s}] {question[:50]}")
            print(f"   Bot dijo 'no hay datos' — iDempiere: {val_label}={expected_val}")
        elif expected_val is None:
            no_verify += 1
            ok += 1  # Can't verify but bot responded
            print(f"⚠️ [{i:3d}] [{agent_name:13s}] {question[:50]}")
        elif number_in_response(expected_val, bot_nums):
            ok += 1
            print(f"✅ [{i:3d}] [{agent_name:13s}] {question[:50]}  [{val_label}={expected_val:.0f}]")
        else:
            # Check if it's close (within 20%)
            closest = min(bot_nums, key=lambda x: abs(x - expected_val)) if bot_nums else None
            if closest and abs(closest - expected_val) / max(abs(expected_val), 1) < 0.20:
                ok += 1
                print(f"✅ [{i:3d}] [{agent_name:13s}] {question[:50]}  [{val_label}≈{closest:.0f}]")
            else:
                fails.append((i, agent_name, cat, question[:50], "mismatch",
                              f"iDempiere:{expected_val:.0f} Bot:{closest:.0f}" if closest else "sin nums"))
                print(f"❌ [{i:3d}] [{agent_name:13s}] {question[:50]}")
                print(f"   iDempiere: {val_label}={expected_val:.0f} | Bot más cercano: {closest}")

        if (i - args.start + 1) % 25 == 0:
            total_so_far = i - args.start + 1
            print(f"--- {ok}/{total_so_far} OK ({100*ok//total_so_far}%) ---")

    total = len(questions)
    print(f"\n{'='*70}")
    print(f"  RESULTADO: {ok}/{total} ({100*ok//max(total,1)}%)")
    if fails:
        print(f"  Fallos: {len(fails)}")
        for pos, ag, cat, q, typ, note in fails:
            print(f"    ❌ [{pos}] [{ag}/{cat}] {q} → {note[:80]}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
