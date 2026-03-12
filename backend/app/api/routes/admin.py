import json
from datetime import datetime, timedelta, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Float, text

from app.database import get_db, IdempiereSession
from app.middleware.auth import require_admin, require_supervisor_or_admin
from app.models.user import User, Department
from app.models.audit import AuditLog
from app.models.conversation import Conversation, Message
from app.services.audit import log_action

from app.services.idempiere_role_sync import (
    sync_user_permissions,
    sync_all_user_permissions,
    list_idempiere_users,
    preview_role_mapping,
)

router = APIRouter(prefix="/admin", tags=["Administración"])


@router.get("/stats")
def get_system_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(func.count(User.id)).scalar()
    active_users = (
        db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    )
    total_conversations = db.query(func.count(Conversation.id)).scalar()
    total_messages = db.query(func.count(Message.id)).scalar()

    # Agent usage stats
    agent_stats = (
        db.query(Message.agent_used, func.count(Message.id))
        .filter(Message.agent_used.isnot(None))
        .group_by(Message.agent_used)
        .all()
    )

    return {
        "users": {"total": total_users, "active": active_users},
        "conversations": total_conversations,
        "messages": total_messages,
        "agent_usage": {agent: count for agent, count in agent_stats},
    }


@router.get("/audit-logs")
def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: int | None = None,
    action: str | None = None,
    current_user: User = Depends(require_supervisor_or_admin),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    logs = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else None,
                "full_name": log.user.full_name if log.user else None,
                "action": log.action,
                "resource": log.resource,
                "detail": log.detail,
                "agent_used": log.agent_used,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("/metrics")
