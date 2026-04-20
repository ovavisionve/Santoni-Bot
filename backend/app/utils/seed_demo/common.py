"""Shared helpers for demo data seeding."""

import random
from datetime import date, timedelta

random.seed(42)


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _rif_juridico() -> str:
    return f"J-{random.randint(10000000, 49999999)}-{random.randint(0, 9)}"


def _cedula() -> str:
    return f"V-{random.randint(5000000, 28000000)}"


def _telefono() -> str:
    prefixes = ["0414", "0424", "0412", "0416", "0426"]
    return f"{random.choice(prefixes)}-{random.randint(1000000, 9999999)}"
