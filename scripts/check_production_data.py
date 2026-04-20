#!/usr/bin/env python3
"""Quick diagnostic: check if m_production has data in iDempiere.

Run from the backend container:
    docker compose exec backend python scripts/check_production_data.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import text
from app.database import IdempiereSession

def main():
    db = IdempiereSession()
    try:
        # 1. Total count of productions
        row = db.execute(text(
            "SELECT COUNT(*) FROM adempiere.m_production WHERE isactive = 'Y'"
        )).fetchone()
        print(f"Total m_production (activas): {row[0]}")

        # 2. Productions by docstatus
        rows = db.execute(text(
            "SELECT docstatus, COUNT(*) FROM adempiere.m_production "
            "WHERE isactive = 'Y' GROUP BY docstatus ORDER BY COUNT(*) DESC"
        )).fetchall()
        print("\nPor docstatus:")
        for r in rows:
            print(f"  {r[0]}: {r[1]}")

        # 3. Date range
        row = db.execute(text(
            "SELECT MIN(movementdate), MAX(movementdate) "
            "FROM adempiere.m_production WHERE isactive = 'Y' AND docstatus IN ('CO','CL')"
        )).fetchone()
        print(f"\nRango de fechas (CO/CL): {row[0]} a {row[1]}")

        # 4. Productions in 2026
        row = db.execute(text(
            "SELECT COUNT(*) FROM adempiere.m_production "
            "WHERE isactive = 'Y' AND docstatus IN ('CO','CL') "
            "AND EXTRACT(YEAR FROM movementdate) = 2026"
        )).fetchone()
        print(f"\nProducciones 2026: {row[0]}")

        # 5. Productions in March 2026
        row = db.execute(text(
            "SELECT COUNT(*) FROM adempiere.m_production "
            "WHERE isactive = 'Y' AND docstatus IN ('CO','CL') "
            "AND EXTRACT(YEAR FROM movementdate) = 2026 "
            "AND EXTRACT(MONTH FROM movementdate) = 3"
        )).fetchone()
        print(f"Producciones Marzo 2026: {row[0]}")

        # 6. Last 5 productions
        rows = db.execute(text(
            "SELECT pr.movementdate, p.name, org.name "
            "FROM adempiere.m_production pr "
            "JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id "
            "JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id "
            "JOIN adempiere.ad_org org ON pr.ad_org_id = org.ad_org_id "
            "WHERE pr.isactive = 'Y' AND pr.docstatus IN ('CO','CL') "
            "AND prl.isendproduct = 'Y' "
            "ORDER BY pr.movementdate DESC LIMIT 5"
        )).fetchall()
        print("\nÚltimas 5 producciones (producto terminado):")
        for r in rows:
            print(f"  {r[0]} | {r[1]} | {r[2]}")

        # 7. Check if schema is accessible
        row = db.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'adempiere' AND table_name = 'm_production'"
        )).fetchone()
        print(f"\nTabla m_production existe en schema adempiere: {'SÍ' if row[0] > 0 else 'NO'}")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
