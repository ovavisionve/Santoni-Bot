"""
Export service for generating PDF, Excel, and CSV files from chat responses.
"""

import csv
import io
import re
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def _extract_tables_from_markdown(text: str) -> list[dict]:
    """Extract tables from markdown text. Returns list of {title, headers, rows}."""
    tables = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Check for markdown table
        if line.startswith("|") and i + 1 < len(lines):
            # Look for title above
            title = ""
            if i > 0:
                prev = lines[i - 1].strip()
                if prev.startswith("#"):
                    title = prev.lstrip("#").strip()

            # Parse header
            headers = [c.strip() for c in line.split("|")[1:-1]]

            # Skip separator
            if i + 1 < len(lines) and "---" in lines[i + 1]:
                i += 2
            else:
                i += 1

            # Parse rows
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
                rows.append(cells)
                i += 1

            if headers and rows:
                tables.append({"title": title, "headers": headers, "rows": rows})
            continue

        i += 1

    return tables


def export_to_csv(content: str, agent_used: str | None = None) -> bytes:
    """Export chat response content to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    tables = _extract_tables_from_markdown(content)

    if tables:
        for table in tables:
            if table["title"]:
                writer.writerow([table["title"]])
                writer.writerow([])
            writer.writerow(table["headers"])
            for row in table["rows"]:
                writer.writerow(row)
            writer.writerow([])
    else:
        # Just write the text content
        writer.writerow(["SantoniBot - Exportación"])
        writer.writerow([f"Agente: {agent_used or 'General'}"])
        writer.writerow([f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
        writer.writerow([])
        for line in content.split("\n"):
            clean = line.strip().lstrip("#").strip()
            if clean:
                writer.writerow([clean])

    return output.getvalue().encode("utf-8-sig")


def export_to_excel(content: str, agent_used: str | None = None) -> bytes:
    """Export chat response content to Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "SantoniBot"

    # Styles
    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="E06400", end_color="E06400", fill_type="solid")
    title_font = Font(name="Calibri", bold=True, size=14, color="E06400")
    subtitle_font = Font(name="Calibri", bold=True, size=11)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Header
    ws.merge_cells("A1:F1")
    ws["A1"] = "SantoniBot - Reporte"
    ws["A1"].font = title_font

    ws["A2"] = f"Agente: {agent_used or 'General'}"
    ws["A2"].font = subtitle_font
    ws["A3"] = f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    current_row = 5
    tables = _extract_tables_from_markdown(content)

    if tables:
        for table in tables:
            if table["title"]:
                ws.cell(row=current_row, column=1, value=table["title"]).font = subtitle_font
                current_row += 1

            # Headers
            for col, header in enumerate(table["headers"], 1):
                cell = ws.cell(row=current_row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
                cell.border = thin_border

            current_row += 1

            # Rows
            for row in table["rows"]:
                for col, value in enumerate(row, 1):
                    cell = ws.cell(row=current_row, column=col, value=value)
                    cell.border = thin_border
                    # Try to convert numeric values
                    try:
                        num = float(value.replace(",", "").replace("Bs.", "").strip())
                        cell.value = num
                        cell.number_format = "#,##0.00"
                    except (ValueError, AttributeError):
                        pass
                current_row += 1

            current_row += 1

        # Auto-width columns
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_length + 2, 40)
    else:
        # Text content
        for line in content.split("\n"):
            clean = line.strip().lstrip("#").strip()
            if clean:
                ws.cell(row=current_row, column=1, value=clean)
                current_row += 1

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def export_to_pdf(content: str, agent_used: str | None = None) -> bytes:
    """Export chat response content to PDF."""
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SantoniTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#E06400"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SantoniSubtitle",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#E06400"),
        spaceAfter=6,
    )
    normal_style = ParagraphStyle(
        "SantoniNormal",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
    )

    elements = []

    # Header
    elements.append(Paragraph("SantoniBot - Reporte", title_style))
    elements.append(
        Paragraph(
            f"Agente: {agent_used or 'General'} | "
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            normal_style,
        )
    )
    elements.append(Spacer(1, 12))

    tables = _extract_tables_from_markdown(content)

    if tables:
        for table in tables:
            if table["title"]:
                elements.append(Paragraph(table["title"], subtitle_style))

            # Build table data
            table_data = [table["headers"]] + table["rows"]

            # Create table with style
            t = Table(table_data, repeatRows=1)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E06400")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF5EB")]),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            elements.append(t)
            elements.append(Spacer(1, 12))
    else:
        # Plain text
        for line in content.split("\n"):
            clean = line.strip()
            if clean.startswith("##"):
                elements.append(Paragraph(clean.lstrip("#").strip(), subtitle_style))
            elif clean:
                elements.append(Paragraph(clean, normal_style))

    doc.build(elements)
    return output.getvalue()
