"""Current-date/time context string for the LLM (Venezuela timezone, Spanish)."""

from datetime import datetime


_DIAS_SEMANA = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}
_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _build_datetime_context() -> str:
    """Build a context string with the current date/time for the LLM."""
    now = datetime.now()
    dia = _DIAS_SEMANA[now.weekday()]
    mes = _MESES_ES[now.month]
    return (
        f"FECHA Y HORA ACTUAL DEL SISTEMA:\n"
        f"- Hoy es: {dia} {now.day} de {mes} de {now.year}\n"
        f"- Hora: {now.strftime('%H:%M')} (Venezuela)\n"
        f"- Mes actual: {mes} {now.year}\n"
        f"- Año actual: {now.year}\n"
        f"\nCuando el usuario diga 'actual', 'hoy', 'este mes', 'del mes', 'este año' "
        f"se refiere a: {mes} {now.year}.\n"
        f"NUNCA respondas con datos de otra fecha a menos que el usuario lo pida explícitamente.\n"
    )