def get_usage_metrics(
    days: int = Query(7, ge=1, le=90),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Usage metrics dashboard: daily activity, top users, department breakdown."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # --- Daily message counts ---
    daily_messages = (
        db.query(
            func.date(Message.created_at).label("day"),
            func.count(Message.id).label("count"),
        )
        .filter(Message.created_at >= since)
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
        .all()
    )

    # --- Daily conversation counts ---
    daily_conversations = (
        db.query(
            func.date(Conversation.created_at).label("day"),
            func.count(Conversation.id).label("count"),
        )
        .filter(Conversation.created_at >= since)
        .group_by(func.date(Conversation.created_at))
        .order_by(func.date(Conversation.created_at))
        .all()
    )

    # --- Top users by message count (period) ---
    top_users = (
        db.query(
            User.username,
            User.full_name,
            User.department,
            func.count(Message.id).label("message_count"),
        )
        .join(Conversation, Conversation.user_id == User.id)
        .join(Message, Message.conversation_id == Conversation.id)
        .filter(Message.created_at >= since)
        .group_by(User.id, User.username, User.full_name, User.department)
        .order_by(func.count(Message.id).desc())
        .limit(10)
        .all()
    )

    # --- Department breakdown ---
    dept_stats = (
        db.query(
            User.department,
            func.count(func.distinct(User.id)).label("users"),
            func.count(Message.id).label("messages"),
        )
        .outerjoin(Conversation, Conversation.user_id == User.id)
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .filter(User.is_active == True)
        .group_by(User.department)
        .all()
    )

    # --- Agent response time (average messages per conversation) ---
    avg_msgs = (
        db.query(func.avg(
            db.query(func.count(Message.id))
            .filter(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        ))
        .select_from(Conversation)
        .filter(Conversation.created_at >= since)
        .scalar()
    )

    return {
        "period_days": days,
        "daily_messages": [
            {"date": str(row.day), "count": row.count}
            for row in daily_messages
        ],
        "daily_conversations": [
            {"date": str(row.day), "count": row.count}
            for row in daily_conversations
        ],
        "top_users": [
            {
                "username": row.username,
                "full_name": row.full_name,
                "department": row.department.value if row.department else None,
                "message_count": row.message_count,
            }
            for row in top_users
        ],
        "department_breakdown": [
            {
                "department": row.department.value if row.department else None,
                "active_users": row.users,
                "messages": row.messages,
            }
            for row in dept_stats
        ],
        "avg_messages_per_conversation": round(float(avg_msgs or 0), 1),
    }


# ─── Security Management (for IT at Santoni) ─────────────────


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


@router.get("/users/{user_id}/conversations")
def get_user_conversations(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all conversations for a user (admin audit view)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    result = []
    for conv in conversations:
        msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
            .all()
        )
        result.append({
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "message_count": len(msgs),
            "messages": [
                {
                    "role": m.role.value,
                    "content": m.content,
                    "agent_used": m.agent_used,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ],
        })

    return {
        "user": {
            "id": target.id,
            "username": target.username,
            "full_name": target.full_name,
            "department": target.department.value if target.department else None,
        },
        "conversations": result,
        "total": len(result),
    }


@router.get("/users/{user_id}/conversations/export")
def export_user_conversations(
    user_id: int,
    format: str = Query("txt", regex="^(txt|pdf)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Export all conversations for a user as TXT or PDF (admin audit)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at)
        .all()
    )

    # Build conversation text
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"HISTORIAL DE CONVERSACIONES - {target.full_name} (@{target.username})")
    lines.append(f"Departamento: {target.department.value if target.department else 'N/A'}")
    lines.append(f"Exportado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}")
    lines.append(f"Total conversaciones: {len(conversations)}")
    lines.append("=" * 70)
    lines.append("")

    for conv in conversations:
        msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
            .all()
        )
        created = conv.created_at.strftime("%d/%m/%Y %H:%M") if conv.created_at else "?"
        lines.append(f"--- Conversación: {conv.title} ({created}) ---")
        lines.append("")
        for m in msgs:
            ts = m.created_at.strftime("%H:%M") if m.created_at else ""
            role_label = "USUARIO" if m.role.value == "user" else f"BOT [{m.agent_used or 'general'}]"
            lines.append(f"[{ts}] {role_label}:")
            lines.append(m.content)
            lines.append("")
        lines.append("")

    full_text = "\n".join(lines)
    filename_base = f"conversaciones_{target.username}_{datetime.now().strftime('%Y%m%d')}"

    if format == "txt":
        buf = BytesIO(full_text.encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.txt"'},
        )

    # PDF format
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=20 * mm, rightMargin=20 * mm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ConvTitle", parent=styles["Heading1"],
            fontSize=14, textColor=HexColor("#042387"),
        )
        header_style = ParagraphStyle(
            "ConvHeader", parent=styles["Heading2"],
            fontSize=11, textColor=HexColor("#E06400"), spaceAfter=6,
        )
        user_style = ParagraphStyle(
            "UserMsg", parent=styles["Normal"],
            fontSize=9, leftIndent=10, textColor=HexColor("#333333"), spaceAfter=4,
        )
        bot_style = ParagraphStyle(
            "BotMsg", parent=styles["Normal"],
            fontSize=9, leftIndent=10, textColor=HexColor("#042387"), spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "Meta", parent=styles["Normal"],
            fontSize=8, textColor=HexColor("#888888"),
        )

        story = []
        story.append(Paragraph("ALIMENTOS SANTONI, C.A.", title_style))
        story.append(Paragraph(
            f"Historial de conversaciones - {target.full_name} (@{target.username})",
            meta_style,
        ))
        story.append(Paragraph(
            f"Departamento: {target.department.value if target.department else 'N/A'} | "
            f"Exportado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
            meta_style,
        ))
        story.append(Spacer(1, 12))

        for conv in conversations:
            msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
                .all()
            )
            created = conv.created_at.strftime("%d/%m/%Y %H:%M") if conv.created_at else "?"
            story.append(Paragraph(f"{conv.title} ({created})", header_style))
            for m in msgs:
                ts = m.created_at.strftime("%H:%M") if m.created_at else ""
                # Escape HTML special chars for ReportLab
                content = (m.content or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                # Truncate very long messages for PDF readability
                if len(content) > 2000:
                    content = content[:2000] + "... [truncado]"
                content = content.replace("\n", "<br/>")
                if m.role.value == "user":
                    story.append(Paragraph(f"<b>[{ts}] USUARIO:</b><br/>{content}", user_style))
                else:
                    agent = m.agent_used or "general"
                    story.append(Paragraph(f"<b>[{ts}] BOT [{agent}]:</b><br/>{content}", bot_style))
            story.append(Spacer(1, 10))

        doc.build(story)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="ReportLab no instalado. Usa formato TXT.",
        )


# ──────────────────────────────────────────────────────────────
# Confidence Score Report
# ──────────────────────────────────────────────────────────────

