import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
OUTPUT = ROOT / "Yousef_Malik_A3_Project_Report.pdf"


def inline_markup(text):
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)

    def link(match):
        label, target = match.groups()
        return f'<link href="{escape(target, quote=True)}" color="#246fdb">{label}</link>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)


def build_story():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER,
        textColor=colors.HexColor("#102a43"), spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="ReportH2", parent=styles["Heading2"], textColor=colors.HexColor("#102a43"),
        spaceBefore=14, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="ReportH3", parent=styles["Heading3"], textColor=colors.HexColor("#246fdb"),
        spaceBefore=10, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="ReportBody", parent=styles["BodyText"], leading=14, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="ReportCode", fontName="Courier", fontSize=8, leading=10,
        backColor=colors.HexColor("#f2f5f8"), borderPadding=7, spaceBefore=3, spaceAfter=9,
    ))

    lines = README.read_text(encoding="utf-8").splitlines()
    story = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("```"):
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            story.append(Preformatted("\n".join(code_lines), styles["ReportCode"]))
            index += 1
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    rows.append([Paragraph(inline_markup(cell), styles["BodyText"]) for cell in cells])
                index += 1
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f0f7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102a43")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5df")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 8)])
            continue
        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image_match:
            alt, image_path = image_match.groups()
            image_file = ROOT / image_path
            if image_file.exists():
                image = Image(str(image_file))
                image._restrictSize(6.5 * inch, 4.8 * inch)
                story.extend([Paragraph(inline_markup(alt), styles["Caption"]), image, Spacer(1, 10)])
            else:
                story.append(Paragraph(f"Screenshot pending: {inline_markup(alt)}", styles["Italic"]))
            index += 1
            continue
        heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            style = "ReportTitle" if level == 1 else "ReportH2" if level == 2 else "ReportH3"
            story.append(Paragraph(inline_markup(heading_match.group(2)), styles[style]))
            index += 1
            continue
        if line.startswith("- ") or re.match(r"\d+\.\s", line):
            ordered = line[:1].isdigit()
            items = []
            while index < len(lines) and (lines[index].startswith("- ") or re.match(r"\d+\.\s", lines[index])):
                item_text = re.sub(r"^(?:- |\d+\.\s)", "", lines[index])
                items.append(ListItem(Paragraph(inline_markup(item_text), styles["ReportBody"])))
                index += 1
            story.append(ListFlowable(items, bulletType="1" if ordered else "bullet", leftIndent=18))
            story.append(Spacer(1, 5))
            continue

        paragraph_lines = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].startswith(("#", "|", "```", "- ", "![")) and not re.match(r"\d+\.\s", lines[index]):
            paragraph_lines.append(lines[index])
            index += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), styles["ReportBody"]))
    return story


def add_page_number(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5b6472"))
    canvas.drawString(0.7 * inch, 0.45 * inch, "GameScope | IT401 A3 | Yousef Malik")
    canvas.drawRightString(7.8 * inch, 0.45 * inch, str(document.page))
    canvas.restoreState()


if __name__ == "__main__":
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, rightMargin=0.7 * inch,
        leftMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.7 * inch,
        title="GameScope IT401 A3 Project Report", author="Yousef Malik",
    )
    document.build(build_story(), onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"Created {OUTPUT.name}")