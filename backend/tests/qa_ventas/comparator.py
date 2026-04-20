"""
Comparador de valores esperados (SQL) vs valores del bot.

Dada una lista de valores esperados y una lista de números extraídos de la
respuesta del bot, verifica que cada esperado aparezca con tolerancia.

Tipos de match:
  - exact: el número tiene que coincidir exactamente (para conteos enteros).
  - amount: tolerancia relativa (default 0.5%) — el bot puede redondear.
  - contains_name: busca un substring en el texto crudo (para nombres de
    clientes/zonas que no son numéricos).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    """Resultado de un chequeo individual dentro de un test case."""
    label: str
    expected: Any
    passed: bool
    closest_found: Any | None = None
    note: str = ""


@dataclass
class CompareReport:
    """Agrega todos los chequeos de un test case."""
    test_name: str
    checks: list[CheckResult] = field(default_factory=list)
    bot_response: str = ""

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def pass_rate(self) -> float:
        if not self.checks:
            return 0.0
        return sum(1 for c in self.checks if c.passed) / len(self.checks)


def _find_closest(target: float, candidates: list[float], rel_tol: float) -> float | None:
    """Busca el candidato más cercano a target dentro de la tolerancia relativa.

    Retorna el candidato si matchea, None si ninguno está dentro de la tolerancia.
    Para target=0, usa tolerancia absoluta de 0.01.
    """
    if not candidates:
        return None

    if target == 0:
        for c in candidates:
            if abs(c) < 0.01:
                return c
        return None

    abs_tol = abs(target) * rel_tol
    best: float | None = None
    best_diff = float("inf")
    for c in candidates:
        diff = abs(c - target)
        if diff <= abs_tol and diff < best_diff:
            best = c
            best_diff = diff
    return best


def check_amount(
    label: str,
    expected: float,
    bot_numbers: list[float],
    rel_tol: float = 0.005,
) -> CheckResult:
    """Chequea que un monto esperado aparezca en los números del bot
    con tolerancia relativa (default 0.5%)."""
    match = _find_closest(expected, bot_numbers, rel_tol)
    if match is not None:
        return CheckResult(
            label=label,
            expected=expected,
            passed=True,
            closest_found=match,
            note=f"tolerancia {rel_tol*100:.2f}%",
        )

    # Fallback: mostrar el número más cercano aunque no matchee
    if bot_numbers:
        closest = min(bot_numbers, key=lambda x: abs(x - expected))
        diff_pct = abs(closest - expected) / abs(expected) * 100 if expected else 100
        return CheckResult(
            label=label,
            expected=expected,
            passed=False,
            closest_found=closest,
            note=f"más cercano difiere {diff_pct:.2f}%",
        )

    return CheckResult(
        label=label,
        expected=expected,
        passed=False,
        closest_found=None,
        note="el bot no mencionó números",
    )


def check_count(label: str, expected: int, bot_numbers: list[float]) -> CheckResult:
    """Chequea que un conteo entero aparezca exacto en los números del bot."""
    for n in bot_numbers:
        if int(n) == expected and abs(n - expected) < 0.01:
            return CheckResult(
                label=label,
                expected=expected,
                passed=True,
                closest_found=expected,
                note="match exacto",
            )
    if bot_numbers:
        closest = min(bot_numbers, key=lambda x: abs(x - expected))
        return CheckResult(
            label=label,
            expected=expected,
            passed=False,
            closest_found=closest,
            note=f"no encontrado (más cercano: {closest})",
        )
    return CheckResult(
        label=label,
        expected=expected,
        passed=False,
        closest_found=None,
        note="sin números en la respuesta",
    )


def check_name_present(
    label: str,
    expected_name: str,
    bot_text: str,
    case_sensitive: bool = False,
) -> CheckResult:
    """Chequea que un nombre (cliente/zona/etc) aparezca en el texto del bot."""
    haystack = bot_text if case_sensitive else bot_text.lower()
    needle = expected_name if case_sensitive else expected_name.lower()
    if needle in haystack:
        return CheckResult(
            label=label,
            expected=expected_name,
            passed=True,
            closest_found=expected_name,
            note="presente en la respuesta",
        )
    return CheckResult(
        label=label,
        expected=expected_name,
        passed=False,
        closest_found=None,
        note="no aparece en el texto del bot",
    )
