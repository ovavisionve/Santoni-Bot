"""Admin API routes — split into sub-modules by domain.

main.py uses `admin.router` so we merge all sub-routers here.
"""

from fastapi import APIRouter

from .stats import router as stats_router
from .security import router as security_router
from .conversations import router as conversations_router
from .confidence import router as confidence_router
from .idempiere_sync import router as idempiere_router
from .sql_audit import router as sql_audit_router

router = APIRouter()
router.include_router(stats_router)
router.include_router(security_router)
router.include_router(conversations_router)
router.include_router(confidence_router)
router.include_router(idempiere_router)
router.include_router(sql_audit_router)
