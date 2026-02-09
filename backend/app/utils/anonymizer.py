"""
Anonymizes sensitive data before sending to external AI APIs.
Replaces names, IDs, and other PII with generic codes.
"""

import re


def anonymize_for_llm(text: str, department: str) -> tuple[str, dict]:
    """
    Anonymize sensitive data in text before sending to LLM.
    Returns (anonymized_text, mapping) where mapping can be used to de-anonymize.
    """
    mapping = {}
    anonymized = text

    # Venezuelan cedula patterns (V-12345678 or similar)
    cedula_pattern = r'\b[VvEe]-?\d{6,8}\b'
    for i, match in enumerate(re.finditer(cedula_pattern, anonymized)):
        code = f"[CEDULA_{i+1}]"
        mapping[code] = match.group()
        anonymized = anonymized.replace(match.group(), code, 1)

    # Phone numbers (04XX-XXXXXXX or similar)
    phone_pattern = r'\b0\d{3}-?\d{7}\b'
    for i, match in enumerate(re.finditer(phone_pattern, anonymized)):
        code = f"[TELEFONO_{i+1}]"
        mapping[code] = match.group()
        anonymized = anonymized.replace(match.group(), code, 1)

    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for i, match in enumerate(re.finditer(email_pattern, anonymized)):
        code = f"[EMAIL_{i+1}]"
        mapping[code] = match.group()
        anonymized = anonymized.replace(match.group(), code, 1)

    return anonymized, mapping


def deanonymize_response(text: str, mapping: dict) -> str:
    """Restore anonymized data in LLM response."""
    result = text
    for code, original in mapping.items():
        result = result.replace(code, original)
    return result
