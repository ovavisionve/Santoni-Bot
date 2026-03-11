"""
Seed de usuarios supervisores para Alimentos Santoni.

Crea 5 usuarios con rol supervisor, cada uno con un departamento
principal y acceso a TODOS los agentes via extra_departments.

Uso:
  docker compose exec backend python scripts/seed_users.py

Si un usuario (por email) ya existe, se omite sin error.
"""
import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.user import User, UserRole, Department
from app.services.auth import hash_password

ALL_DEPARTMENTS = ",".join([
    "finanzas", "contabilidad", "ventas", "rrhh",
    "produccion", "compras_insumos", "compras_productores",
])

PASSWORD = "Santoni2022$"

USERS = [
    {
        "email": "jalvarez.santoni@gmail.com",
        "username": "jalvarez",
        "full_name": "Johan Alvarez",
        "department": Department.CONTABILIDAD,
    },
    {
        "email": "ventas.inproasantoni@gmail.com",
        "username": "lsilva",
        "full_name": "Lenny Silva",
        "department": Department.VENTAS,
    },
    {
        "email": "gerenciacomprasantoni@gmail.com",
        "username": "jchahine",
        "full_name": "Jorge Chahine",
        "department": Department.COMPRAS_INSUMOS,
    },
    {
        "email": "productoresinproa@gmail.com",
        "username": "mfigueredo",
        "full_name": "Marlenis Figueredo",
        "department": Department.COMPRAS_PRODUCTORES,
    },
    {
        "email": "rrhh.inproasantoni@gmail.com",
        "username": "esalas",
        "full_name": "Emelin Salas",
        "department": Department.RRHH,
    },
]


def seed_users():
    db = SessionLocal()
    try:
        hashed = hash_password(PASSWORD)
        created = 0
        skipped = 0

        for u in USERS:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                print(f"  SKIP  {u['full_name']} ({u['email']}) - ya existe")
                skipped += 1
                continue

            # Verificar username duplicado
            existing_username = db.query(User).filter(User.username == u["username"]).first()
            if existing_username:
                print(f"  SKIP  {u['full_name']} (username {u['username']}) - ya existe")
                skipped += 1
                continue

            user = User(
                email=u["email"],
                username=u["username"],
                full_name=u["full_name"],
                hashed_password=hashed,
                role=UserRole.SUPERVISOR,
                department=u["department"],
                extra_departments=ALL_DEPARTMENTS,
                is_active=True,
            )
            db.add(user)
            print(f"  OK    {u['full_name']} ({u['email']}) - {u['department'].value} [supervisor]")
            created += 1

        db.commit()
        print(f"\nResultado: {created} creados, {skipped} omitidos")
    finally:
        db.close()


if __name__ == "__main__":
    print("=== Seed de usuarios supervisores Santoni ===\n")
    seed_users()
    print("\nListo. Clave para todos: Santoni2022$")
