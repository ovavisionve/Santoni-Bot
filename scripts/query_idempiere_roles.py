"""Query iDempiere roles, users, and window access for bot integration."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text

# Build connection from env or defaults
host = os.getenv("IDEMPIERE_DB_HOST", "192.168.1.73")
port = os.getenv("IDEMPIERE_DB_PORT", "5432")
db = os.getenv("IDEMPIERE_DB_NAME", "idempiere_produccion")
user = os.getenv("IDEMPIERE_DB_USER", "ova")
pwd = os.getenv("IDEMPIERE_DB_PASSWORD", "")

url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
engine = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})

queries = {
    "1. ROLES": """
        SELECT ad_role_id, name, description
        FROM adempiere.ad_role
        WHERE isactive = 'Y'
        ORDER BY name
    """,
    "2. USUARIOS Y SUS ROLES": """
        SELECT u.name AS usuario, r.name AS rol
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_user u ON ur.ad_user_id = u.ad_user_id
        JOIN adempiere.ad_role r ON ur.ad_role_id = r.ad_role_id
        WHERE ur.isactive = 'Y'
        ORDER BY r.name, u.name
    """,
    "3. VENTANAS POR ROL (primeros 200)": """
        SELECT r.name AS rol, w.name AS ventana, wa.isreadwrite
        FROM adempiere.ad_window_access wa
        JOIN adempiere.ad_role r ON wa.ad_role_id = r.ad_role_id
        JOIN adempiere.ad_window w ON wa.ad_window_id = w.ad_window_id
        WHERE wa.isactive = 'Y' AND r.isactive = 'Y'
        ORDER BY r.name, w.name
        LIMIT 200
    """,
    "4. ORGANIZACIONES POR ROL": """
        SELECT r.name AS rol, o.name AS organizacion
        FROM adempiere.ad_role_orgaccess roa
        JOIN adempiere.ad_role r ON roa.ad_role_id = r.ad_role_id
        JOIN adempiere.ad_org o ON roa.ad_org_id = o.ad_org_id
        WHERE roa.isactive = 'Y'
        ORDER BY r.name, o.name
    """,
}

with engine.connect() as conn:
    for title, sql in queries.items():
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
        rows = conn.execute(text(sql)).fetchall()
        print(f"  ({len(rows)} resultados)\n")
        for row in rows:
            print("  ", " | ".join(str(v) for v in row))
