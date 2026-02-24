#!/usr/bin/env python3
"""Diagnóstico rápido de datos de nómina en iDempiere.

Verifica cómo se almacenan devengados y deducciones en hr_movement.
Ejecutar: docker compose exec backend python3 scripts/diagnose_payroll.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import IdempiereSession
from sqlalchemy import text

db = IdempiereSession()

print("=" * 70)
print("DIAGNÓSTICO DE NÓMINA - iDempiere hr_movement")
print("=" * 70)

# 1. ¿Hay montos negativos en hr_movement?
print("\n── 1. Distribución de signos en hr_movement.amount (enero 2026) ──")
q1 = text("""
    SELECT
        CASE WHEN hm.amount > 0 THEN 'positivo'
             WHEN hm.amount < 0 THEN 'negativo'
             ELSE 'cero' END AS signo,
        COUNT(*) AS movimientos,
        SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    WHERE hp.docstatus = 'CO'
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = 1
      AND EXTRACT(YEAR FROM hp.dateacct) = 2026
    GROUP BY signo
    ORDER BY signo
""")
for row in db.execute(q1).fetchall():
    print(f"  {row[0]:>10}: {row[1]:>8} movimientos, total = {row[2]:>20,.2f}")

# 2. ¿Qué tipos de concepto hay?
print("\n── 2. Tipos de concepto (hr_concept.type) ──")
q2 = text("""
    SELECT hc.type, COUNT(*) AS movimientos,
           SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
    WHERE hp.docstatus = 'CO'
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = 1
      AND EXTRACT(YEAR FROM hp.dateacct) = 2026
    GROUP BY hc.type
    ORDER BY hc.type
""")
for row in db.execute(q2).fetchall():
    print(f"  tipo='{row[0]}': {row[1]:>8} movimientos, total = {row[2]:>20,.2f}")

# 3. ¿Qué columntype hay?
print("\n── 3. Column types (hr_concept.columntype) ──")
q3 = text("""
    SELECT hc.columntype, COUNT(*) AS movimientos,
           SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
    WHERE hp.docstatus = 'CO'
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = 1
      AND EXTRACT(YEAR FROM hp.dateacct) = 2026
    GROUP BY hc.columntype
    ORDER BY hc.columntype
""")
for row in db.execute(q3).fetchall():
    print(f"  columntype='{row[0]}': {row[1]:>8} movimientos, total = {row[2]:>20,.2f}")

# 4. Top 15 conceptos con sus tipos
print("\n── 4. Top 15 conceptos por monto absoluto (enero 2026) ──")
q4 = text("""
    SELECT hc.name, hc.type, hc.columntype,
           COUNT(*) AS movs,
           SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
    WHERE hp.docstatus = 'CO'
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = 1
      AND EXTRACT(YEAR FROM hp.dateacct) = 2026
    GROUP BY hc.name, hc.type, hc.columntype
    ORDER BY ABS(SUM(hm.amount)) DESC
    LIMIT 15
""")
print(f"  {'Concepto':<45} {'Tipo':>4} {'ColType':>7} {'Movs':>6} {'Total':>20}")
print(f"  {'-'*45} {'-'*4} {'-'*7} {'-'*6} {'-'*20}")
for row in db.execute(q4).fetchall():
    print(f"  {row[0]:<45} {row[1] or '?':>4} {row[2] or '?':>7} {row[3]:>6} {row[4]:>20,.2f}")

# 5. Resumen esperado correcto
print("\n── 5. Resumen nómina enero 2026 (por tipo de concepto) ──")
q5 = text("""
    SELECT
        COALESCE(SUM(CASE WHEN hc.type = 'E' THEN hm.amount ELSE 0 END), 0) AS devengado_tipo_E,
        COALESCE(SUM(CASE WHEN hc.type = 'D' THEN hm.amount ELSE 0 END), 0) AS deduccion_tipo_D,
        COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS positivos,
        COALESCE(SUM(CASE WHEN hm.amount < 0 THEN ABS(hm.amount) ELSE 0 END), 0) AS negativos,
        COALESCE(SUM(hm.amount), 0) AS total_neto
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
    WHERE hp.docstatus = 'CO'
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = 1
      AND EXTRACT(YEAR FROM hp.dateacct) = 2026
""")
row = db.execute(q5).fetchone()
if row:
    print(f"  Por tipo concepto (E=earning):  devengado = {row[0]:>20,.2f}")
    print(f"  Por tipo concepto (D=deducción): deducción = {row[1]:>20,.2f}")
    print(f"  Por signo amount (>0):          positivos = {row[2]:>20,.2f}")
    print(f"  Por signo amount (<0):          negativos = {row[3]:>20,.2f}")
    print(f"  Total neto (SUM):                   neto = {row[4]:>20,.2f}")

db.close()
print("\n" + "=" * 70)
print("FIN DIAGNÓSTICO")
