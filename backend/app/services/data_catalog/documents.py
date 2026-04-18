"""Generation of catalog documents for ChromaDB indexing."""

from datetime import datetime

from .constants import DEPARTMENT_TABLES


def build_catalog_documents(
    schema: dict,
    profiles: dict,
    samples: dict,
    relationships: list,
    dept_stats: dict,
) -> dict[str, list[str]]:
    """Genera documentos de texto estructurado por departamento,
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
