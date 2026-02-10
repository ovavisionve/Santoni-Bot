"""
Tests for the data anonymizer utility.

Verifies that sensitive data (cedulas, phone numbers, emails) is properly
anonymized before sending to LLMs, and can be restored afterwards.
"""

import pytest

from app.utils.anonymizer import anonymize_for_llm, deanonymize_response


# ---------------------------------------------------------------------------
# Cedula anonymization
# ---------------------------------------------------------------------------

class TestCedulaAnonymization:
    """Tests for Venezuelan cedula anonymization."""

    def test_cedula_v_format(self):
        """Standard V-12345678 cedula should be anonymized."""
        text = "El cliente con cedula V-12345678 compro 500 kg."
        anonymized, mapping = anonymize_for_llm(text, "ventas")

        assert "V-12345678" not in anonymized
        assert "[CEDULA_1]" in anonymized
        assert mapping["[CEDULA_1]"] == "V-12345678"

    def test_cedula_e_format(self):
        """E-type cedula for foreigners should be anonymized."""
        text = "Proveedor E-87654321 entrego la mercancia."
        anonymized, mapping = anonymize_for_llm(text, "compras_insumos")

        assert "E-87654321" not in anonymized
        assert "[CEDULA_1]" in anonymized
        assert mapping["[CEDULA_1]"] == "E-87654321"

    def test_cedula_lowercase_v(self):
        """Lowercase v-12345678 should also be anonymized."""
        text = "Cedula: v-9876543"
        anonymized, mapping = anonymize_for_llm(text, "rrhh")

        assert "v-9876543" not in anonymized
        assert "[CEDULA_1]" in anonymized

    def test_cedula_without_dash(self):
        """Cedula without dash (V12345678) should be anonymized."""
        text = "Usuario V12345678 inicio sesion."
        anonymized, mapping = anonymize_for_llm(text, "rrhh")

        assert "V12345678" not in anonymized
        assert "[CEDULA_1]" in anonymized

    def test_multiple_cedulas(self):
        """Multiple cedulas should each get unique codes."""
        text = "Empleados V-11111111 y V-22222222 estan presentes."
        anonymized, mapping = anonymize_for_llm(text, "rrhh")

        assert "V-11111111" not in anonymized
        assert "V-22222222" not in anonymized
        assert "[CEDULA_1]" in anonymized
        assert "[CEDULA_2]" in anonymized
        assert len(mapping) >= 2


# ---------------------------------------------------------------------------
# Phone number anonymization
# ---------------------------------------------------------------------------

class TestPhoneAnonymization:
    """Tests for Venezuelan phone number anonymization."""

    def test_phone_with_dash(self):
        """Phone number like 0414-1234567 should be anonymized."""
        text = "Contactar al 0414-1234567 para mas info."
        anonymized, mapping = anonymize_for_llm(text, "ventas")

        assert "0414-1234567" not in anonymized
        assert "[TELEFONO_1]" in anonymized
        assert mapping["[TELEFONO_1]"] == "0414-1234567"

    def test_phone_without_dash(self):
        """Phone number like 04141234567 should be anonymized."""
        text = "Numero: 04241234567"
        anonymized, mapping = anonymize_for_llm(text, "ventas")

        assert "04241234567" not in anonymized
        assert "[TELEFONO_1]" in anonymized

    def test_multiple_phones(self):
        """Multiple phone numbers should each get unique codes."""
        text = "Telefonos: 0412-1111111 y 0416-2222222"
        anonymized, mapping = anonymize_for_llm(text, "ventas")

        assert "0412-1111111" not in anonymized
        assert "0416-2222222" not in anonymized
        assert "[TELEFONO_1]" in anonymized
        assert "[TELEFONO_2]" in anonymized


# ---------------------------------------------------------------------------
# Email anonymization
# ---------------------------------------------------------------------------

