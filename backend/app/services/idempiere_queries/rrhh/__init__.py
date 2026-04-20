"""RRHH query package (split from rrhh.py, Abr 2026).

Re-exports all build_* functions so `from app.services.idempiere_queries.rrhh
import ...` keeps working unchanged.
"""

from .analytics import build_turnover_summary, build_vacation_summary
from .employees import (
    build_birthday_list,
    build_employee_list,
    build_employee_summary,
)
from .payroll import build_attendance_summary, build_payroll_summary

__all__ = [
    "build_attendance_summary",
    "build_birthday_list",
    "build_employee_list",
    "build_employee_summary",
    "build_payroll_summary",
    "build_turnover_summary",
    "build_vacation_summary",
]
