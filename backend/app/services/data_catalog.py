"""
Data Catalog Service - Extrae metadata real de iDempiere y la indexa en ChromaDB.

Este servicio descubre dinámicamente el schema de iDempiere, perfila los datos
(valores distintos, rangos, conteos) y alimenta ChromaDB para que los agentes
tengan conocimiento real de la estructura y contenido de la base de datos.

Se ejecuta automáticamente cada 5 minutos via catalog_sync.py.
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.database import IdempiereSession

logger = logging.getLogger("santonibot.data_catalog")

# ──────────────────────────────────────────────────────────────────
# Tablas relevantes por departamento (schema adempiere)
# Estas son las tablas que los agentes realmente consultan.
# ──────────────────────────────────────────────────────────────────

DEPARTMENT_TABLES: dict[str, list[str]] = {
    "ventas": [
        "c_invoice",
        "c_invoiceline",
        "c_payment",
        "c_bpartner",
        "c_bpartner_location",
        "c_salesregion",
        "c_doctype",
        "m_product",
        "m_product_category",
        "c_currency",
    ],
    "finanzas": [
        "c_bankaccount",
        "c_bankstatement",
        "c_bankstatementline",
        "c_payment",
        "c_invoice",
        "c_bpartner",
        "c_currency",
    ],
    "contabilidad": [
        "gl_journal",
        "gl_journalline",
        "c_elementvalue",
        "c_acctschema",
        "c_period",
        "fact_acct",
        "c_allocationline",
    ],
    "rrhh": [
        "hr_employee",
        "hr_department",
        "hr_job",
        "hr_process",
        "hr_movement",
        "hr_concept",
        "hr_payroll",
        "c_bpartner",
    ],
    "produccion": [
        "m_product",
        "m_production",
        "m_productionline",
        "m_storageonhand",
        "m_warehouse",
        "m_locator",
        "m_product_category",
    ],
    "compras_insumos": [
        "c_invoice",
        "c_invoiceline",
        "c_bpartner",
        "m_product",
        "m_product_category",
        "c_currency",
        "c_doctype",
    ],
    "compras_productores": [
        "c_invoice",
        "c_invoiceline",
        "c_bpartner",
        "m_product",
        "c_currency",
        "c_doctype",
    ],
}

# Columnas "interesantes" para profiling (valores distintos, rangos)
# Formato: tabla -> lista de columnas a perfilar
PROFILE_COLUMNS: dict[str, list[str]] = {
    "c_invoice": ["docstatus", "issotrx", "c_currency_id", "dateinvoiced"],
    "c_payment": ["docstatus", "isreceipt", "c_currency_id", "datetrx"],
    "c_bpartner": ["isvendor", "iscustomer", "isemployee", "isactive"],
    "c_salesregion": ["name", "isactive"],
    "c_doctype": ["name", "docbasetype", "isactive"],
    "m_product": ["producttype", "isactive", "issold", "ispurchased"],
    "m_product_category": ["name", "isactive"],
    "hr_employee": ["isactive", "startdate", "enddate"],
    "hr_department": ["name", "isactive"],
    "hr_job": ["name", "isactive"],
    "hr_payroll": ["name", "isactive"],
    "hr_concept": ["name", "isactive"],
    "c_currency": ["iso_code", "cursymbol", "isactive"],
    "c_elementvalue": ["accounttype", "issummary", "isactive"],
    "m_warehouse": ["name", "isactive"],
    "c_bankaccount": ["accountno", "isactive"],
}

# Columnas de fecha para determinar rangos temporales
DATE_COLUMNS: dict[str, str] = {
    "c_invoice": "dateinvoiced",
    "c_payment": "datetrx",
    "gl_journal": "datedoc",
    "hr_process": "dateacct",
    "hr_movement": "validfrom",
    "m_production": "movementdate",
    "c_bankstatement": "statementdate",
    "fact_acct": "dateacct",
}


class DataCatalogService:
    """Extrae y gestiona el catálogo de metadata de iDempiere."""

    def __init__(self):
        self._last_sync: datetime | None = None
        self._catalog: dict[str, Any] = {}
        self._sync_errors: list[str] = []

    @property
    def last_sync(self) -> datetime | None:
        return self._last_sync

    @property
    def catalog(self) -> dict[str, Any]:
        return self._catalog

    @property
    def sync_errors(self) -> list[str]:
        return self._sync_errors

    # ──────────────────────────────────────────────────────────────
    # Schema Discovery
    # ──────────────────────────────────────────────────────────────

    def _get_all_relevant_tables(self) -> set[str]:
        """Devuelve el set de todas las tablas relevantes sin duplicados."""
        tables: set[str] = set()
        for dept_tables in DEPARTMENT_TABLES.values():
            tables.update(dept_tables)
        return tables

    def _discover_schema(self, session) -> dict[str, dict]:
        """
        Descubre el schema de las tablas relevantes en iDempiere.
        Retorna: {table_name: {columns: [...], row_count: int, ...}}
        """
        tables = self._get_all_relevant_tables()
        schema: dict[str, dict] = {}

        for table_name in sorted(tables):
            try:
                # Obtener columnas
                col_query = text("""
                    SELECT column_name, data_type, is_nullable,
                           character_maximum_length, numeric_precision
                    FROM information_schema.columns
                    WHERE table_schema = 'adempiere'
                      AND table_name = :table_name
                    ORDER BY ordinal_position
                """)
                cols_result = session.execute(col_query, {"table_name": table_name})
                columns = []
                for row in cols_result:
                    columns.append({
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES",
                        "max_length": row[3],
                        "precision": row[4],
                    })

                if not columns:
                    logger.debug("Tabla '%s' no encontrada en schema adempiere", table_name)
                    continue

                # Contar registros (con timeout para tablas grandes)
                count_query = text(f"SELECT COUNT(*) FROM adempiere.{table_name}")
                count_result = session.execute(count_query)
                row_count = count_result.scalar() or 0

                schema[table_name] = {
                    "columns": columns,
                    "row_count": row_count,
                    "column_names": [c["name"] for c in columns],
                }

            except Exception as e:
                logger.warning("Error descubriendo schema de '%s': %s", table_name, e)
                self._sync_errors.append(f"schema_{table_name}: {e}")

        return schema

    # ──────────────────────────────────────────────────────────────
    # Foreign Keys / Relaciones
    # ──────────────────────────────────────────────────────────────

    def _discover_relationships(self, session) -> list[dict]:
        """Descubre foreign keys entre las tablas relevantes."""
        tables = self._get_all_relevant_tables()
        tables_list = ", ".join(f"'{t}'" for t in tables)

        try:
            fk_query = text(f"""
                SELECT
                    tc.table_name AS source_table,
                    kcu.column_name AS source_column,
                    ccu.table_name AS target_table,
                    ccu.column_name AS target_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'adempiere'
                  AND tc.table_name IN ({tables_list})
                  AND ccu.table_name IN ({tables_list})
                ORDER BY tc.table_name, kcu.column_name
            """)
            result = session.execute(fk_query)
            relationships = []
            for row in result:
                relationships.append({
                    "source_table": row[0],
                    "source_column": row[1],
                    "target_table": row[2],
                    "target_column": row[3],
                })
            return relationships

        except Exception as e:
            logger.warning("Error descubriendo relaciones: %s", e)
            self._sync_errors.append(f"relationships: {e}")
            return []

    # ──────────────────────────────────────────────────────────────
    # Data Profiling
    # ──────────────────────────────────────────────────────────────

    def _profile_column_values(self, session, table: str, column: str, limit: int = 50) -> list:
        """Obtiene valores distintos de una columna (hasta limit)."""
        try:
            query = text(f"""
                SELECT {column}, COUNT(*) as cnt
                FROM adempiere.{table}
                WHERE {column} IS NOT NULL
                GROUP BY {column}
                ORDER BY cnt DESC
                LIMIT :limit
            """)
            result = session.execute(query, {"limit": limit})
            return [{"value": str(row[0]), "count": row[1]} for row in result]
        except Exception as e:
            logger.debug("Error profiling %s.%s: %s", table, column, e)
            return []

    def _profile_date_range(self, session, table: str, date_column: str) -> dict | None:
        """Obtiene el rango de fechas de una columna."""
        try:
            query = text(f"""
                SELECT
                    MIN({date_column}) AS min_date,
                    MAX({date_column}) AS max_date,
                    COUNT(DISTINCT DATE_TRUNC('month', {date_column})) AS months_count
                FROM adempiere.{table}
                WHERE {date_column} IS NOT NULL
            """)
            result = session.execute(query)
            row = result.fetchone()
            if row and row[0]:
                return {
                    "min_date": str(row[0]),
                    "max_date": str(row[1]),
                    "months_with_data": row[2],
                }
        except Exception as e:
            logger.debug("Error profiling date range %s.%s: %s", table, date_column, e)
        return None

    def _profile_data(self, session, schema: dict[str, dict]) -> dict[str, dict]:
        """
        Perfila datos de las tablas: valores distintos, rangos de fechas, etc.
        """
        profiles: dict[str, dict] = {}

        for table_name, table_info in schema.items():
            table_profile: dict[str, Any] = {"columns": {}}

            # Profiling de columnas interesantes
            if table_name in PROFILE_COLUMNS:
                for col in PROFILE_COLUMNS[table_name]:
                    if col in table_info["column_names"]:
                        values = self._profile_column_values(session, table_name, col)
                        if values:
                            table_profile["columns"][col] = values

            # Profiling de rango de fechas
            if table_name in DATE_COLUMNS:
                date_col = DATE_COLUMNS[table_name]
                if date_col in table_info["column_names"]:
                    date_range = self._profile_date_range(session, table_name, date_col)
                    if date_range:
                        table_profile["date_range"] = date_range

            if table_profile["columns"] or "date_range" in table_profile:
                profiles[table_name] = table_profile

        return profiles

    # ──────────────────────────────────────────────────────────────
    # Muestreo de datos
    # ──────────────────────────────────────────────────────────────

    def _sample_data(self, session, schema: dict[str, dict], sample_size: int = 5) -> dict[str, list]:
        """Obtiene filas de ejemplo de cada tabla (las más recientes si hay fecha)."""
        samples: dict[str, list] = {}

        for table_name in schema:
            try:
                # Si la tabla tiene columna de fecha, ordenar por la más reciente
                order_clause = ""
                if table_name in DATE_COLUMNS:
                    date_col = DATE_COLUMNS[table_name]
                    if date_col in schema[table_name]["column_names"]:
                        order_clause = f"ORDER BY {date_col} DESC NULLS LAST"

                # Seleccionar solo columnas clave (primeras 10 para no saturar)
                col_names = schema[table_name]["column_names"][:10]
                cols_sql = ", ".join(col_names)

                query = text(
                    f"SELECT {cols_sql} FROM adempiere.{table_name} "
                    f"{order_clause} LIMIT :limit"
                )
                result = session.execute(query, {"limit": sample_size})
                rows = []
                for row in result:
                    row_dict = {}
                    for i, col in enumerate(col_names):
                        val = row[i]
                        # Convertir a string para serialización
                        if val is not None:
                            row_dict[col] = str(val)
                        else:
                            row_dict[col] = None
                    rows.append(row_dict)

                if rows:
                    samples[table_name] = rows

            except Exception as e:
                logger.debug("Error muestreando %s: %s", table_name, e)

        return samples

    # ──────────────────────────────────────────────────────────────
    # Estadísticas por departamento
    # ──────────────────────────────────────────────────────────────

    def _build_department_stats(self, session) -> dict[str, dict]:
        """Genera estadísticas específicas por departamento."""
        stats: dict[str, dict] = {}

        # ── Ventas ──
        try:
            r = session.execute(text("""
                SELECT
                    COUNT(*) AS total_facturas,
                    COUNT(DISTINCT c_bpartner_id) AS clientes_unicos,
                    MIN(dateinvoiced) AS primera_factura,
                    MAX(dateinvoiced) AS ultima_factura
                FROM adempiere.c_invoice
                WHERE issotrx = 'Y' AND docstatus = 'CO'
            """))
            row = r.fetchone()
            if row:
                stats["ventas"] = {
                    "total_facturas_venta": row[0],
                    "clientes_unicos": row[1],
                    "primera_factura": str(row[2]) if row[2] else None,
                    "ultima_factura": str(row[3]) if row[3] else None,
                }
        except Exception as e:
            logger.debug("Error stats ventas: %s", e)

        # ── Zonas de venta ──
        try:
            r = session.execute(text("""
                SELECT name, isactive
                FROM adempiere.c_salesregion
                WHERE isactive = 'Y'
                ORDER BY name
            """))
            zonas = [row[0] for row in r]
            stats.setdefault("ventas", {})["zonas_activas"] = zonas
        except Exception as e:
            logger.debug("Error stats zonas: %s", e)

        # ── Organizaciones activas ──
        try:
            r = session.execute(text("""
                SELECT ad_org_id, name
                FROM adempiere.ad_org
                WHERE isactive = 'Y' AND ad_org_id > 0
                ORDER BY name
            """))
            orgs = [{"id": row[0], "name": row[1]} for row in r]
            stats["organizaciones"] = orgs
        except Exception as e:
            logger.debug("Error stats organizaciones: %s", e)

        # ── Monedas ──
        try:
            r = session.execute(text("""
                SELECT c_currency_id, iso_code, cursymbol, description
                FROM adempiere.c_currency
                WHERE isactive = 'Y'
                  AND c_currency_id IN (
                      SELECT DISTINCT c_currency_id FROM adempiere.c_invoice
                      WHERE docstatus = 'CO' LIMIT 20
                  )
                ORDER BY iso_code
            """))
            monedas = [{"id": row[0], "iso_code": row[1], "symbol": row[2], "description": row[3]} for row in r]
            stats["monedas"] = monedas
        except Exception as e:
            logger.debug("Error stats monedas: %s", e)

        # ── RRHH ──
        try:
            r = session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE isactive = 'Y') AS activos,
                    COUNT(*) FILTER (WHERE isactive = 'N') AS inactivos,
                    COUNT(*) AS total
                FROM adempiere.hr_employee
            """))
            row = r.fetchone()
            if row:
                stats["rrhh"] = {
                    "empleados_activos": row[0],
                    "empleados_inactivos": row[1],
                    "total_empleados": row[2],
                }
        except Exception as e:
            logger.debug("Error stats rrhh: %s", e)

        # ── Departamentos HR ──
        try:
            r = session.execute(text("""
                SELECT name FROM adempiere.hr_department
                WHERE isactive = 'Y' ORDER BY name
            """))
            stats.setdefault("rrhh", {})["departamentos"] = [row[0] for row in r]
        except Exception as e:
            logger.debug("Error stats hr_department: %s", e)

        # ── Cargos HR ──
        try:
            r = session.execute(text("""
                SELECT name FROM adempiere.hr_job
                WHERE isactive = 'Y' ORDER BY name
            """))
            stats.setdefault("rrhh", {})["cargos"] = [row[0] for row in r]
        except Exception as e:
            logger.debug("Error stats hr_job: %s", e)

        # ── Productos más facturados ──
        try:
            r = session.execute(text("""
                SELECT p.name, COUNT(*) AS veces
                FROM adempiere.c_invoiceline il
                JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
                JOIN adempiere.c_invoice i ON il.c_invoice_id = i.c_invoice_id
                WHERE i.docstatus = 'CO' AND i.issotrx = 'Y'
                GROUP BY p.name
                ORDER BY veces DESC
                LIMIT 30
            """))
            stats["productos_top"] = [{"nombre": row[0], "frecuencia": row[1]} for row in r]
        except Exception as e:
            logger.debug("Error stats productos: %s", e)

        # ── Categorías de producto ──
        try:
            r = session.execute(text("""
                SELECT name FROM adempiere.m_product_category
                WHERE isactive = 'Y' ORDER BY name
            """))
            stats["categorias_producto"] = [row[0] for row in r]
        except Exception as e:
            logger.debug("Error stats categorias: %s", e)

        # ── Proveedores (compras) ──
        try:
            r = session.execute(text("""
                SELECT COUNT(DISTINCT bp.c_bpartner_id) AS total_proveedores
                FROM adempiere.c_bpartner bp
                WHERE bp.isvendor = 'Y' AND bp.isactive = 'Y'
            """))
            row = r.fetchone()
            if row:
                stats["compras"] = {"total_proveedores_activos": row[0]}
        except Exception as e:
            logger.debug("Error stats proveedores: %s", e)

        # ── Almacenes ──
        try:
            r = session.execute(text("""
                SELECT m_warehouse_id, name
                FROM adempiere.m_warehouse
                WHERE isactive = 'Y'
                ORDER BY name
            """))
            stats["almacenes"] = [{"id": row[0], "name": row[1]} for row in r]
        except Exception as e:
            logger.debug("Error stats almacenes: %s", e)

        return stats

    # ──────────────────────────────────────────────────────────────
    # Generación de documentos para ChromaDB
    # ──────────────────────────────────────────────────────────────

    def _build_catalog_documents(
        self,
        schema: dict,
        profiles: dict,
        samples: dict,
        relationships: list,
        dept_stats: dict,
    ) -> dict[str, list[str]]:
        """
        Genera documentos de texto estructurado por departamento,
        listos para indexar en ChromaDB.
        """
        docs_by_dept: dict[str, list[str]] = {}

        for dept, tables in DEPARTMENT_TABLES.items():
            dept_docs: list[str] = []

            # Documento 1: Resumen del schema de tablas del departamento
            schema_parts = [f"CATÁLOGO DE DATOS - Departamento: {dept.upper()}"]
            schema_parts.append(f"Última sincronización: {datetime.now().isoformat()}")
            schema_parts.append("")

            for table in tables:
                if table not in schema:
                    continue
                info = schema[table]
                schema_parts.append(f"## Tabla: adempiere.{table}")
                schema_parts.append(f"- Registros: {info['row_count']:,}")
                schema_parts.append(f"- Columnas ({len(info['columns'])}):")
                for col in info["columns"]:
                    col_desc = f"  - {col['name']} ({col['type']}"
                    if col["max_length"]:
                        col_desc += f", max {col['max_length']}"
                    col_desc += ")"
                    schema_parts.append(col_desc)

                # Rango de fechas
                if table in profiles and "date_range" in profiles[table]:
                    dr = profiles[table]["date_range"]
                    schema_parts.append(
                        f"- Rango temporal: {dr['min_date']} a {dr['max_date']} "
                        f"({dr['months_with_data']} meses con datos)"
                    )

                schema_parts.append("")

            dept_docs.append("\n".join(schema_parts))

            # Documento 2: Valores distintos / profiling
            profile_parts = [f"PERFIL DE DATOS - Departamento: {dept.upper()}"]
            profile_parts.append("")
            has_profile = False

            for table in tables:
                if table not in profiles or not profiles[table].get("columns"):
                    continue
                has_profile = True
                profile_parts.append(f"## Valores en adempiere.{table}")
                for col, values in profiles[table]["columns"].items():
                    profile_parts.append(f"### {table}.{col}:")
                    for v in values[:20]:
                        profile_parts.append(f"  - {v['value']} ({v['count']:,} registros)")
                profile_parts.append("")

            if has_profile:
                dept_docs.append("\n".join(profile_parts))

            # Documento 3: Relaciones (foreign keys) relevantes
            dept_rels = [r for r in relationships
                         if r["source_table"] in tables or r["target_table"] in tables]
            if dept_rels:
                rel_parts = [f"RELACIONES DE TABLAS - Departamento: {dept.upper()}"]
                rel_parts.append("")
                for r in dept_rels:
                    rel_parts.append(
                        f"- {r['source_table']}.{r['source_column']} → "
                        f"{r['target_table']}.{r['target_column']}"
                    )
                dept_docs.append("\n".join(rel_parts))

            # Documento 4: Datos de ejemplo
            sample_parts = [f"DATOS DE EJEMPLO - Departamento: {dept.upper()}"]
            sample_parts.append("")
            has_samples = False

            for table in tables:
                if table not in samples:
                    continue
                has_samples = True
                sample_parts.append(f"## Ejemplo de adempiere.{table} (últimos registros):")
                for i, row in enumerate(samples[table], 1):
                    row_str = ", ".join(f"{k}={v}" for k, v in row.items() if v is not None)
                    sample_parts.append(f"  {i}. {row_str}")
                sample_parts.append("")

            if has_samples:
                dept_docs.append("\n".join(sample_parts))

            # Documento 5: Estadísticas del departamento
            if dept in dept_stats:
                stat_parts = [f"ESTADÍSTICAS OPERATIVAS - Departamento: {dept.upper()}"]
                stat_parts.append("")
                for key, val in dept_stats[dept].items():
                    if isinstance(val, list):
                        stat_parts.append(f"### {key}:")
                        for item in val:
                            if isinstance(item, dict):
                                stat_parts.append(f"  - {item}")
                            else:
                                stat_parts.append(f"  - {item}")
                    else:
                        stat_parts.append(f"- {key}: {val}")
                dept_docs.append("\n".join(stat_parts))

            # Documento compartido: organizaciones y monedas
            shared_parts = []
            if "organizaciones" in dept_stats:
                shared_parts.append("ORGANIZACIONES ACTIVAS EN iDEMPIERE:")
                for org in dept_stats["organizaciones"]:
                    shared_parts.append(f"  - ID {org['id']}: {org['name']}")
            if "monedas" in dept_stats:
                shared_parts.append("\nMONEDAS USADAS EN FACTURACIÓN:")
                for m in dept_stats["monedas"]:
                    shared_parts.append(
                        f"  - ID {m['id']}: {m['iso_code']} ({m['symbol']}) - {m['description']}"
                    )
            if "almacenes" in dept_stats:
                shared_parts.append("\nALMACENES:")
                for a in dept_stats["almacenes"]:
                    shared_parts.append(f"  - ID {a['id']}: {a['name']}")
            if "productos_top" in dept_stats and dept in ("ventas", "compras_insumos", "produccion"):
                shared_parts.append("\nPRODUCTOS MÁS FACTURADOS (top 30):")
                for p in dept_stats["productos_top"]:
                    shared_parts.append(f"  - {p['nombre']} ({p['frecuencia']:,} veces)")
            if "categorias_producto" in dept_stats and dept in ("ventas", "compras_insumos", "produccion"):
                shared_parts.append("\nCATEGORÍAS DE PRODUCTO:")
                for c in dept_stats["categorias_producto"]:
                    shared_parts.append(f"  - {c}")

            if shared_parts:
                dept_docs.append("\n".join(shared_parts))

            docs_by_dept[dept] = dept_docs

        return docs_by_dept

    # ──────────────────────────────────────────────────────────────
    # Sync principal
    # ──────────────────────────────────────────────────────────────

    def sync(self) -> dict:
        """
        Ejecuta la sincronización completa:
        1. Descubre schema
        2. Perfila datos
        3. Muestrea datos
        4. Descubre relaciones
        5. Genera estadísticas departamentales
        6. Indexa todo en ChromaDB

        Retorna un resumen del resultado.
        """
        self._sync_errors = []
        start_time = datetime.now()
        logger.info("Iniciando sincronización del catálogo de datos...")

        session = IdempiereSession()
        try:
            # 1. Schema discovery
            logger.info("Paso 1/5: Descubriendo schema...")
            schema = self._discover_schema(session)
            logger.info("  → %d tablas descubiertas", len(schema))

            # 2. Data profiling
            logger.info("Paso 2/5: Perfilando datos...")
            profiles = self._profile_data(session, schema)
            logger.info("  → %d tablas perfiladas", len(profiles))

            # 3. Sample data
            logger.info("Paso 3/5: Muestreando datos...")
            samples = self._sample_data(session, schema)
            logger.info("  → %d tablas muestreadas", len(samples))

            # 4. Relationships
            logger.info("Paso 4/5: Descubriendo relaciones...")
            relationships = self._discover_relationships(session)
            logger.info("  → %d relaciones encontradas", len(relationships))

            # 5. Department stats
            logger.info("Paso 5/5: Generando estadísticas departamentales...")
            dept_stats = self._build_department_stats(session)

        except Exception as e:
            logger.error("Error fatal durante sincronización: %s", e, exc_info=True)
            self._sync_errors.append(f"fatal: {e}")
            return {
                "ok": False,
                "error": str(e),
                "errors": self._sync_errors,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }
        finally:
            session.close()

        # 6. Generar documentos y subir a ChromaDB
        logger.info("Indexando en ChromaDB...")
        docs_by_dept = self._build_catalog_documents(
            schema, profiles, samples, relationships, dept_stats
        )
        index_result = self._index_to_chromadb(docs_by_dept)

        # Guardar catálogo en memoria para consultas rápidas
        self._catalog = {
            "schema": schema,
            "profiles": profiles,
            "relationships": relationships,
            "dept_stats": dept_stats,
            "tables_count": len(schema),
            "total_rows": sum(t.get("row_count", 0) for t in schema.values()),
        }
        self._last_sync = datetime.now()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            "Sincronización completada en %.1fs. %d tablas, %d documentos indexados.",
            duration, len(schema), index_result.get("total_docs", 0),
        )

        return {
            "ok": True,
            "duration_seconds": round(duration, 1),
            "tables_discovered": len(schema),
            "tables_profiled": len(profiles),
            "relationships_found": len(relationships),
            "documents_indexed": index_result.get("total_docs", 0),
            "departments_updated": index_result.get("departments_updated", []),
            "errors": self._sync_errors if self._sync_errors else None,
            "last_sync": self._last_sync.isoformat(),
        }

    def _index_to_chromadb(self, docs_by_dept: dict[str, list[str]]) -> dict:
        """Indexa los documentos generados en ChromaDB via RAGService."""
        try:
            from app.services.rag_service import get_rag_service
            rag = get_rag_service()
        except Exception as e:
            logger.warning("ChromaDB no disponible para indexación: %s", e)
            return {"total_docs": 0, "departments_updated": []}

        total_docs = 0
        departments_updated = []

        for dept, docs in docs_by_dept.items():
            # Limpiar colección de catálogo previa (usa colección separada)
            catalog_dept = f"catalog_{dept}"

            # Asegurar que el departamento de catálogo existe en DEPARTMENTS
            # Usamos la colección del departamento directamente con metadata de fuente
            for i, doc in enumerate(docs):
                result = rag.add_document(
                    department=dept,
                    text=doc,
                    metadata={
                        "source": "data_catalog",
                        "catalog_doc_index": str(i),
                        "sync_time": datetime.now().isoformat(),
                    },
                )
                if result.get("ok"):
                    total_docs += result.get("chunks_stored", 0)

            departments_updated.append(dept)

        return {
            "total_docs": total_docs,
            "departments_updated": departments_updated,
        }

    # ──────────────────────────────────────────────────────────────
    # Consulta del catálogo en memoria
    # ──────────────────────────────────────────────────────────────

    def get_table_info(self, table_name: str) -> dict | None:
        """Retorna información del schema de una tabla específica."""
        return self._catalog.get("schema", {}).get(table_name)

    def get_department_context(self, department: str) -> str | None:
        """
        Genera un contexto resumido del catálogo para un departamento.
        Útil para inyectar en el prompt del agente.
        """
        if not self._catalog or not self._last_sync:
            return None

        schema = self._catalog.get("schema", {})
        profiles = self._catalog.get("profiles", {})
        dept_stats = self._catalog.get("dept_stats", {})
        tables = DEPARTMENT_TABLES.get(department, [])

        if not tables:
            return None

        parts = [
            f"CATÁLOGO DE DATOS iDEMPIERE (sincronizado: {self._last_sync.strftime('%Y-%m-%d %H:%M')})",
            "",
        ]

        for table in tables:
            if table not in schema:
                continue
            info = schema[table]
            parts.append(f"• {table}: {info['row_count']:,} registros, "
                         f"{len(info['columns'])} columnas")

            # Rango de fechas si existe
            if table in profiles and "date_range" in profiles[table]:
                dr = profiles[table]["date_range"]
                parts.append(f"  Datos desde {dr['min_date']} hasta {dr['max_date']}")

        # Stats del departamento
        if department in dept_stats:
            parts.append("")
            parts.append(f"Estadísticas {department}:")
            for key, val in dept_stats[department].items():
                if isinstance(val, list) and len(val) > 10:
                    parts.append(f"  {key}: {len(val)} elementos")
                elif isinstance(val, list):
                    parts.append(f"  {key}: {', '.join(str(v) for v in val)}")
                else:
                    parts.append(f"  {key}: {val}")

        return "\n".join(parts)

    def get_status(self) -> dict:
        """Retorna el estado actual del catálogo."""
        return {
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "tables_count": self._catalog.get("tables_count", 0),
            "total_rows": self._catalog.get("total_rows", 0),
            "relationships_count": len(self._catalog.get("relationships", [])),
            "errors": self._sync_errors if self._sync_errors else None,
            "is_synced": self._last_sync is not None,
        }


# ──────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────

_catalog_service: DataCatalogService | None = None


def get_catalog_service() -> DataCatalogService:
    """Retorna la instancia singleton del servicio de catálogo."""
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = DataCatalogService()
    return _catalog_service
