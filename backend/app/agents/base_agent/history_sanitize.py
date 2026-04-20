"""Cleanup helpers for prior LLM responses before re-injecting into history."""

import re
from collections import Counter


def clean_corrupted_response(text: str) -> str:
    """Detect and clean corrupted LLM responses (e.g. repeated text loops).

    Some LLM responses degenerate into repeating the same phrase/sentence.
    This pollutes conversation history and causes follow-up hallucinations.
    """
    if not text or len(text) < 200:
        return text

    sentences = re.split(r'[.!?\n]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if len(sentences) >= 4:
        counts = Counter(sentences)
        most_common_count = counts.most_common(1)[0][1] if counts else 0
        if most_common_count >= 3:
            truncated = text[:200].rsplit(' ', 1)[0]
            return (
                f"{truncated}...\n\n"
                "(Nota: la respuesta anterior se cortó por ser repetitiva. "
                "Los datos fueron consultados correctamente.)"
            )

    return text


def strip_tables_from_history(text: str) -> str:
    """Remove markdown tables from previous responses to prevent data recycling.

    When follow-up queries ask for different months/filters, the LLM tends to
    copy employee names, IDs, and amounts from previous response tables,
    generating hallucinated data. Stripping tables forces the LLM to use only
    fresh query results.
    """
    if not text:
        return text

    lines = text.split('\n')
    cleaned_lines: list[str] = []
    in_table = False
    table_replaced = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and '|' in stripped[1:]:
            if not in_table:
                in_table = True
                table_replaced = False
            if not table_replaced:
                cleaned_lines.append(
                    "*(Se consultaron datos reales — ver respuesta original)*"
                )
                table_replaced = True
            continue
        else:
            if in_table:
                in_table = False
            cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result
