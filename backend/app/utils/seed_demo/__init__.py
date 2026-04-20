"""Demo data seeding — split by domain.

Populates realistic Venezuelan business data for development and testing across
all 7 departments of Alimentos Santoni, C.A.
"""

from app.database import SessionLocal
from app.models.demo_data import DemoCliente

from .compras_insumos import seed_compras_insumos
from .compras_productores import seed_compras_productores
from .contabilidad import seed_contabilidad
from .finanzas import seed_finanzas
from .produccion import seed_produccion
from .rrhh import seed_rrhh
from .ventas import seed_ventas


def seed_demo_data():
    """Populate all demo tables with realistic Venezuelan business data."""
    db = SessionLocal()
    try:
        existing = db.query(DemoCliente).count()
        if existing > 0:
            print(f"[SantoniBot] Demo data already exists ({existing} clients). Skipping seed.")
            return

        ventas_counts = seed_ventas(db)
        finanzas_counts = seed_finanzas(db)
        contab_counts = seed_contabilidad(db)
        rrhh_counts = seed_rrhh(db)
        prod_counts = seed_produccion(db)
        ci_counts = seed_compras_insumos(db)
        cp_counts = seed_compras_productores(db)

        db.commit()

        print(
            f"[SantoniBot] Demo data seeded: "
            f"{ventas_counts['clientes']} clients, "
            f"{ventas_counts['facturas']} invoices, "
            f"{ventas_counts['lineas_factura']} invoice lines, "
            f"{ventas_counts['cobranzas']} collections, "
            f"{ventas_counts['metas']} sales targets, "
            f"{finanzas_counts['cuentas']} bank accounts, "
            f"{finanzas_counts['movimientos']} bank movements, "
            f"{finanzas_counts['cuentas_pagar']} payables, "
            f"{contab_counts['asientos']} journal entries, "
            f"{contab_counts['balance_records']} balance records, "
            f"{rrhh_counts['empleados']} employees, "
            f"{rrhh_counts['nominas']} payroll records, "
            f"{rrhh_counts['asistencias']} attendance records, "
            f"{prod_counts['prod_diaria']} production records, "
            f"{prod_counts['ordenes_prod']} production orders, "
            f"{ci_counts['proveedores_insumos']} supply vendors, "
            f"{ci_counts['ordenes_compra']} supply purchase orders, "
            f"{cp_counts['productores']} producers, "
            f"{cp_counts['compras_prod']} producer purchases"
        )

    except Exception as e:
        db.rollback()
        print(f"[SantoniBot] Error seeding demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
