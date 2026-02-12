from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.database import get_db
from app.middleware.auth import require_admin, require_supervisor_or_admin
from app.models.user import User, Department
from app.models.audit import AuditLog
from app.models.conversation import Conversation, Message
from app.services.audit import log_action

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
