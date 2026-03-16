"""Validar que build_producer_purchases ahora incluye compras de maíz externas.

Ejecuta las funciones reales del agente (no SQL directo) para validar el fix.

Uso: docker compose exec backend python scripts/validate_producer_fix.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.idempiere_queries import (
    build_producer_purchases,
    build_producer_price_analysis,
)


def pp(label, data):
    print(f"\n{'=' * 80}")
    print(label)
    print('=' * 80)
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                print(f"\n  {k} ({len(v)} items):")
                for item in v[:10]:
                    print(f"    {item}")
            elif isinstance(v, dict):
                print(f"\n  {k}:")
                for kk, vv in v.items():
                    print(f"    {kk}: {vv}")
            else:
                print(f"  {k}: {v}")
    elif isinstance(data, list):
        for item in data[:15]:
            print(f"  {item}")
    else:
        print(f"  {data}")


def main():
    print("VALIDACIÓN POST-FIX: Compras a Productores")
    print("Esperado: MAIZ BLANCO DE CONSUMO aparece con guías y montos")
    print("Esperado: Precio arroz ~100+ Bs/kg (no 2.85)")

    # 1. Compras de maíz 2026
    result = build_producer_purchases(producto="maiz", anio=2026)
    pp("1. build_producer_purchases(producto='maiz', anio=2026)", result)

    # 2. Compras de arroz 2026
    result = build_producer_purchases(producto="arroz paddy", anio=2026)
    pp("2. build_producer_purchases(producto='arroz paddy', anio=2026)", result)

    # 3. Todas las compras 2026 (sin filtro de producto)
    result = build_producer_purchases(anio=2026)
    pp("3. build_producer_purchases(anio=2026) - SIN filtro producto", result)

    # 4. Precios 2026
    prices = build_producer_price_analysis(anio=2026)
    pp("4. build_producer_price_analysis(anio=2026)", prices)

    # 5. Compras de maíz en InproMaiz (el caso que antes daba 0)
    result = build_producer_purchases(producto="maiz", anio=2026, org_name="InproMaiz")
    pp("5. build_producer_purchases(producto='maiz', org_name='InproMaiz')", result)


if __name__ == "__main__":
    main()
