"""iDempiere read-only queries for role/org/window/table access."""

from sqlalchemy import text

from app.database import IdempiereSession


def _get_user_roles(ide_session, ad_user_id: int) -> list[str]:
    """Query iDempiere for the roles assigned to a user."""
    rows = ide_session.execute(text("""
        SELECT r.name
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_role r ON ur.ad_role_id = r.ad_role_id
        WHERE ur.ad_user_id = :uid AND ur.isactive = 'Y' AND r.isactive = 'Y'
        ORDER BY r.name
    """), {"uid": ad_user_id}).fetchall()
    return [row[0] for row in rows]


def _get_user_org_ids(ide_session, ad_user_id: int) -> list[int]:
    """Query iDempiere for the organizations accessible via user's roles."""
    rows = ide_session.execute(text("""
        SELECT DISTINCT roa.ad_org_id
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_role_orgaccess roa ON ur.ad_role_id = roa.ad_role_id
        WHERE ur.ad_user_id = :uid
          AND ur.isactive = 'Y'
          AND roa.isactive = 'Y'
          AND roa.ad_org_id > 0
        ORDER BY roa.ad_org_id
    """), {"uid": ad_user_id}).fetchall()
    return [row[0] for row in rows]


def _get_user_window_names(ide_session, ad_user_id: int) -> list[str]:
    """Query iDempiere for the window names accessible via user's roles."""
    rows = ide_session.execute(text("""
        SELECT DISTINCT w.name
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_window_access wa ON ur.ad_role_id = wa.ad_role_id
        JOIN adempiere.ad_window w ON wa.ad_window_id = w.ad_window_id
        WHERE ur.ad_user_id = :uid
          AND ur.isactive = 'Y'
          AND wa.isactive = 'Y'
          AND w.isactive = 'Y'
        ORDER BY w.name
    """), {"uid": ad_user_id}).fetchall()
    return [row[0] for row in rows]


def _get_user_table_names(ide_session, ad_user_id: int) -> list[str]:
    """Query iDempiere for the table names accessible via user's window→tab access."""
    rows = ide_session.execute(text("""
        SELECT DISTINCT t.tablename
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_window_access wa ON ur.ad_role_id = wa.ad_role_id
        JOIN adempiere.ad_tab tab ON tab.ad_window_id = wa.ad_window_id
        JOIN adempiere.ad_table t ON tab.ad_table_id = t.ad_table_id
        WHERE ur.ad_user_id = :uid
          AND ur.isactive = 'Y'
          AND wa.isactive = 'Y'
          AND tab.isactive = 'Y'
          AND t.isactive = 'Y'
        ORDER BY t.tablename
    """), {"uid": ad_user_id}).fetchall()
    return [row[0] for row in rows]


def _get_idempiere_user_name(ide_session, ad_user_id: int) -> str | None:
    """Get the name of an iDempiere user by ID."""
    row = ide_session.execute(text(
        "SELECT name FROM adempiere.ad_user WHERE ad_user_id = :uid"
    ), {"uid": ad_user_id}).fetchone()
    return row[0] if row else None


def list_idempiere_users() -> list[dict]:
    """List all iDempiere users for the admin to pick from when linking."""
    ide = IdempiereSession()
    try:
        rows = ide.execute(text("""
            SELECT u.ad_user_id, u.name, u.email,
                   string_agg(DISTINCT r.name, ', ' ORDER BY r.name) AS roles
            FROM adempiere.ad_user u
            LEFT JOIN adempiere.ad_user_roles ur
                ON ur.ad_user_id = u.ad_user_id AND ur.isactive = 'Y'
            LEFT JOIN adempiere.ad_role r
                ON r.ad_role_id = ur.ad_role_id AND r.isactive = 'Y'
            WHERE u.isactive = 'Y'
              AND u.ad_user_id > 0
              AND u.name NOT IN ('System', 'SuperUser', 'GardenAdmin', 'GardenUser')
            GROUP BY u.ad_user_id, u.name, u.email
            ORDER BY u.name
        """)).fetchall()
        return [
            {
                "ad_user_id": row[0],
                "name": row[1],
                "email": row[2],
                "roles": row[3] or "",
            }
            for row in rows
        ]
    finally:
        ide.close()
