#!/usr/bin/env python3
"""Render worksheet JSON into a template-aligned PDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle


ROOT = Path(__file__).resolve().parents[1]
PAGE_WIDTH, PAGE_HEIGHT = A4
LINE = HexColor("#808080")
TEXT = HexColor("#2a2a2a")
MUTED = HexColor("#565656")
GREEN_A = HexColor("#e8efd7")
GREEN_B = HexColor("#d7eb8a")
POINT_GREEN = HexColor("#9fca8d")

TASK_ICON_MAP = {
    "matching": ROOT / "pictogramme" / "Verbinden-1.png",
    "sorting": ROOT / "pictogramme" / "Verbinden-2.png",
    "cut_and_paste": ROOT / "pictogramme" / "Verbinden-3.png",
    "short_answer": ROOT / "pictogramme" / "Lesen-1.png",
    "fill_in": ROOT / "pictogramme" / "Lesen-2.png",
    "tracing": ROOT / "pictogramme" / "Lesen-3.png",
    "open_task": ROOT / "pictogramme" / "Lesen-4.png",
    "circling": ROOT / "pictogramme" / "Betrachten-1.png",
    "drawing": ROOT / "pictogramme" / "Betrachten-2.png",
    "multiple_choice": ROOT / "pictogramme" / "Betrachten-1.png",
}

FONT_CANDIDATES = [
    ROOT / "templates" / "OpenSan.ttf",
    ROOT / "templates" / "OpenSan-Regular.ttf",
    ROOT / "assets" / "fonts" / "OpenSan.ttf",
    ROOT / "assets" / "fonts" / "OpenSan-Regular.ttf",
]


def register_open_san() -> str:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            try:
                pdfmetrics.registerFont(TTFont("OpenSan", str(candidate)))
                return "OpenSan"
            except Exception:
                continue
    return "Helvetica"


def render_pdf(worksheet_set: dict[str, Any], output_path: Path, template_variant: str = "instructions") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font = register_open_san()
    pdf = canvas.Canvas(str(output_path), pagesize=A4)

    for index, level in enumerate(worksheet_set["levels"], start=1):
        draw_page(pdf, worksheet_set, level, template_variant, index, font)
        pdf.showPage()

    pdf.save()
    return output_path


def draw_page(
    pdf: canvas.Canvas,
    worksheet_set: dict[str, Any],
    level: dict[str, Any],
    template_variant: str,
    page_number: int,
    font: str,
) -> None:
    show_footer_zone = template_variant == "instructions"

    pdf.setStrokeColor(LINE)
    pdf.setFillColor(white)
    pdf.setLineWidth(0.9)

    left = 8.5 * mm
    right = PAGE_WIDTH - 8.5 * mm
    top = PAGE_HEIGHT - 8.5 * mm

    top_row_y = top - 16 * mm
    meta_row_y = top_row_y - 12 * mm
    frame_top = meta_row_y - 2 * mm
    frame_bottom = 10.5 * mm

    subject_w = 56 * mm
    gap = 2.2 * mm

    round_box(pdf, left, top_row_y, subject_w, 16 * mm)
    round_box(pdf, left + subject_w + gap, top_row_y, right - left - subject_w - gap, 16 * mm)
    round_box(pdf, left, meta_row_y, subject_w, 10 * mm)
    round_box(pdf, left + subject_w + gap, meta_row_y, right - left - subject_w - gap, 10 * mm)

    round_box(pdf, left, frame_bottom, right - left, frame_top - frame_bottom)
    pill_x = left + 4 * mm
    pill_y = frame_top - 15 * mm
    pill_w = right - left - 8 * mm
    round_box(pdf, pill_x, pill_y, pill_w, 10 * mm)

    draw_text(pdf, "Fachbereich", left + 2.4 * mm, top_row_y + 7.2 * mm, font, 13, TEXT)
    draw_text(pdf, "Datum:", left + 3 * mm, meta_row_y + 3.5 * mm, font, 11, TEXT)
    draw_text(pdf, "Name:", left + subject_w + gap + 3 * mm, meta_row_y + 3.5 * mm, font, 11, TEXT)
    draw_text(pdf, "Arbeitsanweisung", pill_x + 1.2 * mm, pill_y + 3.2 * mm, font, 15, TEXT)

    draw_paragraph(
        pdf,
        worksheet_set["target_group"],
        left + 3 * mm,
        top_row_y + 0.8 * mm,
        subject_w - 6 * mm,
        10 * mm,
        style(font, 8.5, 10, TEXT, align=1),
    )
    draw_paragraph(
        pdf,
        level["level_label"],
        left + subject_w + gap + 4 * mm,
        top_row_y + 12 * mm,
        45 * mm,
        3 * mm,
        style(font, 8.5, 9.5, MUTED),
    )
    draw_paragraph(
        pdf,
        worksheet_set["topic"],
        left + subject_w + gap + 4 * mm,
        top_row_y + 9.8 * mm,
        right - left - subject_w - gap - 8 * mm,
        8 * mm,
        style(font, 18, 20, TEXT),
    )
    draw_paragraph(
        pdf,
        level["student_title"],
        left + subject_w + gap + 4 * mm,
        top_row_y + 3.6 * mm,
        right - left - subject_w - gap - 8 * mm,
        4 * mm,
        style(font, 8.8, 10.2, MUTED),
    )

    if show_footer_zone:
        draw_instruction_rows(pdf, level, left, right, pill_y - 11 * mm, font)
        workspace_top = pill_y - 66 * mm
        footer_top = frame_bottom + 30 * mm
        draw_bottom_zone(pdf, left + 4 * mm, right - 4 * mm, frame_bottom + 4 * mm, font)
    else:
        workspace_top = pill_y - 5 * mm
        footer_top = frame_bottom + 4 * mm

    workspace_left = left + 4 * mm
    workspace_right = right - 4 * mm
    sidebar_w = 42 * mm
    gap_w = 4 * mm
    main_w = workspace_right - workspace_left - sidebar_w - gap_w
    workspace_h = workspace_top - footer_top

    main_x = workspace_left
    main_y = footer_top
    side_x = workspace_left + main_w + gap_w

    draw_paragraph(
        pdf,
        level["student_instruction"],
        main_x,
        workspace_top - 7 * mm,
        main_w,
        8 * mm,
        style(font, 11, 13, TEXT),
    )
    draw_paragraph(
        pdf,
        worksheet_set["general_teacher_note"],
        main_x,
        workspace_top - 16 * mm,
        main_w,
        8 * mm,
        style(font, 9.5, 11.5, MUTED),
    )
    draw_paragraph(
        pdf,
        level["difficulty_description"],
        main_x,
        workspace_top - 24 * mm,
        main_w,
        8 * mm,
        style(font, 9.5, 11.5, MUTED),
    )

    task_y = workspace_top - 34 * mm
    for number, task in enumerate(level["tasks"], start=1):
        card_h = draw_task_card(pdf, task, number, main_x, task_y, main_w, font)
        task_y -= card_h + 3 * mm
        if task_y < footer_top + 8 * mm:
            break

    sidebar_y = workspace_top - 5 * mm
    sidebar_y = draw_info_box(pdf, "Unterstuetzung", level["support_material"], side_x, sidebar_y, sidebar_w, font)
    image_items = [level["image_brief"] or "Bildbeschreibung fehlt."] if level["image_needed"] else ["Kein zusaetzliches Bild noetig."]
    sidebar_y = draw_info_box(pdf, "Bild", image_items, side_x, sidebar_y - 3 * mm, sidebar_w, font)
    draw_info_box(pdf, "Loesung", level["solution_notes"], side_x, sidebar_y - 3 * mm, sidebar_w, font)

    draw_text(pdf, "Fußzeile mit Erklärung / Version / Ersteller", left, 6 * mm, font, 9, TEXT)
    draw_text(pdf, f"Seite {page_number}", right - 22 * mm, 6 * mm, font, 9, TEXT)


def draw_instruction_rows(pdf: canvas.Canvas, level: dict[str, Any], left: float, right: float, top_y: float, font: str) -> None:
    rows = [level["student_instruction"]]
    rows.extend(task["prompt"] for task in level["tasks"][:2])
    rows.append("Arbeite ruhig und Schritt für Schritt.")
    rows.append("Kontrolliere deine Lösung am Ende.")
    rows = rows[:4]
    icons = [
        ROOT / "pictogramme" / "Lesen-1.png",
        ROOT / "pictogramme" / "Lesen-2.png",
        ROOT / "pictogramme" / "Betrachten-1.png",
        ROOT / "pictogramme" / "Verbinden-1.png",
    ]

    box_x = left + 4 * mm
    icon_w = 15 * mm
    box_w = right - left - 8 * mm
    row_h = 12 * mm
    step = 17 * mm

    for index, text in enumerate(rows):
        y = top_y - index * step
        round_box(pdf, box_x, y, box_w, row_h, radius=2 * mm)
        round_box(pdf, box_x, y, icon_w, row_h, radius=2 * mm)
        if index < 3:
            pdf.saveState()
            pdf.setFillColor(GREEN_A)
            pdf.rect(box_x + icon_w, y, box_w - icon_w, row_h, stroke=0, fill=1)
            pdf.setFillColor(GREEN_B)
            pdf.rect(box_x + icon_w + (box_w - icon_w) * 0.72, y, (box_w - icon_w) * 0.28, row_h, stroke=0, fill=1)
            pdf.restoreState()
            round_box(pdf, box_x, y, box_w, row_h, radius=2 * mm)
            round_box(pdf, box_x, y, icon_w, row_h, radius=2 * mm)
        icon_path = icons[index]
        if icon_path.exists():
            pdf.drawImage(str(icon_path), box_x + 1 * mm, y + 1 * mm, width=13 * mm, height=10 * mm, preserveAspectRatio=True, mask="auto")
        draw_paragraph(pdf, text, box_x + icon_w + 2 * mm, y + 1.7 * mm, box_w - icon_w - 4 * mm, 8 * mm, style(font, 11, 13, TEXT))


def draw_bottom_zone(pdf: canvas.Canvas, left: float, right: float, bottom: float, font: str) -> None:
    top = bottom + 27 * mm
    pdf.line(left, top, right, top)

    points_w = 40 * mm
    memo_x = left + points_w + 6 * mm
    round_box(pdf, left, bottom + 2 * mm, points_w, 21 * mm, radius=2 * mm)
    round_box(pdf, memo_x, bottom + 2 * mm, right - memo_x, 21 * mm, radius=2 * mm)

    pdf.saveState()
    pdf.setFillColor(POINT_GREEN)
    path = pdf.beginPath()
    path.moveTo(left, bottom + 2 * mm)
    path.lineTo(left + points_w * 0.58, bottom + 23 * mm)
    path.lineTo(left, bottom + 23 * mm)
    path.close()
    pdf.drawPath(path, fill=1, stroke=0)
    pdf.restoreState()

    draw_text(pdf, "Punkte:", left + 1 * mm, bottom + 18 * mm, font, 8, TEXT)
    draw_text(pdf, "von", left + 1 * mm, bottom + 13 * mm, font, 8, TEXT)
    draw_text(pdf, "Das muss ich üben!", left + 24 * mm, bottom + 17 * mm, font, 7, TEXT)
    draw_text(pdf, "Das kann ich manchmal!", left + 24 * mm, bottom + 10.5 * mm, font, 7, TEXT)
    draw_text(pdf, "Das kann ich gut!", left + 24 * mm, bottom + 4 * mm, font, 7, TEXT)
    draw_text(pdf, "Memo:", memo_x + 2 * mm, bottom + 18 * mm, font, 14, TEXT)


def draw_task_card(pdf: canvas.Canvas, task: dict[str, Any], number: int, x: float, top_y: float, width: float, font: str) -> float:
    card_h = 23 * mm
    y = top_y - card_h
    round_box(pdf, x, y, width, card_h, radius=2 * mm)
    draw_text(pdf, str(number), x + 5 * mm, top_y - 7.2 * mm, font, 11, TEXT)
    icon_path = TASK_ICON_MAP.get(task["task_type"])
    if icon_path and icon_path.exists():
        pdf.drawImage(str(icon_path), x + 14 * mm, top_y - 10 * mm, width=8 * mm, height=8 * mm, preserveAspectRatio=True, mask="auto")
    draw_text(pdf, task["task_type"].replace("_", " "), x + 25 * mm, top_y - 7.2 * mm, font, 9, MUTED)
    draw_paragraph(pdf, task["prompt"], x + 4 * mm, top_y - 15.5 * mm, width - 8 * mm, 8 * mm, style(font, 10.2, 12.2, TEXT))
    draw_paragraph(
        pdf,
        f"<b>Erwartete Antwort:</b> {task['expected_answer_format']}",
        x + 4 * mm,
        top_y - 21 * mm,
        width - 8 * mm,
        6 * mm,
        style(font, 8.8, 10.2, MUTED),
    )
    return card_h


def draw_info_box(pdf: canvas.Canvas, title: str, items: list[str], x: float, top_y: float, width: float, font: str) -> float:
    body_lines = max(1, sum(max(1, len(item) // 18) for item in items))
    height = max(20 * mm, (10 + body_lines * 4.4) * mm / 3.2)
    y = top_y - height
    pdf.rect(x, y, width, height, stroke=1, fill=0)
    draw_text(pdf, title, x + 3 * mm, top_y - 6 * mm, font, 11, TEXT)
    current_top = top_y - 12 * mm
    for item in items:
        draw_paragraph(pdf, f"• {item}", x + 3 * mm, current_top, width - 6 * mm, 12 * mm, style(font, 9.2, 11.2, TEXT))
        current_top -= 9 * mm
    return y


def round_box(pdf: canvas.Canvas, x: float, y: float, w: float, h: float, radius: float = 1.7 * mm) -> None:
    pdf.roundRect(x, y, w, h, radius, stroke=1, fill=0)


def draw_text(pdf: canvas.Canvas, text: str, x: float, y: float, font: str, size: float, color) -> None:
    pdf.setFont(font, size)
    pdf.setFillColor(color)
    pdf.drawString(x, y, text)


def style(font: str, size: float, leading: float, color, align: int = 0) -> ParagraphStyle:
    return ParagraphStyle(
        "temp",
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=align,
    )


def draw_paragraph(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    top_y: float,
    width: float,
    height: float,
    paragraph_style: ParagraphStyle,
) -> None:
    para = Paragraph(text, paragraph_style)
    wrapped_width, wrapped_height = para.wrap(width, height)
    para.drawOn(pdf, x, top_y - wrapped_height)
