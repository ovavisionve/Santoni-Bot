"""Sales-specific helpers: zone mapping, currency label, salesrep dedup."""

from .common import logger


# Mapping of sales zones (c_salesregion) to macro regions for Venezuela
# This groups individual states/zones into broader commercial regions
_ZONE_TO_REGION = {
    "portuguesa": "Llanos",
    "barinas": "Llanos",
    "guanare": "Llanos",
    "cojedes": "Llanos",
    "apure": "Llanos",
    "lara": "Centro-Occidente",
    "yaracuy": "Centro-Occidente",
    "falcon": "Centro-Occidente",
    "carabobo": "Centro",
    "aragua": "Centro",
    "valencia": "Centro",
    "caracas": "Capital",
    "miranda": "Capital",
    "vargas": "Capital",
    "la guaira": "Capital",
    "zulia": "Occidente",
    "maracaibo": "Occidente",
    "cabimas": "Occidente",
    "trujillo": "Andes",
    "merida": "Andes",
    "mérida": "Andes",
    "tachira": "Andes",
    "táchira": "Andes",
    "san cristobal": "Andes",
    "san cristóbal": "Andes",
    "santa barbara": "Occidente",
    "margarita": "Oriente",
    "oriente": "Oriente",
    "anzoategui": "Oriente",
    "anzoátegui": "Oriente",
    "sucre": "Oriente",
    "monagas": "Oriente",
    "bolivar": "Guayana",
    "bolívar": "Guayana",
    "delta amacuro": "Guayana",
    "amazonas": "Guayana",
}


def _region_case_sql() -> str:
    """Build a SQL CASE expression that maps zone names to macro regions."""
    cases = []
    # Group by region to reduce SQL size
    region_zones: dict[str, list[str]] = {}
    for zone, region in _ZONE_TO_REGION.items():
        region_zones.setdefault(region, []).append(zone)

    for region, zones in region_zones.items():
        like_conds = " OR ".join(f"LOWER(cz.zona_name) LIKE '%{z}%'" for z in zones)
        cases.append(f"WHEN ({like_conds}) THEN '{region}'")

    return f"CASE {' '.join(cases)} ELSE 'Otra' END"


def _currency_label(alias: str = "i") -> str:
    """SQL CASE expression that groups Santoni's multiple USD currency entries
    into a single 'USD' label and VES into 'Bs.' for display."""
    return (
        f"CASE WHEN {alias}.c_currency_id = 205 THEN 'Bs.' "
        f"WHEN {alias}.c_currency_id IN "
        f"(100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) "
        f"THEN 'USD' ELSE 'Otro' END"
    )


def _add_salesrep_filter(conditions: list, params: dict, salesrep_id: int | None, alias: str = "i"):
    """Add salesrep_id filter to conditions if provided."""
    if salesrep_id:
        conditions.append(f"{alias}.salesrep_id = :salesrep_id")
        params["salesrep_id"] = salesrep_id


def _dedupe_salesrep_rows(
    rows: list[dict],
    numeric_keys: list[str],
    name_key: str = "vendedor",
    sort_key: str | None = None,
) -> list[dict]:
    """Merge salesrep rows whose names are the same person written differently.

    iDempiere tiene ad_user duplicados con el mismo nombre en diferente orden
    (ej: "ROJAS OBANDO RENEE DE JESUS" vs "RENEE DE JESUS ROJAS OBANDO"). Al
    agrupar por sr.name aparecen como dos filas distintas. Esta función las
    consolida usando como clave el conjunto ordenado de tokens del nombre.

    Args:
        rows: filas ya formateadas como dict (salida del SELECT).
        numeric_keys: nombres de columnas numéricas a sumar al fusionar.
        name_key: columna con el nombre del vendedor (default "vendedor").
        sort_key: columna para reordenar el resultado (default: primera
            numeric_key, descendente).

    Returns:
        Nueva lista con las filas fusionadas.
    """
    if not rows:
        return rows

    def _norm(name: str) -> str:
        if not name or name.strip().lower() in ("sin vendedor", ""):
            return (name or "").strip().upper()
        tokens = [t for t in name.upper().split() if t]
        return " ".join(sorted(tokens))

    merged: dict[str, dict] = {}
    for row in rows:
        key = _norm(row.get(name_key) or "")
        if key not in merged:
            # Copia superficial; preserva el nombre tal como vino de la DB
            merged[key] = {k: v for k, v in row.items()}
        else:
            existing = merged[key]
            for nk in numeric_keys:
                if nk in row and isinstance(row[nk], (int, float)):
                    existing[nk] = existing.get(nk, 0) + row[nk]

    result = list(merged.values())
    sk = sort_key or (numeric_keys[0] if numeric_keys else None)
    if sk:
        result.sort(key=lambda r: r.get(sk, 0) or 0, reverse=True)
    return result


