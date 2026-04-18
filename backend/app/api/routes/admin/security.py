"""Admin endpoints: locked users, unlock, security overview."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Float, text

from app.database import get_db
from app.middleware.auth import require_admin, require_supervisor_or_admin
from app.models.user import User
from app.services.audit import log_action
from datetime import datetime, timedelta, timezone
from app.models.audit import AuditLog
from app.models.conversation import Conversation, Message
from app.models.user import Department

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.get("/security/locked-users")
def get_locked_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all currently locked user accounts. For IT team at Santoni."""
    now = datetime.now(timezone.utc)
    locked = (
        db.query(User)
        .filter(User.locked_until.isnot(None), User.locked_until > now)
        .all()
    )

    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "department": u.department.value,
            "failed_attempts": u.failed_login_attempts,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
            "remaining_minutes": max(
                0,
                int((u.locked_until - now).total_seconds() / 60) + 1,
            )
            if u.locked_until
            else 0,
        }
        for u in locked
    ]


@router.post("/security/unlock-user/{user_id}")
def unlock_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unlock a locked user account. For IT team at Santoni."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    log_action(
        db,
        user_id=admin.id,
        action="account_unlocked",
        resource="security",
        detail=f"Cuenta desbloqueada: {user.username} (por {admin.username})",
    )

    return {"message": f"Cuenta de {user.username} desbloqueada exitosamente"}


# ─── iDempiere Data Diagnostic ───────────────────────────────


@router.get("/diagnostico-idempiere")
def diagnostico_idempiere(admin: User = Depends(require_admin)):
    """
    Diagnóstico completo de la conexión a iDempiere.
    Muestra datos reales para verificar que el bot navega la data de Santoni.
    Solo accesible por administradores.
    """
    results = {}
    db = IdempiereSession()
    try:
        # 1. Conexión básica
        try:
            row = db.execute(text("SELECT version()")).fetchone()
            results["conexion"] = {"status": "ok", "version": row[0]}
        except Exception as e:
            return {"conexion": {"status": "error", "detalle": str(e)}}

        # 2. Organizaciones
        try:
            orgs = db.execute(text(
                "SELECT ad_org_id, value, name FROM adempiere.ad_org "
                "WHERE isactive = 'Y' AND ad_org_id > 0 ORDER BY name"
            )).fetchall()
            results["organizaciones"] = [
                {"id": r[0], "codigo": r[1], "nombre": r[2]} for r in orgs
            ]
        except Exception as e:
            results["organizaciones"] = {"error": str(e)}

        # 3. Facturas de venta recientes (últimas 5)
        try:
            facturas = db.execute(text(
                "SELECT i.documentno, i.dateinvoiced, i.grandtotal, "
                "       bp.name AS cliente, o.name AS organizacion "
                "FROM adempiere.c_invoice i "
                "JOIN adempiere.c_bpartner bp ON bp.c_bpartner_id = i.c_bpartner_id "
                "JOIN adempiere.ad_org o ON o.ad_org_id = i.ad_org_id "
                "WHERE i.issotrx = 'Y' AND i.docstatus = 'CO' "
                "ORDER BY i.dateinvoiced DESC LIMIT 5"
            )).fetchall()
            results["ultimas_facturas_venta"] = [
                {
                    "numero": r[0],
                    "fecha": str(r[1]),
                    "monto": float(r[2]) if r[2] else 0,
                    "cliente": r[3],
                    "organizacion": r[4],
                }
                for r in facturas
            ]
        except Exception as e:
            results["ultimas_facturas_venta"] = {"error": str(e)}

        # 4. Socios de negocio (clientes top 5 por nombre)
        try:
            clientes = db.execute(text(
                "SELECT bp.value, bp.name, bp.name2 "
                "FROM adempiere.c_bpartner bp "
                "WHERE bp.isactive = 'Y' AND bp.iscustomer = 'Y' "
                "ORDER BY bp.name LIMIT 5"
            )).fetchall()
            results["muestra_clientes"] = [
                {"codigo": r[0], "nombre": r[1], "nombre2": r[2]} for r in clientes
            ]
        except Exception as e:
            results["muestra_clientes"] = {"error": str(e)}

        # 5. Empleados activos (muestra)
        try:
            empleados = db.execute(text(
                "SELECT bp.name, bp.value "
                "FROM adempiere.c_bpartner bp "
                "WHERE bp.isactive = 'Y' AND bp.isemployee = 'Y' "
                "ORDER BY bp.name LIMIT 5"
            )).fetchall()
            results["muestra_empleados"] = [
                {"nombre": r[0], "codigo": r[1]} for r in empleados
            ]
        except Exception as e:
            results["muestra_empleados"] = {"error": str(e)}

        # 6. Productos (muestra)
        try:
            productos = db.execute(text(
                "SELECT p.value, p.name, p.producttype "
                "FROM adempiere.m_product p "
                "WHERE p.isactive = 'Y' "
                "ORDER BY p.name LIMIT 5"
            )).fetchall()
            results["muestra_productos"] = [
                {"codigo": r[0], "nombre": r[1], "tipo": r[2]} for r in productos
            ]
        except Exception as e:
            results["muestra_productos"] = {"error": str(e)}

        # 7. Cuentas contables (muestra)
        try:
            cuentas = db.execute(text(
                "SELECT ev.value, ev.name "
                "FROM adempiere.c_elementvalue ev "
                "WHERE ev.isactive = 'Y' AND ev.issummary = 'N' "
                "ORDER BY ev.value LIMIT 5"
            )).fetchall()
            results["muestra_cuentas_contables"] = [
                {"codigo": r[0], "nombre": r[1]} for r in cuentas
            ]
        except Exception as e:
            results["muestra_cuentas_contables"] = {"error": str(e)}

        # 8. Conteo de tablas principales
        try:
            counts = {}
            for table, label in [
                ("c_invoice", "facturas"),
                ("c_order", "ordenes"),
                ("c_bpartner", "socios_negocio"),
                ("m_product", "productos"),
                ("c_payment", "pagos"),
                ("fact_acct", "asientos_contables"),
            ]:
                row = db.execute(text(
                    f"SELECT COUNT(*) FROM adempiere.{table}"
                )).fetchone()
                counts[label] = row[0]
            results["conteo_registros"] = counts
        except Exception as e:
            results["conteo_registros"] = {"error": str(e)}

    finally:
        db.close()

    return results


