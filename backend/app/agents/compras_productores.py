"""
Agente de Compras a Productores - Alimentos Santoni
Especializado en: compras de materia prima agrícola (arroz, maíz) a productores,
volúmenes, precios por kilo/tonelada, pagos pendientes, productores registrados.
"""

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import build_producer_purchases, execute_demo_query


class ComprasProductoresAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "compras_productores"

    @property
    def display_name(self) -> str:
        return "Compras a Productores"

    @property
    def department(self) -> str:
        return "compras_productores"

    @property
    def description(self) -> str:
        return (
            "Consultas de compras a productores agrícolas: arroz paddy, maíz, "
            "volúmenes, precios, pagos pendientes, productores registrados"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Compras a Productores de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la gestión de compras de materia prima agrícola a productores.

REGLAS:
- Responde siempre en español
- Presenta volúmenes en kg y toneladas
- Presenta precios en Bs./kg
- Distingue entre Arroz Paddy Húmedo y Maíz
- Los datos que recibes son REALES de la base de datos de Santoni

CONTEXTO:
- Responsable: Marlenis Figueredo
- Productos: Arroz Paddy Húmedo, Maíz
- Zonas productoras: Portuguesa, Barinas, Apure, Lara, Cojedes"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_productores, demo_compras_productores
"""

    def fetch_data(self, message: str) -> str | None:
        msg = message.lower()
        sections = []

        anio = datetime.now().year
        year_match = re.search(r'20\d{2}', message)
        if year_match:
            anio = int(year_match.group())

        producto = None
        if "arroz" in msg:
            producto = "Arroz Paddy Húmedo"
        elif "maíz" in msg or "maiz" in msg:
            producto = "Maíz"

        summary = build_producer_purchases(producto=producto, anio=anio)
        sections.append(self._format_summary(summary, f"Compras a Productores {anio}"))

        if any(w in msg for w in ["productor", "registrad", "cuántos", "cuantos"]):
            try:
                by_state = execute_demo_query(
                    "SELECT estado, tipo_producto, COUNT(*) as cantidad "
                    "FROM demo_productores WHERE activo = true "
                    "GROUP BY estado, tipo_producto ORDER BY cantidad DESC"
                )
                sections.append("## Productores Registrados por Estado")
                sections.append(self._format_table(by_state))

                total = execute_demo_query(
                    "SELECT tipo_producto, COUNT(*) as total "
                    "FROM demo_productores WHERE activo = true GROUP BY tipo_producto"
                )
                sections.append("## Total por Tipo de Producto")
                sections.append(self._format_table(total))
            except Exception:
                pass

        if any(w in msg for w in ["pago", "pendiente", "deuda", "deb"]):
            try:
                data = execute_demo_query(
                    "SELECT p.nombre as productor, p.estado as ubicacion, "
                    "c.producto, c.peso_neto_kg, c.monto_total, c.fecha "
                    "FROM demo_compras_productores c "
                    "JOIN demo_productores p ON c.productor_id = p.id "
                    "WHERE c.estado_pago = 'pendiente' ORDER BY c.monto_total DESC"
                )
                total_pendiente = sum(d["monto_total"] for d in data)
                sections.append(
                    f"## Pagos Pendientes ({len(data)} guías - Total: Bs. {total_pendiente:,.2f})"
                )
                sections.append(self._format_table(data))
            except Exception:
                pass

        if any(w in msg for w in ["precio", "costo", "valor"]):
            try:
                data = execute_demo_query(
                    "SELECT producto, "
                    "MIN(precio_kg) as precio_min, AVG(precio_kg) as precio_promedio, "
                    "MAX(precio_kg) as precio_max, COUNT(*) as compras "
                    "FROM demo_compras_productores "
                    "WHERE EXTRACT(YEAR FROM fecha) = :anio GROUP BY producto",
                    {"anio": anio},
                )
                sections.append(f"## Análisis de Precios {anio} (Bs./kg)")
                sections.append(self._format_table(data))
            except Exception:
                pass

        return "\n\n".join(sections) if sections else None
