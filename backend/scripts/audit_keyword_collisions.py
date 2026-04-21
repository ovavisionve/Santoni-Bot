#!/usr/bin/env python3
"""Detecta colisiones de substring en keywords.

Busca keywords que son substring de nombres de organizaciones,
productos comunes, o cargos — lo que causaría falsos positivos.

Uso: python scripts/audit_keyword_collisions.py
"""
from app.agents.keywords import (
    ORGANIZACIONES, RRHH_CARGOS, PRODUCTOS_ARROZ, PRODUCTOS_MAIZ,
    PRODUCTOS_INSUMOS, VENTAS_CLIENTES, VENTAS_COBRANZA, VENTAS_CXC,
    VENTAS_FACTURACION, VENTAS_ZONAS, COMPRAS_GENERAL,
)

# Names that keywords should NOT accidentally match inside
ORG_NAMES = [
    "inpromaiz", "inproa santoni", "santoni service",
    "agropecuaria r.r.", "agroinproa", "inversiones aga", "agro import",
]

PRODUCT_NAMES = [
    "arroz paddy acondicionado", "maiz blanco de consumo",
    "harina de maiz blanco", "harina precocida",
]

print("=== Substring collisions: keywords que matchean dentro de org names ===\n")
all_sets = {
    "VENTAS_CLIENTES": VENTAS_CLIENTES,
    "VENTAS_COBRANZA": VENTAS_COBRANZA,
    "VENTAS_FACTURACION": VENTAS_FACTURACION,
    "VENTAS_ZONAS": VENTAS_ZONAS,
    "COMPRAS_GENERAL": COMPRAS_GENERAL,
}

collisions = 0
for set_name, kw_set in all_sets.items():
    for kw in sorted(kw_set):
        if len(kw) < 3:
            continue
        for org in ORG_NAMES:
            if kw in org and kw != org:
                print(f"  ⚠️  '{kw}' (in {set_name}) matchea dentro de '{org}'")
                collisions += 1

if collisions == 0:
    print("  ✅ Sin colisiones detectadas")
else:
    print(f"\n  Total: {collisions} colisiones potenciales")

print("\n=== Keywords muy cortos (< 3 chars) que pueden causar falsos positivos ===\n")
for set_name, kw_set in all_sets.items():
    short = [kw for kw in kw_set if len(kw) < 3]
    if short:
        print(f"  ⚠️  {set_name}: {short}")
