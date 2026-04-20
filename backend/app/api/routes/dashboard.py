"""
Dashboard & Alerts API endpoints.
- /api/dashboard/kpis: Department-specific KPIs for the logged-in user
- /api/dashboard/alerts: User's active alerts
- /api/dashboard/alerts/configure: Create/update alert rules
"""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.database import get_db, IdempiereSession
from app.middleware.auth import get_current_user, require_admin
from app.models.user import User
from app.models.conversation import Message, Conversation
from app.services.cache import cache_stats, clear_cache

logger = logging.getLogger("santonibot.dashboard")

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ──────────────────────────────────────────────────────────────
# KPIs endpoint — returns department-specific metrics
# ──────────────────────────────────────────────────────────────

def _get_idempiere_kpis(department: str, org_ids: list[int] | None) -> dict:
    """Fetch KPIs from iDempiere based on department."""
    db = IdempiereSession()
    kpis = {}
    org_filter = ""
    if org_ids:
        org_filter = f" AND i.ad_org_id IN ({','.join(str(x) for x in org_ids)})"

    try:
        if department == "ventas":
            # Sales KPIs
            now = datetime.now()
            year, month = now.year, now.month

            # Monthly sales total
            row = db.execute(text(f"""
                SELECT COALESCE(SUM(i.grandtotal), 0) as total,
                       COUNT(i.c_invoice_id) as count
                FROM adempiere.c_invoice i
                WHERE i.issotrx = 'Y' AND i.docstatus = 'CO'
                AND EXTRACT(YEAR FROM i.dateinvoiced) = :year
                AND EXTRACT(MONTH FROM i.dateinvoiced) = :month
                {org_filter}
            """), {"year": year, "month": month}).fetchone()
            kpis["ventas_mes"] = {"valor": float(row[0]) if row else 0, "facturas": row[1] if row else 0}

            # Overdue receivables
            # PERF-100 (14/Abr/2026): reemplazar invoiceopen() con LEFT JOIN
            # agregado para ~100x speedup (invoiceopen es VOLATILE PL/pgSQL).
            row = db.execute(text(f"""
                SELECT COALESCE(SUM(i.grandtotal - COALESCE(alloc.paid, 0)), 0) as total,
                       COUNT(i.c_invoice_id) as count
                FROM adempiere.c_invoice i
                LEFT JOIN (
                    SELECT al.c_invoice_id,
                           SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid
                    FROM adempiere.c_allocationline al
                    JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
                    WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL')
                    AND ah.dateacct >= (CURRENT_DATE - INTERVAL '3 years')
                    GROUP BY al.c_invoice_id
                ) alloc ON alloc.c_invoice_id = i.c_invoice_id
                WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
                AND i.dateinvoiced < CURRENT_DATE - INTERVAL '30 days'
                AND (i.grandtotal - COALESCE(alloc.paid, 0)) > 0
                {org_filter}
            """)).fetchone()
            kpis["cxc_vencidas"] = {"valor": float(row[0]) if row else 0, "facturas": row[1] if row else 0}

            # Top 5 clients this month
            rows = db.execute(text(f"""
                SELECT bp.name, SUM(i.grandtotal) as total
                FROM adempiere.c_invoice i
                JOIN adempiere.c_bpartner bp ON bp.c_bpartner_id = i.c_bpartner_id
                WHERE i.issotrx = 'Y' AND i.docstatus = 'CO'
                AND EXTRACT(YEAR FROM i.dateinvoiced) = :year
                AND EXTRACT(MONTH FROM i.dateinvoiced) = :month
                {org_filter}
                GROUP BY bp.name ORDER BY total DESC LIMIT 5
            """), {"year": year, "month": month}).fetchall()
            kpis["top_clientes"] = [{"nombre": r[0], "total": float(r[1])} for r in rows]

        elif department == "finanzas":
            # Bank balances (simplified)
            row = db.execute(text("""
                SELECT COUNT(DISTINCT ba.c_bankaccount_id) as cuentas
                FROM adempiere.c_bankaccount ba
                JOIN adempiere.c_bank b ON b.c_bank_id = ba.c_bank_id
                WHERE ba.isactive = 'Y'
            """)).fetchone()
            kpis["cuentas_bancarias"] = row[0] if row else 0

            # Payables total
            # PERF-100: reemplazar invoiceopen() con LEFT JOIN agregado
            row = db.execute(text(f"""
                SELECT COALESCE(SUM(i.grandtotal - COALESCE(alloc.paid, 0)), 0) as total,
                       COUNT(i.c_invoice_id) as count
                FROM adempiere.c_invoice i
                LEFT JOIN (
                    SELECT al.c_invoice_id,
                           SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid
                    FROM adempiere.c_allocationline al
                    JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
                    WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL')
                    AND ah.dateacct >= (CURRENT_DATE - INTERVAL '3 years')
                    GROUP BY al.c_invoice_id
                ) alloc ON alloc.c_invoice_id = i.c_invoice_id
                WHERE i.issotrx = 'N' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
                AND (i.grandtotal - COALESCE(alloc.paid, 0)) > 0
                {org_filter}
            """)).fetchone()
            kpis["cxp_pendientes"] = {"valor": float(row[0]) if row else 0, "facturas": row[1] if row else 0}

        elif department in ("compras_productores", "compras_insumos"):
            now = datetime.now()
            year, month = now.year, now.month
            is_sotrx = "'N'"

            row = db.execute(text(f"""
                SELECT COALESCE(SUM(i.grandtotal), 0) as total,
                       COUNT(i.c_invoice_id) as count
                FROM adempiere.c_invoice i
                WHERE i.issotrx = {is_sotrx} AND i.docstatus = 'CO'
                AND EXTRACT(YEAR FROM i.dateinvoiced) = :year
                AND EXTRACT(MONTH FROM i.dateinvoiced) = :month
                {org_filter}
            """), {"year": year, "month": month}).fetchone()
            kpis["compras_mes"] = {"valor": float(row[0]) if row else 0, "facturas": row[1] if row else 0}

        elif department == "contabilidad":
            # Count of journal entries this month
            now = datetime.now()
            row = db.execute(text("""
                SELECT COUNT(DISTINCT gl_journal_id)
                FROM adempiere.gl_journal
                WHERE docstatus = 'CO'
                AND EXTRACT(YEAR FROM datedoc) = :year
                AND EXTRACT(MONTH FROM datedoc) = :month
            """), {"year": now.year, "month": now.month}).fetchone()
            kpis["asientos_mes"] = row[0] if row else 0

        elif department == "rrhh":
            # Active employees
            row = db.execute(text("""
                SELECT COUNT(*)
                FROM adempiere.c_bpartner
                WHERE isactive = 'Y' AND isemployee = 'Y'
            """)).fetchone()
            kpis["empleados_activos"] = row[0] if row else 0

        elif department == "produccion":
            kpis["nota"] = "KPIs de producción disponibles via consulta al agente"

    except Exception as exc:
        logger.warning("Error fetching iDempiere KPIs for %s: %s", department, exc)
        kpis["error"] = str(exc)
    finally:
        db.close()

    return kpis