@router.get("/confidence-report")
def get_confidence_report(
    limit: int = Query(50, ge=1, le=500),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    max_score: float = Query(1.0, ge=0.0, le=1.0),
    agent: str | None = Query(None),
    admin: User = Depends(require_supervisor_or_admin),
    db: Session = Depends(get_db),
):
    """Confidence Score report for the last N interactions.

    Filters:
    - limit: number of interactions (default 50)
    - min_score / max_score: filter by confidence range
    - agent: filter by agent name
    """
    query = (
        db.query(
            Message.id,
            Message.conversation_id,
            Message.content,
            Message.agent_used,
            Message.confidence_score,
            Message.metadata_json,
            Message.created_at,
            Conversation.user_id,
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Message.role == "assistant")
        .filter(Message.confidence_score.isnot(None))
    )

    if min_score > 0.0:
        query = query.filter(Message.confidence_score >= min_score)
    if max_score < 1.0:
        query = query.filter(Message.confidence_score <= max_score)
    if agent:
        query = query.filter(Message.agent_used == agent)

    messages = (
        query.order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )

    # Get user info for the report
    user_ids = list({m.user_id for m in messages})
    users = {
        u.id: {"username": u.username, "full_name": u.full_name}
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    # Build report
    interactions = []
    for m in messages:
        meta = {}
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        user_info = users.get(m.user_id, {})
        # Get the user message that preceded this assistant message
        user_msg = (
            db.query(Message.content)
            .filter(
                Message.conversation_id == m.conversation_id,
                Message.role == "user",
                Message.created_at < m.created_at,
            )
            .order_by(Message.created_at.desc())
            .first()
        )

        interactions.append({
            "message_id": m.id,
            "conversation_id": m.conversation_id,
            "timestamp": m.created_at.isoformat() if m.created_at else None,
            "user": user_info.get("full_name", "?"),
            "username": user_info.get("username", "?"),
            "pregunta": user_msg[0][:200] if user_msg else "?",
            "respuesta": m.content[:300] if m.content else "",
            "agent_used": m.agent_used,
            "confidence_score": m.confidence_score,
            "score_breakdown": meta.get("score_breakdown"),
            "match_type": meta.get("match_type"),
        })

    # Summary stats
    scores = [i["confidence_score"] for i in interactions if i["confidence_score"] is not None]
    low_confidence = [i for i in interactions if (i["confidence_score"] or 0) < 0.5]

    summary = {
        "total_interactions": len(interactions),
        "score_promedio": round(sum(scores) / len(scores), 2) if scores else 0,
        "score_minimo": round(min(scores), 2) if scores else 0,
        "score_maximo": round(max(scores), 2) if scores else 0,
        "interacciones_baja_confianza": len(low_confidence),
        "por_agente": {},
    }

    # Breakdown by agent
    agent_scores: dict[str, list[float]] = {}
    for i in interactions:
        ag = i["agent_used"] or "unknown"
        agent_scores.setdefault(ag, []).append(i["confidence_score"] or 0)
    for ag, sc in agent_scores.items():
        summary["por_agente"][ag] = {
            "total": len(sc),
            "promedio": round(sum(sc) / len(sc), 2),
        }

    return {
        "resumen": summary,
        "interacciones": interactions,
    }


@router.get("/confidence-report/low")
def get_low_confidence_interactions(
    limit: int = Query(50, ge=1, le=500),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    admin: User = Depends(require_supervisor_or_admin),
    db: Session = Depends(get_db),
):
    """Get interactions with confidence score below threshold (failures).

    This is the endpoint the Santoni IT manager requested:
    'Confidence Score de las últimas 50 interacciones fallidas'
    """
    query = (
        db.query(
            Message.id,
            Message.conversation_id,
            Message.content,
            Message.agent_used,
            Message.confidence_score,
            Message.metadata_json,
            Message.created_at,
            Conversation.user_id,
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Message.role == "assistant")
        .filter(Message.confidence_score.isnot(None))
        .filter(Message.confidence_score < threshold)
        .order_by(Message.confidence_score.asc())
        .limit(limit)
    )

    messages = query.all()

    user_ids = list({m.user_id for m in messages})
    users = {
        u.id: {"username": u.username, "full_name": u.full_name}
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    interactions = []
    for m in messages:
        meta = {}
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        user_info = users.get(m.user_id, {})
        user_msg = (
            db.query(Message.content)
            .filter(
                Message.conversation_id == m.conversation_id,
                Message.role == "user",
                Message.created_at < m.created_at,
            )
            .order_by(Message.created_at.desc())
            .first()
        )

        breakdown = meta.get("score_breakdown", {})
        interactions.append({
            "message_id": m.id,
            "timestamp": m.created_at.isoformat() if m.created_at else None,
            "user": user_info.get("full_name", "?"),
            "pregunta": user_msg[0][:200] if user_msg else "?",
            "agent_used": m.agent_used,
            "confidence_score": m.confidence_score,
            "routing_score": breakdown.get("routing"),
            "data_score": breakdown.get("data"),
            "match_type": meta.get("match_type") or breakdown.get("match_type"),
            "causa_probable": _diagnose_low_confidence(
                m.confidence_score, m.agent_used, breakdown, meta,
            ),
        })

    return {
        "threshold": threshold,
        "total_baja_confianza": len(interactions),
        "interacciones": interactions,
    }


def _diagnose_low_confidence(
    score: float | None,
    agent: str | None,
    breakdown: dict,
    meta: dict,
) -> str:
    """Generate a human-readable diagnosis for a low-confidence interaction."""
    match_type = meta.get("match_type") or breakdown.get("match_type", "")

    if agent == "general" and match_type == "sin_match":
        return "Sin keywords reconocidos - pregunta fue al agente general sin datos"
    if agent == "general" and match_type == "saludo_directo":
        return "Saludo o pregunta general - no requiere datos"
    if agent == "orchestrator":
        if meta.get("classification") == "no_access":
            return "Usuario sin permisos para el departamento detectado"
        return "Acceso denegado al departamento"
    if match_type == "followup_last_agent":
        if breakdown.get("data", 0) < 0.5:
            return "Follow-up sin datos - posible pérdida de contexto"
        return "Follow-up al agente anterior - confianza media"
    if match_type == "keyword_bloqueado_fallback_last_agent":
        return "Keyword matcheó departamento bloqueado, se usó agente anterior como fallback"
    if match_type == "fallback_ventas":
        return "Sin keywords específicos, se asumió ventas por palabras genéricas"
    if breakdown.get("data", 1) < 0.5:
        return "Agente correcto pero no se encontraron datos para la consulta"

    return "Confianza baja - revisar manualmente"


# ──────────────────────────────────────────────────────────────
# iDempiere Role Sync (maps iDempiere roles → bot permissions)
# ──────────────────────────────────────────────────────────────


@router.get("/idempiere-users")
def get_idempiere_users_list(
    admin: User = Depends(require_admin),
):
    """List iDempiere users with their roles (for linking to bot users)."""
    try:
        users = list_idempiere_users()
        return {"total": len(users), "users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando iDempiere: {e}")


@router.get("/role-sync/preview/{ad_user_id}")
def preview_role_sync(
    ad_user_id: int,
    admin: User = Depends(require_admin),
):
    """Preview what bot permissions would be assigned for an iDempiere user.

    Call this before linking a bot user to verify the mapping is correct.
    """
    try:
        return preview_role_mapping(ad_user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@router.post("/role-sync/user/{user_id}")
def sync_single_user_roles(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync a single bot user's permissions from their iDempiere roles.

    The user must have ad_user_id set (linked to iDempiere).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    result = sync_user_permissions(db, user)

    log_action(
        db,
        user_id=admin.id,
        action="role_sync",
        resource="security",
        detail=(
            f"Sync roles para {result.username}: "
            f"{result.departments_before} → {result.departments_after} "
            f"({result.status})"
        ),
    )

    return {
        "user_id": result.user_id,
        "username": result.username,
        "ad_user_id": result.ad_user_id,
        "status": result.status,
        "detail": result.detail,
        "departments": {
            "before": result.departments_before,
            "after": result.departments_after,
        },
        "org_ids": {
            "before": result.org_ids_before,
            "after": result.org_ids_after,
        },
    }


@router.post("/role-sync/all")
def sync_all_users_roles(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync permissions for ALL bot users linked to iDempiere.

    Only processes users with ad_user_id set and is_active=true.
    """
    results = sync_all_user_permissions(db)

    log_action(
        db,
        user_id=admin.id,
        action="role_sync_all",
        resource="security",
        detail=f"Sync masivo: {len(results)} usuarios procesados",
    )

    synced = [r for r in results if r.status == "synced"]
    errors = [r for r in results if r.status == "error"]
    no_roles = [r for r in results if r.status == "no_roles_found"]

    return {
        "total_processed": len(results),
        "synced": len(synced),
        "errors": len(errors),
        "no_roles_found": len(no_roles),
        "results": [
            {
                "user_id": r.user_id,
                "username": r.username,
                "ad_user_id": r.ad_user_id,
                "status": r.status,
                "detail": r.detail,
                "departments_after": r.departments_after,
                "org_ids_after": r.org_ids_after,
            }
            for r in results
        ],
    }
