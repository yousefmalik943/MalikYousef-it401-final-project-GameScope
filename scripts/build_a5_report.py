from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
OUTPUT = ROOT / "Yousef_Malik_A5_Project_Report.pdf"


def build_story():
    styles = getSampleStyleSheet()
    lines = README.read_text(encoding="utf-8").splitlines()
    story = []
    story.append(Paragraph(
        "GameScope IT401 A5 Project Report",
        style=styles["Title"],
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Student: Yousef Malik", style=styles["BodyText"]))
    story.append(Paragraph(
        "Assignment: A5 — Expanding the Web Intelligence Application with Intelligence Generation",
        style=styles["BodyText"],
    ))
    story.append(Spacer(1, 0.25 * inch))
    rows = [["Section", "Coverage"]]
    for line in lines:
        if line.startswith("#") or line.startswith("##") or line.startswith("###"):
            rows.append([line.strip("# "), "Documented in README"])
    table = Table(rows, colWidths=[2.1 * inch, 4.6 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f0f7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102a43")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5df")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph(
        "The project README contains the full A5 implementation details including retrieval-augmented generation, prompt design, validation, persistence, and reliability handling.",
        style=styles["BodyText"],
    ))
    return story


if __name__ == "__main__":
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    document.build(build_story())
    print(f"Created {OUTPUT.name}")
