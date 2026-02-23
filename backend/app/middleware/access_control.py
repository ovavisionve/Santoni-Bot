"""
Access control middleware for SantoniBot.
Enforces:
1. Business hours restriction (configurable)
2. Network/IP whitelist (configurable)
3. Data sensitivity levels per department

These are configurable via environment variables and admin API.
"""

import logging
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network

from fastapi import Request, HTTPException, status

from app.config import get_settings

logger = logging.getLogger("santonibot.access_control")

settings = get_settings()

# ──────────────────────────────────────────────────────────────
# Business hours check
# ──────────────────────────────────────────────────────────────

# Venezuela timezone is UTC-4
_VE_OFFSET = timedelta(hours=-4)

# Default business hours: 6:00 AM to 9:00 PM (generous window)
_BUSINESS_HOURS_START = int(getattr(settings, "business_hours_start", 6))
_BUSINESS_HOURS_END = int(getattr(settings, "business_hours_end", 21))
_ENFORCE_BUSINESS_HOURS = getattr(settings, "enforce_business_hours", False)


def check_business_hours() -> bool:
    """Check if current time is within business hours (Venezuela time)."""
    if not _ENFORCE_BUSINESS_HOURS:
        return True

    now_utc = datetime.now(timezone.utc)
    now_ve = now_utc + _VE_OFFSET
    hour = now_ve.hour

    # Also check weekday (0=Monday, 6=Sunday)
    weekday = now_ve.weekday()
    if weekday >= 6:  # Sunday
        return False

    return _BUSINESS_HOURS_START <= hour < _BUSINESS_HOURS_END


# ──────────────────────────────────────────────────────────────
# Network whitelist check
# ──────────────────────────────────────────────────────────────

# Default: allow all. Set ALLOWED_NETWORKS in .env to restrict
# Format: comma-separated CIDR or IPs, e.g. "192.168.1.0/24,10.0.0.0/8"
_ALLOWED_NETWORKS_RAW = getattr(settings, "allowed_networks", "")
_ENFORCE_NETWORK = bool(_ALLOWED_NETWORKS_RAW)
_ALLOWED_NETWORKS = []

if _ALLOWED_NETWORKS_RAW:
    for net in _ALLOWED_NETWORKS_RAW.split(","):
        net = net.strip()
        if net:
            try:
                _ALLOWED_NETWORKS.append(ip_network(net, strict=False))
            except ValueError:
                logger.warning("Invalid network in ALLOWED_NETWORKS: %s", net)


def check_network(client_ip: str) -> bool:
    """Check if client IP is in the allowed networks."""
    if not _ENFORCE_NETWORK:
        return True

    # Always allow localhost
    if client_ip in ("127.0.0.1", "::1", "localhost"):
        return True

    try:
        addr = ip_address(client_ip)
        return any(addr in net for net in _ALLOWED_NETWORKS)
    except ValueError:
        logger.warning("Invalid client IP: %s", client_ip)
        return False


# ──────────────────────────────────────────────────────────────
# Data sensitivity levels
# ──────────────────────────────────────────────────────────────

# Sensitivity levels: basic (0), financial (1), confidential (2)
# Each department has a default sensitivity level
DEPARTMENT_SENSITIVITY: dict[str, int] = {
    "ventas": 0,         # Basic - sales data
    "produccion": 0,     # Basic - production data
    "compras_insumos": 0,  # Basic - purchase data
    "compras_productores": 0,  # Basic - purchase data
    "contabilidad": 1,   # Financial - accounting data
    "finanzas": 1,       # Financial - financial data
    "rrhh": 2,           # Confidential - HR/salary data
}

# Roles and their maximum sensitivity access
ROLE_MAX_SENSITIVITY: dict[str, int] = {
    "usuario": 1,          # Can see basic + financial
    "vendedor": 0,         # Can only see basic (their sales)
    "supervisor": 2,       # Can see all
    "administrador": 2,    # Can see all
}


def check_sensitivity(department: str, user_sensitivity_level: int) -> bool:
    """Check if user's sensitivity level allows access to the department's data.

    The user's sensitivity_level is stored per-user in the DB and chosen
    by the admin when creating the user.  0=basic, 1=financial, 2=confidential.
    """
    dept_level = DEPARTMENT_SENSITIVITY.get(department, 0)
    return user_sensitivity_level >= dept_level


# ──────────────────────────────────────────────────────────────
# Combined access check (for use in middleware/dependencies)
# ──────────────────────────────────────────────────────────────

def enforce_access_controls(request: Request, user_role: str = "usuario") -> None:
    """
    Enforce all access controls. Raises HTTPException if denied.
    Call this from route handlers or middleware.
    """
    client_ip = request.client.host if request.client else "unknown"

    # 1. Business hours
    if not check_business_hours():
        logger.warning(
            "Access denied: outside business hours. IP=%s, Role=%s",
            client_ip, user_role,
        )
        # Admins can always access
        if user_role != "administrador":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso restringido fuera del horario laboral (6:00 AM - 9:00 PM). Contacta al administrador.",
            )

    # 2. Network whitelist
    if not check_network(client_ip):
        logger.warning(
            "Access denied: IP not in whitelist. IP=%s, Role=%s",
            client_ip, user_role,
        )
        # Admins can access from anywhere
        if user_role != "administrador":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso restringido a la red corporativa de Santoni. Contacta al administrador.",
            )