@router.get("/security/overview")
def security_overview(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Security dashboard overview. For IT team at Santoni."""
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # Failed logins last 24h
    failed_24h = (
        db.query(func.count(AuditLog.id))
        .filter(
            AuditLog.action == "login_failed",
            AuditLog.created_at >= last_24h,
        )
        .scalar()
    )

    # Account lockouts last 7 days
    lockouts_7d = (
        db.query(func.count(AuditLog.id))
        .filter(
            AuditLog.action == "account_locked",
            AuditLog.created_at >= last_7d,
        )
        .scalar()
    )

    # Currently locked accounts
    locked_now = (
        db.query(func.count(User.id))
        .filter(User.locked_until.isnot(None), User.locked_until > now)
        .scalar()
    )

    # Users with 2FA enabled
    totp_enabled = (
        db.query(func.count(User.id))
        .filter(User.totp_enabled == True, User.is_active == True)
        .scalar()
    )
    total_active = (
        db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    )

    # Suspicious IPs (most failed logins)
    suspicious_ips = (
        db.query(AuditLog.ip_address, func.count(AuditLog.id).label("count"))
        .filter(
            AuditLog.action == "login_failed",
            AuditLog.created_at >= last_7d,
            AuditLog.ip_address.isnot(None),
        )
        .group_by(AuditLog.ip_address)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )

    return {
        "failed_logins_24h": failed_24h,
        "account_lockouts_7d": lockouts_7d,
        "currently_locked": locked_now,
        "totp_enabled_users": totp_enabled,
        "total_active_users": total_active,
        "totp_coverage_pct": round(
            (totp_enabled / total_active * 100) if total_active else 0, 1
        ),
        "suspicious_ips": [
            {"ip": ip, "failed_attempts": count} for ip, count in suspicious_ips
        ],
    }


# ─── Conversation audit / export ─────────────────────────────