class TestEmailAnonymization:
    """Tests for email address anonymization."""

    def test_simple_email(self):
        """Standard email should be anonymized."""
        text = "Enviar reporte a juan.perez@santoni.com por favor."
        anonymized, mapping = anonymize_for_llm(text, "ventas")

        assert "juan.perez@santoni.com" not in anonymized
        assert "[EMAIL_1]" in anonymized
        assert mapping["[EMAIL_1]"] == "juan.perez@santoni.com"

    def test_email_with_numbers(self):
        """Email with numbers should be anonymized."""
        text = "Usuario admin123@empresa.co.ve registrado."
        anonymized, mapping = anonymize_for_llm(text, "rrhh")

        assert "admin123@empresa.co.ve" not in anonymized
        assert "[EMAIL_1]" in anonymized

    def test_multiple_emails(self):
        """Multiple emails should each get unique codes."""
        text = "Correos: a@test.com y b@test.com"
        anonymized, mapping = anonymize_for_llm(text, "rrhh")

        assert "a@test.com" not in anonymized
        assert "b@test.com" not in anonymized
        assert "[EMAIL_1]" in anonymized
        assert "[EMAIL_2]" in anonymized


# ---------------------------------------------------------------------------
# Mixed PII anonymization
# ---------------------------------------------------------------------------

class TestMixedAnonymization:
    """Tests with text containing multiple types of PII."""

    def test_cedula_phone_and_email(self):
        """Text with cedula, phone, and email should anonymize all of them."""
        text = (
            "Empleado V-11111111, telefono 0414-5555555, "
            "email empleado@santoni.com solicita vacaciones."
        )
        anonymized, mapping = anonymize_for_llm(text, "rrhh")

        assert "V-11111111" not in anonymized
        assert "0414-5555555" not in anonymized
        assert "empleado@santoni.com" not in anonymized
        assert "[CEDULA_1]" in anonymized
        assert "[TELEFONO_1]" in anonymized
        assert "[EMAIL_1]" in anonymized

    def test_no_pii_text_unchanged(self):
        """Text without PII should remain unchanged."""
        text = "Las ventas del mes de enero fueron de 500,000 Bs."
        anonymized, mapping = anonymize_for_llm(text, "ventas")

        assert anonymized == text
        assert len(mapping) == 0


# ---------------------------------------------------------------------------
# Deanonymization
# ---------------------------------------------------------------------------

class TestDeanonymization:
    """Tests for restoring anonymized data."""

    def test_deanonymize_restores_original(self):
        """deanonymize_response should restore all anonymized values."""
        original = (
            "Empleado V-12345678, tel 0414-1234567, email test@test.com"
        )
        anonymized, mapping = anonymize_for_llm(original, "rrhh")

        # Simulate LLM response that uses the anonymized codes
        llm_response = (
            f"El empleado {list(mapping.keys())[0]} tiene el telefono "
            f"{list(mapping.keys())[1]} y correo {list(mapping.keys())[2]}."
        )

        restored = deanonymize_response(llm_response, mapping)

        assert "V-12345678" in restored
        assert "0414-1234567" in restored
        assert "test@test.com" in restored

    def test_deanonymize_empty_mapping(self):
        """Deanonymize with empty mapping should return text unchanged."""
        text = "No PII here."
        result = deanonymize_response(text, {})
        assert result == text

    def test_deanonymize_partial_codes_in_response(self):
        """If LLM only uses some codes, only those should be restored."""
        mapping = {
            "[CEDULA_1]": "V-12345678",
            "[EMAIL_1]": "test@test.com",
        }
        text = "El usuario [CEDULA_1] no tiene email registrado."
        result = deanonymize_response(text, mapping)

        assert "V-12345678" in result
        assert "[EMAIL_1]" not in result or "test@test.com" not in text

    def test_roundtrip_anonymize_deanonymize(self):
        """Full roundtrip: anonymize then deanonymize should restore original PII."""
        original = "Cliente V-55555555, cel 0412-9876543"
        anonymized, mapping = anonymize_for_llm(original, "ventas")

        # Deanonymize the anonymized text itself
        restored = deanonymize_response(anonymized, mapping)
        assert restored == original
