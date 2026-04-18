"""Admin endpoints: confidence reports, trends, low-confidence analysis."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Float, text

from app.database import get_db
from app.middleware.auth import require_admin, require_supervisor_or_admin
from app.models.user import User
from app.services.audit import log_action
from datetime import datetime, timedelta, timezone
from app.models.conversation import Conversation, Message

router = APIRouter(prefix="/admin", tags=["Administración"])

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


@router.get("/confidence-report/trends")
def get_confidence_trends(
    days: int = Query(30, ge=1, le=180),
    admin: User = Depends(require_supervisor_or_admin),
    db: Session = Depends(get_db),
):
    """Confidence score trends over time.

    Shows daily averages, low-confidence counts, and top failure causes
    to track if the system is improving or degrading.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # --- Daily confidence averages ---
    daily_stats = (
        db.query(
            func.date(Message.created_at).label("day"),
            func.avg(Message.confidence_score).label("avg_score"),
            func.min(Message.confidence_score).label("min_score"),
            func.count(Message.id).label("total"),
            func.count(
                func.nullif(Message.confidence_score < 0.5, False)
            ).label("low_count"),
        )
        .filter(
            Message.role == "assistant",
            Message.confidence_score.isnot(None),
            Message.created_at >= since,
        )
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
        .all()
    )

    # --- Per-agent trends (avg score per agent in the period) ---
    agent_trends = (
        db.query(
            Message.agent_used,
            func.avg(Message.confidence_score).label("avg_score"),
            func.count(Message.id).label("total"),
            func.count(
                func.nullif(Message.confidence_score < 0.5, False)
            ).label("low_count"),
        )
        .filter(
            Message.role == "assistant",
            Message.confidence_score.isnot(None),
            Message.created_at >= since,
        )
        .group_by(Message.agent_used)
        .order_by(func.avg(Message.confidence_score))
        .all()
    )

    # --- Diagnosis distribution for low-confidence ---
    low_msgs = (
        db.query(Message.agent_used, Message.confidence_score, Message.metadata_json)
        .filter(
            Message.role == "assistant",
            Message.confidence_score.isnot(None),
            Message.confidence_score < 0.5,
            Message.created_at >= since,
        )
        .all()
    )

    causa_counts: dict[str, int] = {}
    for m in low_msgs:
        meta = {}
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass
        breakdown = meta.get("score_breakdown", {})
        causa = _diagnose_low_confidence(m.confidence_score, m.agent_used, breakdown, meta)
        causa_counts[causa] = causa_counts.get(causa, 0) + 1

    # Sort causes by frequency
    causas_ordenadas = sorted(causa_counts.items(), key=lambda x: x[1], reverse=True)

    # --- Verdict: dataset vs threshold ---
    total_low = len(low_msgs)
    dataset_causes = sum(
        c for label, c in causa_counts.items()
        if "keywords" in label.lower() or "fallback" in label.lower() or "ventas" in label.lower()
    )
    data_causes = sum(
        c for label, c in causa_counts.items()
        if "datos" in label.lower() or "data" in label.lower()
    )

    if total_low == 0:
        veredicto = "Sin interacciones de baja confianza en el período - sistema funcionando bien"
    elif dataset_causes > data_causes and dataset_causes > total_low * 0.5:
        veredicto = (
            f"PROBLEMA DE DATASET: {dataset_causes}/{total_low} fallos "
            f"({round(dataset_causes/total_low*100)}%) son por keywords no reconocidos. "
            f"Se recomienda ampliar el dataset de entrenamiento con las preguntas que fallan."
        )
    elif data_causes > dataset_causes and data_causes > total_low * 0.5:
        veredicto = (
            f"PROBLEMA DE DATOS: {data_causes}/{total_low} fallos "
            f"({round(data_causes/total_low*100)}%) son porque iDempiere no tiene datos "
            f"para el período consultado. El clasificador funciona bien."
        )
    else:
        veredicto = (
            f"MIXTO: {dataset_causes} fallos por dataset, {data_causes} por datos, "
            f"{total_low - dataset_causes - data_causes} por otras causas. "
            f"Revisar causas detalladas abajo."
        )

    return {
        "periodo_dias": days,
        "veredicto": veredicto,
        "tendencia_diaria": [
            {
                "fecha": str(row.day),
                "score_promedio": round(float(row.avg_score or 0), 2),
                "score_minimo": round(float(row.min_score or 0), 2),
                "total_interacciones": row.total,
                "baja_confianza": row.low_count,
            }
            for row in daily_stats
        ],
        "por_agente": [
            {
                "agente": row.agent_used or "unknown",
                "score_promedio": round(float(row.avg_score or 0), 2),
                "total": row.total,
                "baja_confianza": row.low_count,
            }
            for row in agent_trends
        ],
        "causas_de_fallo": [
            {"causa": label, "cantidad": count, "porcentaje": round(count / total_low * 100, 1)}
            for label, count in causas_ordenadas
        ] if total_low > 0 else [],
        "totales": {
            "interacciones_periodo": sum(r.total for r in daily_stats),
            "baja_confianza_periodo": total_low,
            "tasa_fallo_pct": round(
                total_low / sum(r.total for r in daily_stats) * 100, 1
            ) if daily_stats and sum(r.total for r in daily_stats) > 0 else 0,
        },
    }


# ──────────────────────────────────────────────────────────────
# iDempiere Role Sync (maps iDempiere roles → bot permissions)
# ──────────────────────────────────────────────────────────────