@router.get("/kpis")
def get_dashboard_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return KPIs specific to the user's department."""
    departments = current_user.allowed_departments
    primary_dept = current_user.department.value

    # Internal stats
    now = datetime.now(timezone.utc)
    last_7d = now - timedelta(days=7)

    # User's conversation count
    user_conversations = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.user_id == current_user.id)
        .scalar()
    )
    user_messages_7d = (
        db.query(func.count(Message.id))
        .join(Conversation)
        .filter(
            Conversation.user_id == current_user.id,
            Message.created_at >= last_7d,
        )
        .scalar()
    )

    # iDempiere KPIs
    idempiere_kpis = {}
    try:
        idempiere_kpis = _get_idempiere_kpis(primary_dept, current_user.org_ids)
    except Exception as exc:
        logger.warning("Could not load iDempiere KPIs: %s", exc)

    return {
        "user": {
            "name": current_user.full_name,
            "department": primary_dept,
            "departments": departments,
            "role": current_user.role.value,
        },
        "activity": {
            "conversations": user_conversations,
            "messages_7d": user_messages_7d,
        },
        "kpis": idempiere_kpis,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────────────────────
# Alerts system
# ──────────────────────────────────────────────────────────────

# In-memory alert rules (persisted via API, stored in DB in future)
_ALERT_RULES: list[dict] = []


class AlertRule(BaseModel):
    name: str
    department: str
    condition: str  # "cxc_vencidas > 1000000" or "produccion_diaria < 50"
    threshold: float
    metric: str  # "cxc_vencidas", "ventas_mes", "produccion_diaria"
    active: bool = True


@router.get("/alerts")
def get_alerts(
    current_user: User = Depends(get_current_user),
):
    """Get active alerts for the user's departments."""
    departments = current_user.allowed_departments
    alerts = []

    # Check iDempiere for alert conditions
    try:
        db = IdempiereSession()
        try:
            org_ids = current_user.org_ids
            org_filter = ""
            if org_ids:
                org_filter = f" AND i.ad_org_id IN ({','.join(str(x) for x in org_ids)})"

            # Alert: Overdue receivables (for ventas, finanzas)
            # PERF-100: reemplazar invoiceopen() con LEFT JOIN agregado
            if any(d in departments for d in ["ventas", "finanzas"]):
                row = db.execute(text(f"""
                    SELECT COALESCE(SUM(i.grandtotal - COALESCE(alloc.paid, 0)), 0),
                           COUNT(i.c_invoice_id)
                    FROM adempiere.c_invoice i
                    LEFT JOIN (
                        SELECT al.c_invoice_id,
                               SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid
                        FROM adempiere.c_allocationline al
                        JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
                        WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL')
                        AND ah.dateacct >= (CURRENT_DATE - INTERVAL '3 years')
                        GROUP BY al.c_invoice_id
                    ) alloc ON alloc.c_invoice_id = i.c_invoice_id
                    WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
                    AND i.dateinvoiced < CURRENT_DATE - INTERVAL '30 days'
                    AND (i.grandtotal - COALESCE(alloc.paid, 0)) > 0
                    {org_filter}
                """)).fetchone()
                if row and row[1] > 0:
                    alerts.append({
                        "type": "warning",
                        "department": "ventas",
                        "title": "Cuentas por cobrar vencidas",
                        "message": f"Hay {row[1]} facturas vencidas (+30 dias) por Bs. {float(row[0]):,.2f}",
                        "metric": "cxc_vencidas",
                        "value": float(row[0]),
                    })

            # Alert: Overdue payables (for finanzas, compras)
            # PERF-100: reemplazar invoiceopen() con LEFT JOIN agregado
            if any(d in departments for d in ["finanzas", "compras_insumos", "compras_productores"]):
                row = db.execute(text(f"""
                    SELECT COALESCE(SUM(i.grandtotal - COALESCE(alloc.paid, 0)), 0),
                           COUNT(i.c_invoice_id)
                    FROM adempiere.c_invoice i
                    LEFT JOIN (
                        SELECT al.c_invoice_id,
                               SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid
                        FROM adempiere.c_allocationline al
                        JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
                        WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL')
                        AND ah.dateacct >= (CURRENT_DATE - INTERVAL '3 years')
                        GROUP BY al.c_invoice_id
                    ) alloc ON alloc.c_invoice_id = i.c_invoice_id
                    WHERE i.issotrx = 'N' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
                    AND i.dateinvoiced < CURRENT_DATE - INTERVAL '30 days'
                    AND (i.grandtotal - COALESCE(alloc.paid, 0)) > 0
                    {org_filter}
                """)).fetchone()
                if row and row[1] > 0:
                    alerts.append({
                        "type": "warning",
                        "department": "finanzas",
                        "title": "Cuentas por pagar vencidas",
                        "message": f"Hay {row[1]} facturas de proveedor vencidas (+30 dias) por Bs. {float(row[0]):,.2f}",
                        "metric": "cxp_vencidas",
                        "value": float(row[0]),
                    })

        finally:
            db.close()
    except Exception as exc:
        logger.warning("Error checking alert conditions: %s", exc)

    # Check custom alert rules
    for rule in _ALERT_RULES:
        if rule["department"] in departments and rule.get("active"):
            alerts.append({
                "type": "custom",
                "department": rule["department"],
                "title": rule["name"],
                "message": f"Regla: {rule['condition']}",
                "metric": rule["metric"],
                "value": rule.get("threshold", 0),
            })

    return {"alerts": alerts, "count": len(alerts)}


@router.post("/alerts/configure")
def configure_alert(
    rule: AlertRule,
    current_user: User = Depends(require_admin),
):
    """Configure a new alert rule (admin only)."""
    _ALERT_RULES.append(rule.model_dump())
    return {"message": f"Alerta '{rule.name}' configurada exitosamente", "total_rules": len(_ALERT_RULES)}


@router.get("/alerts/rules")
def get_alert_rules(
    current_user: User = Depends(require_admin),
):
    """List all configured alert rules."""
    return {"rules": _ALERT_RULES}


# ──────────────────────────────────────────────────────────────
# Cache management (admin)
# ──────────────────────────────────────────────────────────────

@router.get("/cache/stats")
def get_cache_stats(admin: User = Depends(require_admin)):
    """Get cache statistics."""
    return cache_stats()


@router.post("/cache/clear")
def clear_query_cache(admin: User = Depends(require_admin)):
    """Clear the query cache."""
    count = clear_cache()
    return {"message": f"Caché limpiado: {count} entradas eliminadas"}


# ──────────────────────────────────────────────────────────────
# Saved Reports
# ──────────────────────────────────────────────────────────────

class SavedReportCreate(BaseModel):
    name: str
    query: str
    department: str
    schedule: str | None = None  # null, "daily", "weekly"


@router.get("/reports")
def get_saved_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's saved reports."""
    from app.models.saved_report import SavedReport
    reports = (
        db.query(SavedReport)
        .filter(SavedReport.user_id == current_user.id, SavedReport.is_active == True)
        .order_by(SavedReport.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "query": r.query,
            "department": r.department,
            "schedule": r.schedule,
            "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.post("/reports")
def create_saved_report(
    data: SavedReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a query as a report."""
    from app.models.saved_report import SavedReport
    report = SavedReport(
        user_id=current_user.id,
        name=data.name,
        query=data.query,
        department=data.department,
        schedule=data.schedule,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "name": report.name,
        "message": f"Reporte '{report.name}' guardado exitosamente",
    }


@router.delete("/reports/{report_id}")
def delete_saved_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved report."""
    from app.models.saved_report import SavedReport
    report = (
        db.query(SavedReport)
        .filter(SavedReport.id == report_id, SavedReport.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    report.is_active = False
    db.commit()
    return {"message": "Reporte eliminado"}


# ──────────────────────────────────────────────────────────────
# Access control status (admin)
# ──────────────────────────────────────────────────────────────

@router.get("/access-control")
def get_access_control_status(admin: User = Depends(require_admin)):
    """Get current access control configuration."""
    from app.middleware.access_control import (
        _ENFORCE_BUSINESS_HOURS,
        _BUSINESS_HOURS_START,
        _BUSINESS_HOURS_END,
        _ENFORCE_NETWORK,
        _ALLOWED_NETWORKS,
        DEPARTMENT_SENSITIVITY,
        ROLE_MAX_SENSITIVITY,
    )
    return {
        "business_hours": {
            "enforced": _ENFORCE_BUSINESS_HOURS,
            "start": _BUSINESS_HOURS_START,
            "end": _BUSINESS_HOURS_END,
        },
        "network": {
            "enforced": _ENFORCE_NETWORK,
            "allowed_networks": [str(n) for n in _ALLOWED_NETWORKS],
        },
        "sensitivity": {
            "departments": DEPARTMENT_SENSITIVITY,
            "roles": ROLE_MAX_SENSITIVITY,
        },
    }
