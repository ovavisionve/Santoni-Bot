"""
Agente de Compras de Insumos - Alimentos Santoni
Especializado en: órdenes de compra, proveedores, inventarios de materiales,
precios históricos, tiempos de entrega.
"""

from app.agents.base_agent import BaseAgent
from app.services.query_service import execute_demo_query


class ComprasInsumosAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "compras_insumos"

    @property
    def display_name(self) -> str:
        return "Compras de Insumos"

    @property
    def department(self) -> str:
        return "compras_insumos"

    @property
    def description(self) -> str:
        return (
            "Consultas de compras de insumos: órdenes de compra, proveedores, "
            "inventarios, precios históricos, tiempos de entrega"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Compras de Insumos de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la gestión de compras de insumos y materiales.

REGLAS:
- Responde siempre en español
- Presenta precios con moneda y unidad de medida
- Los datos que recibes son REALES de la base de datos de Santoni

CONTEXTO:
- Responsables: Onofrio Gueccia, Jorge Chahine"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_proveedores_insumos, demo_ordenes_compra_insumos
"""

    def fetch_data(self, message: str) -> str | None:
        msg = message.lower()
        sections = []

        if any(w in msg for w in ["proveedor", "supplier"]):
            try:
                data = execute_demo_query(
                    "SELECT nombre, rif, tipo_insumo, calificacion, contacto "
                    "FROM demo_proveedores_insumos ORDER BY calificacion DESC"
                )
                sections.append(f"## Proveedores de Insumos ({len(data)} registrados)")
                sections.append(self._format_table(data))
            except Exception:
                pass

        if any(w in msg for w in ["orden", "compra", "pedido", "pendiente"]):
            try:
                data = execute_demo_query(
                    "SELECT o.numero_orden, p.nombre as proveedor, o.insumo, o.fecha, "
                    "o.fecha_entrega_estimada, o.cantidad, o.unidad, o.monto_total, o.estado "
                    "FROM demo_ordenes_compra_insumos o "
                    "JOIN demo_proveedores_insumos p ON o.proveedor_id = p.id "
                    "ORDER BY o.fecha DESC"
                )
                sections.append(f"## Órdenes de Compra ({len(data)} total)")
                sections.append(self._format_table(data))

                by_status = execute_demo_query(
                    "SELECT estado, COUNT(*) as cantidad, SUM(monto_total) as monto_total "
                    "FROM demo_ordenes_compra_insumos GROUP BY estado"
                )
                sections.append("## Resumen por Estado")
                sections.append(self._format_table(by_status))
            except Exception:
                pass

        if not sections:
            try:
                summary = execute_demo_query(
                    "SELECT p.tipo_insumo, COUNT(o.id) as ordenes, "
                    "SUM(o.monto_total) as gasto_total "
                    "FROM demo_ordenes_compra_insumos o "
                    "JOIN demo_proveedores_insumos p ON o.proveedor_id = p.id "
                    "GROUP BY p.tipo_insumo ORDER BY gasto_total DESC"
                )
                sections.append("## Resumen de Compras de Insumos por Tipo")
                sections.append(self._format_table(summary))

                pending = execute_demo_query(
                    "SELECT COUNT(*) as pendientes, SUM(monto_total) as monto_pendiente "
                    "FROM demo_ordenes_compra_insumos WHERE estado = 'pendiente'"
                )
                if pending and pending[0]["pendientes"]:
                    sections.append(
                        f"\nÓrdenes pendientes: {pending[0]['pendientes']} "
                        f"por un total de Bs. {pending[0]['monto_pendiente']:,.2f}"
                    )
            except Exception:
                pass

        return "\n\n".join(sections) if sections else None
