"""List agents available to the current user."""

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()

_AGENT_INFO = [
    {"name": "ventas", "display_name": "Ventas", "icon": "ShoppingCart",
     "description": "Facturación, clientes, cobranza, zonas"},
    {"name": "finanzas", "display_name": "Finanzas", "icon": "DollarSign",
     "description": "Bancos, cuentas por cobrar/pagar"},
    {"name": "contabilidad", "display_name": "Contabilidad", "icon": "Calculator",
     "description": "Balance, estados financieros, libro mayor"},
    {"name": "rrhh", "display_name": "RRHH", "icon": "Users",
     "description": "Empleados, nómina, vacaciones, ausentismo"},
    {"name": "produccion", "display_name": "Producción", "icon": "Factory",
     "description": "Órdenes de producción, inventario"},
    {"name": "compras_insumos", "display_name": "Compras Insumos", "icon": "Package",
     "description": "Proveedores, órdenes de compra, stock"},
    {"name": "compras_productores", "display_name": "Compras Productores", "icon": "Wheat",
     "description": "Arroz, maíz, productores, pagos"},
]


@router.get("/agents")
def list_agents(
    current_user: User = Depends(get_current_user),
):
    """Return agents available for the current user based on their permissions."""
    allowed = current_user.allowed_departments
    return [agent for agent in _AGENT_INFO if agent["name"] in allowed]
