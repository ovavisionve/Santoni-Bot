"""Chat API package — composes agents, messaging, conversations, and export routes.

The shared ``orchestrator`` instance lives at this module's namespace so tests
that ``@patch("app.api.routes.chat.orchestrator")`` continue to work.
"""

from fastapi import APIRouter

from app.agents.orchestrator import Orchestrator

from .agents import router as _agents_router
from .messaging import router as _messaging_router
from .conversations import router as _conversations_router
from .exports import router as _exports_router

router = APIRouter(prefix="/chat", tags=["Chat"])
orchestrator = Orchestrator()

# Order matters: /conversations/{id}/export is declared before /conversations/export-all
# in the original file, keep identical ordering here.
router.include_router(_agents_router)
router.include_router(_messaging_router)
router.include_router(_conversations_router)
router.include_router(_exports_router)

__all__ = ["router", "orchestrator"]
