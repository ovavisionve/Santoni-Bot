#!/usr/bin/env python3
"""
Explorar TODAS las tablas de producción/manufactura en iDempiere.
Ejecutar: docker compose exec backend python scripts/explore_idempiere_production.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text

DB_URL = os.getenv(
    "IDEMPIERE_DB_URL",
    "postgresql://adempiere:adempiere@192.168.1.73:5432/idempiere_produccion"
)

engine = create_engine(DB_URL)

# Tablas de interés para producción/manufactura en iDempiere
PRODUCTION_TABLES = [
    # Manufacturing (módulo Libero)
    "pp_order",              # Órdenes de manufactura
    "pp_order_bomline",      # BOM lines de la orden
    "pp_order_workflow",     # Workflow de la orden
    "pp_order_node",         # Nodos del workflow
    "pp_order_node_asset",   # Activos en nodos
    "pp_order_cost",         # Costos de la orden
    "pp_product_bom",        # Bill of Materials (definición)
    "pp_product_bomline",    # Líneas del BOM
    "pp_product_planning",   # Planning de producto
    "pp_mrp",                # Material Requirements Planning
    "pp_forecast",           # Forecast de demanda
    "pp_forecastline",       # Líneas del forecast
    # Production clásico (no Libero)
    "m_production",          # Producción clásica
    "m_productionline",      # Líneas de producción clásica
    "m_productionplan",      # Plan de producción
    "m_productionbatch",     # Lotes de producción
    # Movimientos de inventario (lo que usa actualmente el bot)
    "m_inout",               # Movimientos de material
    "m_inoutline",           # Líneas de movimiento
    "m_movement",            # Movimientos internos
    "m_movementline",        # Líneas de movimiento interno
    "m_inventory",           # Inventario físico
    "m_inventoryline",       # Líneas de inventario físico
    # Inventario/almacén
    "m_storageonhand",       # Stock actual
    "m_warehouse",           # Almacenes
    "m_locator",             # Ubicaciones
    # Quality (si existe)
    "qm_specification",      # Especificaciones de calidad
    "qm_specificationline",  # Líneas de especificación
    # Otros relevantes
    "m_costdetail",          # Detalle de costos
    "m_cost",                # Costos de producto
    "c_projectline",         # Líneas de proyecto (a veces usado para producción)
]

def main():
    with engine.connect() as conn:
        print("=" * 80)
        print("EXPLORACIÓN DE TABLAS DE PRODUCCIÓN EN iDEMPIERE")
        print("=" * 80)

        # 1. Verificar qué tablas existen
        print("\n\n### 1. TABLAS QUE EXISTEN ###\n")
        existing = []
        for table in PRODUCTION_TABLES:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'adempiere' AND table_name = :t
                )
            """), {"t": table})
            exists = result.scalar()
            if exists:
                # Contar registros
                count = conn.execute(text(f"SELECT COUNT(*) FROM adempiere.{table}")).scalar()
                print(f"  ✅ {table:30s} → {count:>10,} registros")
                if count > 0:
                    existing.append((table, count))
            else:
                print(f"  ❌ {table:30s} → NO EXISTE")

        # 2. Para cada tabla con datos, mostrar columnas y sample
        print("\n\n### 2. ESTRUCTURA Y DATOS DE TABLAS CON REGISTROS ###\n")
        for table, count in existing:
            print(f"\n{'=' * 70}")
            print(f"TABLA: adempiere.{table}  ({count:,} registros)")
            print(f"{'=' * 70}")

            # Columnas
            cols = conn.execute(text("""
                SELECT column_name, data_type, is_nullable,
                       character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'adempiere' AND table_name = :t
                ORDER BY ordinal_position
            """), {"t": table}).fetchall()

            print(f"\nColumnas ({len(cols)}):")
            for c in cols:
                tipo = c[1]
                if c[3]:
                    tipo += f"({c[3]})"
                null = "NULL" if c[2] == "YES" else "NOT NULL"
                print(f"  {c[0]:40s} {tipo:25s} {null}")

            # Sample de 5 registros
            print(f"\nMuestra (5 registros):")
            try:
                rows = conn.execute(text(
                    f"SELECT * FROM adempiere.{table} LIMIT 5"
                )).fetchall()
                col_names = [c[0] for c in cols]
                for i, row in enumerate(rows):
                    print(f"\n  --- Registro {i+1} ---")
                    for j, val in enumerate(row):
                        if j < len(col_names):
                            # Truncar valores largos
                            str_val = str(val)
                            if len(str_val) > 100:
                                str_val = str_val[:100] + "..."
                            print(f"    {col_names[j]:35s} = {str_val}")
            except Exception as e:
                print(f"  Error leyendo muestra: {e}")

        # 3. Análisis específico de m_inout (movementtype)
        print("\n\n### 3. ANÁLISIS DE MOVEMENT TYPES EN m_inout ###\n")
        try:
            rows = conn.execute(text("""
                SELECT movementtype, COUNT(*) as cnt,
                       MIN(movementdate) as primera, MAX(movementdate) as ultima
                FROM adempiere.m_inout
                WHERE isactive = 'Y' AND docstatus IN ('CO','CL')
                GROUP BY movementtype
                ORDER BY cnt DESC
            """)).fetchall()
            print(f"  {'Tipo':<10} {'Cantidad':>12} {'Primera fecha':>15} {'Última fecha':>15}")
            print(f"  {'-'*10} {'-'*12} {'-'*15} {'-'*15}")
            for r in rows:
                print(f"  {r[0]:<10} {r[1]:>12,} {str(r[2]):>15} {str(r[3]):>15}")
        except Exception as e:
            print(f"  Error: {e}")

        # 4. Si pp_order tiene datos, analizar estados
        print("\n\n### 4. ANÁLISIS DE pp_order (SI TIENE DATOS) ###\n")
        try:
            rows = conn.execute(text("""
                SELECT docstatus, COUNT(*) as cnt
                FROM adempiere.pp_order
                GROUP BY docstatus
                ORDER BY cnt DESC
            """)).fetchall()
            if rows:
                for r in rows:
                    print(f"  docstatus={r[0]}: {r[1]:,} órdenes")
            else:
                print("  (tabla vacía)")
        except Exception as e:
            print(f"  Tabla no existe o error: {e}")

        # 5. Si m_production tiene datos, analizar
        print("\n\n### 5. ANÁLISIS DE m_production (SI TIENE DATOS) ###\n")
        try:
            rows = conn.execute(text("""
                SELECT docstatus, COUNT(*) as cnt,
                       MIN(movementdate) as primera, MAX(movementdate) as ultima
                FROM adempiere.m_production
                GROUP BY docstatus
                ORDER BY cnt DESC
            """)).fetchall()
            if rows:
                for r in rows:
                    print(f"  docstatus={r[0]}: {r[1]:,} producciones ({r[2]} a {r[3]})")
            else:
                print("  (tabla vacía)")
        except Exception as e:
            print(f"  Tabla no existe o error: {e}")

        # 6. m_movement (movimientos internos entre almacenes)
        print("\n\n### 6. ANÁLISIS DE m_movement (MOVIMIENTOS INTERNOS) ###\n")
        try:
            rows = conn.execute(text("""
                SELECT docstatus, COUNT(*) as cnt,
                       MIN(movementdate) as primera, MAX(movementdate) as ultima
                FROM adempiere.m_movement
                GROUP BY docstatus
                ORDER BY cnt DESC
            """)).fetchall()
            if rows:
                for r in rows:
                    print(f"  docstatus={r[0]}: {r[1]:,} movimientos ({r[2]} a {r[3]})")
            else:
                print("  (tabla vacía)")
        except Exception as e:
            print(f"  Tabla no existe o error: {e}")

        # 7. m_inventory (inventarios físicos)
        print("\n\n### 7. ANÁLISIS DE m_inventory (INVENTARIOS FÍSICOS) ###\n")
        try:
            rows = conn.execute(text("""
                SELECT docstatus, COUNT(*) as cnt,
                       MIN(movementdate) as primera, MAX(movementdate) as ultima
                FROM adempiere.m_inventory
                GROUP BY docstatus
                ORDER BY cnt DESC
            """)).fetchall()
            if rows:
                for r in rows:
                    print(f"  docstatus={r[0]}: {r[1]:,} inventarios ({r[2]} a {r[3]})")
            else:
                print("  (tabla vacía)")
        except Exception as e:
            print(f"  Tabla no existe o error: {e}")

        # 8. BOM (Bill of Materials) - estructura de productos
        print("\n\n### 8. BILL OF MATERIALS (pp_product_bom / pp_product_bomline) ###\n")
        try:
            bom_count = conn.execute(text(
                "SELECT COUNT(*) FROM adempiere.pp_product_bom"
            )).scalar()
            if bom_count > 0:
                print(f"  pp_product_bom: {bom_count:,} BOMs definidos")
                rows = conn.execute(text("""
                    SELECT b.name, p.name as producto, b.isactive,
                           (SELECT COUNT(*) FROM adempiere.pp_product_bomline bl
                            WHERE bl.pp_product_bom_id = b.pp_product_bom_id) as lineas
                    FROM adempiere.pp_product_bom b
                    JOIN adempiere.m_product p ON b.m_product_id = p.m_product_id
                    LIMIT 10
                """)).fetchall()
                print(f"\n  Muestra de BOMs:")
                for r in rows:
                    print(f"    BOM: {r[0]} | Producto: {r[1]} | Activo: {r[2]} | Líneas: {r[3]}")
            else:
                print("  (sin BOMs definidos)")
        except Exception as e:
            print(f"  Error o tabla no existe: {e}")

        # 9. Resumen de almacenes y stock
        print("\n\n### 9. ALMACENES Y STOCK ACTUAL ###\n")
        try:
            rows = conn.execute(text("""
                SELECT w.name as almacen, o.name as organizacion,
                       COUNT(DISTINCT s.m_product_id) as productos,
                       SUM(s.qtyonhand) as stock_total
                FROM adempiere.m_storageonhand s
                JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id
                JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id
                JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id
                WHERE s.isactive = 'Y' AND s.qtyonhand <> 0
                GROUP BY w.name, o.name
                ORDER BY stock_total DESC
            """)).fetchall()
            print(f"  {'Almacén':<35} {'Organización':<25} {'Productos':>10} {'Stock Total':>15}")
            print(f"  {'-'*35} {'-'*25} {'-'*10} {'-'*15}")
            for r in rows:
                print(f"  {r[0]:<35} {r[1]:<25} {r[2]:>10,} {r[3]:>15,.2f}")
        except Exception as e:
            print(f"  Error: {e}")

        print("\n\n" + "=" * 80)
        print("FIN DE LA EXPLORACIÓN")
        print("=" * 80)


if __name__ == "__main__":
    main()
