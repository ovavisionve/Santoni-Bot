"""iDempiere → bot role sync.

Public API re-exported for backward compatibility with callers that used
to import from ``app.services.idempiere_role_sync`` as a single module.
"""

from .mapping import SyncResult
from .queries import list_idempiere_users
from .sync import (
    bulk_import_idempiere_users,
    preview_role_mapping,
    sync_all_user_permissions,
    sync_user_permissions,
)

__all__ = [
    "SyncResult",
    "bulk_import_idempiere_users",
    "list_idempiere_users",
    "preview_role_mapping",
    "sync_all_user_permissions",
    "sync_user_permissions",
]
