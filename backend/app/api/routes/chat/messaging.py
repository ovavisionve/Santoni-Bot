"""/stream (SSE) and / (POST) endpoints — the core chat handlers."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.middleware.auth import get_current_user
from app.middleware.access_control import enforce_access_controls
from app.models.user import User
from app.models.conversation import Message, MessageRole
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.audit import log_action
from app.services.cache import (
    get_cached_response,
    set_cached_response,
    get_data_timestamp,
)

from .helpers import _get_or_create_conversation, _get_history, _get_last_agent

logger = logging.getLogger("santonibot.chat")

router = APIRouter()


# ──────────────────────────────────────────────────────────────
# Streaming endpoint (SSE) — primary, fast
# ──────────────────────────────────────────────────────────────

@router.post("/stream")
async def stream_message(
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream response tokens via Server-Sent Events (SSE)."""
    # Late import so unittest.mock.patch("app.api.routes.chat.orchestrator")
    # replaces the reference seen here at call time.
    from app.api.routes import chat as _chat

    enforce_access_controls(request, current_user.role.value)

    if data.file_id:
        return await send_message(data, request, current_user, db)

    conversation = _get_or_create_conversation(
        db, current_user.id, data.conversation_id, data.message
    )

    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=data.message,
    )
    db.add(user_msg)
    db.commit()

    history = _get_history(db, conversation.id)
    last_agent = _get_last_agent(db, conversation.id)

    # ── FIX 15/Abr/2026: intentar SQL Directo ANTES del classificador ──
    sql_result_pre = await _chat.orchestrator._try_sql_direct(data.message, current_user, history)

    if sql_result_pre is not None:
        agent_name = "sql_direct"
        routing_score = 1.0
        match_type = "sql_direct"
    else:
        agent_name, routing_score, match_type = await _chat.orchestrator.get_stream_agent_name(
            data.message, current_user, last_agent=last_agent,
        )

    conv_id = conversation.id
    user_id = current_user.id
    message_text = data.message
    ip_addr = request.client.host if request.client else None

    cached = None if sql_result_pre is not None else get_cached_response(message_text, agent_name)
    data_ts = get_data_timestamp()

    async def event_generator():
        full_response = []

        yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv_id, 'agent': agent_name, 'timestamp': data_ts, 'routing_score': routing_score})}\n\n"

        if cached:
            full_response.append(cached["response"])
            yield f"data: {json.dumps({'type': 'token', 'content': cached['response']})}\n\n"
        elif sql_result_pre is not None:
            full_response.append(sql_result_pre["response"])
            yield f"data: {json.dumps({'type': 'token', 'content': sql_result_pre['response']})}\n\n"
        else:
            try:
                async for token in _chat.orchestrator.stream(
                    message=message_text,
                    user=current_user,
                    history=history,
                    last_agent=last_agent,
                ):
                    full_response.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            except Exception as exc:
                logger.error("Streaming error: %s: %s", type(exc).__name__, exc, exc_info=True)
                error_msg = f"Error al consultar el modelo de IA: {type(exc).__name__}"
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                full_response.append(error_msg)

        complete_text = "".join(full_response)
        if not cached and "Error al consultar" not in complete_text:
            set_cached_response(message_text, agent_name, complete_text, agent_name)

        try:
            save_db = SessionLocal()
            try:
                from app.agents.orchestrator import compute_confidence_score
                _no_data_markers = [
                    "Error al consultar",
                    "no se encontraron datos",
                    "no arrojó resultados",
                    "no hay registros",
                    "no hay datos",
                    "no tengo esa información",
                    "intente de nuevo",
                ]
                has_data = (
                    bool(complete_text)
                    and not any(marker in complete_text for marker in _no_data_markers)
                )
                conf_score, score_breakdown = compute_confidence_score(
                    routing_score, has_data, agent_name,
                )
                score_breakdown["match_type"] = match_type
                meta_dict = {
                    "confidence_score": conf_score,
                    "score_breakdown": score_breakdown,
                    "match_type": match_type,
                }
                assistant_msg = Message(
                    conversation_id=conv_id,
                    role=MessageRole.ASSISTANT,
                    content=complete_text,
                    agent_used=agent_name,
                    confidence_score=conf_score,
                    metadata_json=json.dumps(meta_dict),
                )
                save_db.add(assistant_msg)
                save_db.commit()
                save_db.refresh(assistant_msg)
                msg_id = assistant_msg.id

                log_action(
                    save_db,
                    user_id=user_id,
                    action="chat_query",
                    resource="chat",
                    detail=f"Consulta: {message_text}",
                    agent_used=agent_name,
                    ip_address=ip_addr,
                )
            finally:
                save_db.close()
        except Exception as save_exc:
            logger.error("Error saving streamed response: %s", save_exc)
            msg_id = 0

        yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'conversation_id': conv_id, 'agent_used': agent_name})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────────────────────────
# Non-streaming endpoint (fallback, document analysis)
# ──────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def send_message(
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.api.routes import chat as _chat

    enforce_access_controls(request, current_user.role.value)

    conversation = _get_or_create_conversation(
        db, current_user.id, data.conversation_id, data.message
    )

    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=data.message,
    )
    db.add(user_msg)
    db.commit()

    history = _get_history(db, conversation.id)
    last_agent = _get_last_agent(db, conversation.id)

    document = None
    if data.file_id:
        from app.services.document_service import read_document
        document = read_document(data.file_id)
        if document:
            logger.info("Document attached: %s (%s)", document.get("filename"), document["type"])

    try:
        result = await _chat.orchestrator.process(
            message=data.message,
            user=current_user,
            history=history,
            document=document,
            last_agent=last_agent,
        )
    except Exception as exc:
        logger.error(
            "Error processing chat message: %s: %s",
            type(exc).__name__, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Error al consultar el modelo de IA: {type(exc).__name__}: {exc}",
        )

    conf_score = result.get("confidence_score")
    score_breakdown = result.get("score_breakdown")
    metadata = result.get("metadata") or {}
    meta_dict = {
        "confidence_score": conf_score,
        "score_breakdown": score_breakdown,
        **metadata,
    }
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result["response"],
        agent_used=result.get("agent_used"),
        confidence_score=conf_score,
        metadata_json=json.dumps(meta_dict) if meta_dict else None,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    action = "access_denied" if (metadata.get("classification") == "no_access" or metadata.get("access_denied")) else "chat_query"
    log_action(
        db,
        user_id=current_user.id,
        action=action,
        resource="chat",
        detail=f"{'ACCESO DENEGADO - ' if action == 'access_denied' else ''}Consulta: {data.message}",
        agent_used=result.get("agent_used"),
        ip_address=request.client.host if request.client else None,
    )

    return ChatResponse(
        message=result["response"],
        message_id=assistant_msg.id,
        conversation_id=conversation.id,
        agent_used=result.get("agent_used"),
        metadata=result.get("metadata"),
    )
