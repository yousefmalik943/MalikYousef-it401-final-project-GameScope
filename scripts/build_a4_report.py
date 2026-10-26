from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate

from build_a3_report import build_story


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Yousef_Malik_A4_Project_Report.pdf"


def add_page_number(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(0.36, 0.39, 0.45)
    canvas.drawString(0.7 * inch, 0.45 * inch, "GameScope | IT401 A4 | Yousef Malik")
    canvas.drawRightString(7.8 * inch, 0.45 * inch, str(document.page))
    canvas.restoreState()


if __name__ == "__main__":
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
        title="GameScope IT401 A4 Project Report",
        author="Yousef Malik",
    )
    document.build(build_story(), onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"Created {OUTPUT.name}")
