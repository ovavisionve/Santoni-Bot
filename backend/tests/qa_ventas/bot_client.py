"""
Cliente HTTP del bot para el runner de QA.

Tres responsabilidades:
  1. login(): devuelve un JWT token para el admin.
  2. ask(): envía una pregunta al agente y retorna la respuesta en texto.
  3. extract_numbers(): extrae todos los números (montos, conteos) del texto
     de la respuesta para poder compararlos con el SQL de verificación.

Los montos en la respuesta del bot suelen venir formateados al estilo
venezolano (1.234.567,89) o inglés (1,234,567.89). `extract_numbers` normaliza
ambos a float.
"""

import re
from typing import Any

import requests


class BotClient:
    """Cliente simple para el API de SantoniBot."""

    def __init__(self, base_url: str, username: str, password: str, timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._token: str | None = None

    def login(self) -> str:
        """Autentica y guarda el JWT token."""
        resp = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def ask(self, question: str, agent_name: str = "ventas") -> dict[str, Any]:
        """Envía una pregunta al agente. Retorna el dict con la respuesta completa.

        Claves relevantes del dict retornado:
          - message: texto de la respuesta
          - agent_used: qué agente respondió
          - confidence_score (opcional)
          - metadata (opcional)
        """
        if self._token is None:
            self.login()

        resp = requests.post(
            f"{self.base_url}/api/chat/",
            json={"message": question, "agent_name": agent_name},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


# Regex que captura montos con separadores:
#   - 1.234.567,89 (venezolano)
#   - 1,234,567.89 (inglés)
#   - 1234567.89 (sin separador)
#   - 1234567 (entero)
_NUMBER_RE = re.compile(
    r"[-+]?(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
)


def _normalize_number(s: str) -> float | None:
    """Normaliza un número formateado a float.

    Heurística para distinguir venezolano vs inglés:
      - Si tiene ambos `.` y `,`: el último separador es el decimal.
      - Si solo tiene uno: si aparece >1 vez, es separador de miles.
    """
    s = s.strip()
    if not s:
        return None

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        if s.rindex(",") > s.rindex("."):
            cleaned = s.replace(".", "").replace(",", ".")
        else:
            cleaned = s.replace(",", "")
    elif has_comma:
        if s.count(",") > 1:
            cleaned = s.replace(",", "")
        else:
            parts = s.split(",")
            if len(parts[-1]) == 3 and len(parts[0]) <= 3:
                cleaned = s.replace(",", "")
            else:
                cleaned = s.replace(",", ".")
    elif has_dot:
        if s.count(".") > 1:
            cleaned = s.replace(".", "")
        else:
            parts = s.split(".")
            if len(parts[-1]) == 3 and len(parts[0]) <= 3:
                cleaned = s.replace(".", "")
            else:
                cleaned = s
    else:
        cleaned = s

    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_numbers(text: str) -> list[float]:
    """Extrae todos los números del texto (montos + conteos) como floats.

    Útil para después chequear si los totales del SQL aparecen en la respuesta.
    Se ignoran números muy chicos (< 1) salvo que sean enteros, para no
    capturar cosas como "2.5%" de porcentajes.
    """
    numbers: list[float] = []
    for match in _NUMBER_RE.finditer(text):
        val = _normalize_number(match.group())
        if val is None:
            continue
        numbers.append(val)
    return numbers
