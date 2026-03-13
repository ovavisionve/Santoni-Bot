#!/usr/bin/env python3
"""Diagnóstico rápido de datos de nómina en iDempiere.

Verifica cómo se almacenan devengados y deducciones en hr_movement.
Ejecutar: docker compose exec backend python3 scripts/diagnose_payroll.py [--mes N] [--anio N]
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import IdempiereSession
from sqlalchemy import text

parser = argparse.ArgumentParser(description="Diagnóstico de nómina iDempiere")
parser.add_argument("--mes", type=int, default=1, help="Mes a consultar (1-12)")
parser.add_argument("--anio", type=int, default=2026, help="Año a consultar")
args = parser.parse_args()

mes = args.mes
anio = args.anio

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}
mes_nombre = MESES.get(mes, str(mes))

db = IdempiereSession()

print("=" * 70)
print("DIAGNÓSTICO DE NÓMINA - iDempiere hr_movement")
print("=" * 70)

# 1. ¿Hay montos negativos en hr_movement?
print(f"\n── 1. Distribución de signos en hr_movement.amount ({mes_nombre} {anio}) ──")
q1 = text("""
    SELECT
        CASE WHEN hm.amount > 0 THEN 'positivo'
             WHEN hm.amount < 0 THEN 'negativo'
             ELSE 'cero' END AS signo,
        COUNT(*) AS movimientos,
        SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    WHERE hp.docstatus IN ('CO', 'CL')
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = :mes
      AND EXTRACT(YEAR FROM hp.dateacct) = :anio
    GROUP BY signo
    ORDER BY signo
""")
rows = db.execute(q1, {"mes": mes, "anio": anio}).fetchall()
if not rows:
    print(f"  ⚠ No hay movimientos de nómina para {mes_nombre} {anio}")
else:
    for row in rows:
        print(f"  {row[0]:>10}: {row[1]:>8} movimientos, total = {row[2]:>20,.2f}")

# 2. ¿Qué tipos de concepto hay?
print(f"\n── 2. Tipos de concepto (hr_concept.type) ──")
q2 = text("""
    SELECT hc.type, COUNT(*) AS movimientos,
           SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
    WHERE hp.docstatus IN ('CO', 'CL')
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = :mes
      AND EXTRACT(YEAR FROM hp.dateacct) = :anio
    GROUP BY hc.type
    ORDER BY hc.type
""")
for row in db.execute(q2, {"mes": mes, "anio": anio}).fetchall():
    print(f"  tipo='{row[0]}': {row[1]:>8} movimientos, total = {row[2]:>20,.2f}")

# 3. ¿Qué columntype hay?
print(f"\n── 3. Column types (hr_concept.columntype) ──")
q3 = text("""
    SELECT hc.columntype, COUNT(*) AS movimientos,
           SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
    WHERE hp.docstatus IN ('CO', 'CL')
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = :mes
      AND EXTRACT(YEAR FROM hp.dateacct) = :anio
    GROUP BY hc.columntype
    ORDER BY hc.columntype
""")
for row in db.execute(q3, {"mes": mes, "anio": anio}).fetchall():
    print(f"  columntype='{row[0]}': {row[1]:>8} movimientos, total = {row[2]:>20,.2f}")

# 4. Top 15 conceptos con sus tipos
print(f"\n── 4. Top 15 conceptos por monto absoluto ({mes_nombre} {anio}) ──")
q4 = text("""
    SELECT hc.name, hc.type, hc.columntype,
           COUNT(*) AS movs,
           SUM(hm.amount) AS total
    FROM adempiere.hr_process hp
    JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
    WHERE hp.docstatus IN ('CO', 'CL')
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = :mes
      AND EXTRACT(YEAR FROM hp.dateacct) = :anio
    GROUP BY hc.name, hc.type, hc.columntype
    ORDER BY ABS(SUM(hm.amount)) DESC
    LIMIT 15
""")
print(f"  {'Concepto':<45} {'Tipo':>4} {'ColType':>7} {'Movs':>6} {'Total':>20}")
print(f"  {'-'*45} {'-'*4} {'-'*7} {'-'*6} {'-'*20}")
for row in db.execute(q4, {"mes": mes, "anio": anio}).fetchall():
    print(f"  {row[0]:<45} {row[1] or '?':>4} {row[2] or '?':>7} {row[3]:>6} {row[4]:>20,.2f}")

# 5. Resumen esperado correcto
print(f"\n── 5. Resumen nómina {mes_nombre} {anio} (por tipo de concepto) ──")
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
    WHERE hp.docstatus IN ('CO', 'CL')
      AND hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = :mes
      AND EXTRACT(YEAR FROM hp.dateacct) = :anio
""")
row = db.execute(q5, {"mes": mes, "anio": anio}).fetchone()
if row:
    print(f"  Por tipo concepto (E=earning):  devengado = {row[0]:>20,.2f}")
    print(f"  Por tipo concepto (D=deducción): deducción = {row[1]:>20,.2f}")
    print(f"  Por signo amount (>0):          positivos = {row[2]:>20,.2f}")
    print(f"  Por signo amount (<0):          negativos = {row[3]:>20,.2f}")
    print(f"  Total neto (SUM):                   neto = {row[4]:>20,.2f}")

# 6. Verificar si hay procesos sin movimientos
print(f"\n── 6. Procesos de nómina en {mes_nombre} {anio} ──")
q6 = text("""
    SELECT hp.hr_process_id, hp.documentno, hp.dateacct, hp.docstatus,
           COUNT(hm.hr_movement_id) AS movimientos
    FROM adempiere.hr_process hp
    LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
    WHERE hp.isactive = 'Y'
      AND EXTRACT(MONTH FROM hp.dateacct) = :mes
      AND EXTRACT(YEAR FROM hp.dateacct) = :anio
    GROUP BY hp.hr_process_id, hp.documentno, hp.dateacct, hp.docstatus
    ORDER BY hp.dateacct
    LIMIT 20
""")
rows = db.execute(q6, {"mes": mes, "anio": anio}).fetchall()
if not rows:
    print(f"  ⚠ No hay procesos de nómina para {mes_nombre} {anio}")
else:
    print(f"  {'ID':>10} {'Documento':<20} {'Fecha':>12} {'Status':>8} {'Movimientos':>12}")
    print(f"  {'-'*10} {'-'*20} {'-'*12} {'-'*8} {'-'*12}")
    for row in rows:
        print(f"  {row[0]:>10} {row[1] or '':>20} {str(row[2]):>12} {row[3]:>8} {row[4]:>12}")

db.close()
print("\n" + "=" * 70)
print("FIN DIAGNÓSTICO")
