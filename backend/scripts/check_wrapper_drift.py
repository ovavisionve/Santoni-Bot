#!/usr/bin/env python3
"""Detecta drift entre query_service wrappers e idempiere_queries.

Si alguien agrega un parámetro a idempiere_queries.build_X() sin
actualizar query_service.build_X(), este script lo detecta.

Uso: python scripts/check_wrapper_drift.py
"""
import ast, sys

def extract_funcs(path):
    tree = ast.parse(open(path).read())
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("build_"):
            params = [a.arg for a in node.args.args if a.arg != "self"]
            result[node.name] = set(params)
    return result

qs = extract_funcs("app/services/query_service.py")
iq = extract_funcs("app/services/idempiere_queries.py")

drift = 0
for name in sorted(qs.keys()):
    if name not in iq:
        continue
    missing = iq[name] - qs[name]
    if missing:
        drift += 1
        print(f"❌ {name}(): query_service FALTA {sorted(missing)}")

if drift == 0:
    print("✅ Sin drift — todos los wrappers están alineados")
else:
    print(f"\n⚠️  {drift} wrappers con drift")
    sys.exit(1)
