#!/usr/bin/env python3
"""Render worksheet JSON into a printable HTML preview."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "examples" / "output-example.json"
DEFAULT_OUTPUT = ROOT / "out" / "arbeitsblaetter-vorschau.html"
DEFAULT_SCHEMA = ROOT / "schemas" / "worksheet-set.schema.json"

EXPECTED_LEVELS = [
    ("very_easy", "sehr leicht"),
    ("medium", "mittel"),
    ("slightly_harder", "etwas schwerer"),
]

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

TEMPLATE_VARIANTS = {
    "blank": {
        "label": "AB-Vorlage-Blank.pdf",
        "instruction_hint": "",
        "show_memo": False,
    },
    "instructions": {
        "label": "AB-Vorlage-mit-Arbeitsanweisungen.pdf",
        "instruction_hint": (
            "Schreiben Sie die Loesungen in die Kaestchen. "
            "Schauen Sie sich den Unterschied an. "
            "Verbinden Sie die Stecker mit den richtigen Begriffen. "
            "Lesen und Lernen Sie die Inhalte des Arbeitsblattes."
        ),
        "show_memo": True,
    },
}


class ValidationError(Exception):
    """Raised when the worksheet JSON misses required content."""


@dataclass
class RenderConfig:
    template_variant: str
    output_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a worksheet JSON file into a printable HTML preview."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the worksheet-set JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the generated HTML file.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Path to the schema file. Currently used as a required reference.",
    )
    parser.add_argument(
        "--template",
        choices=sorted(TEMPLATE_VARIANTS),
        default="instructions",
        help="Visual template variant derived from the uploaded PDFs.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema_file(path: Path) -> None:
    if not path.exists():
        raise ValidationError(f"Schema file not found: {path}")


def validate_worksheet_set(data: dict[str, Any]) -> None:
    require_fields(
        data,
        [
            "topic",
            "learning_goal",
            "target_group",
            "general_teacher_note",
            "levels",
        ],
        "root",
    )

    if not isinstance(data["levels"], list) or len(data["levels"]) != 3:
        raise ValidationError("Expected exactly 3 levels in 'levels'.")

    seen_pairs = []
    for index, level in enumerate(data["levels"], start=1):
        require_fields(
            level,
            [
                "level_key",
                "level_label",
                "difficulty_description",
                "student_title",
                "student_instruction",
                "tasks",
                "support_material",
                "image_needed",
                "image_brief",
                "solution_notes",
            ],
            f"levels[{index}]",
        )
        seen_pairs.append((level["level_key"], level["level_label"]))
        if not isinstance(level["tasks"], list) or not level["tasks"]:
            raise ValidationError(f"levels[{index}].tasks must contain at least one item.")
        for task_index, task in enumerate(level["tasks"], start=1):
            require_fields(
                task,
                ["task_type", "prompt", "expected_answer_format"],
                f"levels[{index}].tasks[{task_index}]",
            )

    if seen_pairs != EXPECTED_LEVELS:
        raise ValidationError(
            "Levels must appear in this order: "
            + ", ".join(f"{key}/{label}" for key, label in EXPECTED_LEVELS)
        )


def require_fields(obj: dict[str, Any], fields: list[str], context: str) -> None:
    missing = [field for field in fields if field not in obj]
    if missing:
        raise ValidationError(f"Missing fields in {context}: {', '.join(missing)}")


def render_html(data: dict[str, Any], config: RenderConfig) -> str:
    variant = TEMPLATE_VARIANTS[config.template_variant]
    pages = [
        render_page(data, level, variant, page_number=index + 1)
        for index, level in enumerate(data["levels"])
    ]
    title = f"{data['topic']} - Arbeitsblaetter"
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <style>
{build_css()}
  </style>
</head>
<body>
  <main class="worksheet-set">
    {''.join(pages)}
  </main>
</body>
</html>
"""


def render_page(
    worksheet_set: dict[str, Any],
    level: dict[str, Any],
    variant: dict[str, Any],
    page_number: int,
) -> str:
    tasks_html = "".join(render_task(task, number=index + 1) for index, task in enumerate(level["tasks"]))
    support_material = render_tag_list(level["support_material"], "Unterstuetzung")
    solution_notes = render_tag_list(level["solution_notes"], "Loesung")
    image_box = render_image_box(level)
    footer_boxes = render_footer_boxes() if variant["show_memo"] else ""
    instruction_rows = render_instruction_rows(level, variant)
    return f"""
    <section class="page">
      <div class="top-grid">
        <div class="subject-box">{escape(worksheet_set['target_group'])}</div>
        <div class="title-box">
          <div class="level-label">{escape(level['level_label'])}</div>
          <h1>{escape(worksheet_set['topic'])}</h1>
          <p class="title-sub">{escape(level['student_title'])}</p>
        </div>
      </div>

      <div class="meta-grid">
        <div class="meta-box">Datum:</div>
        <div class="meta-box">Name:</div>
      </div>

      <div class="sheet-frame">
        <div class="sheet-pill">Arbeitsanweisung</div>
        {instruction_rows}

        <div class="workspace {escape(config_variant_class(variant))}">
          <div class="workspace-main">
            <div class="instruction-copy">
              <p class="instruction-text">{escape(level['student_instruction'])}</p>
              <p class="teacher-note">{escape(worksheet_set['general_teacher_note'])}</p>
              <p class="difficulty-note">{escape(level['difficulty_description'])}</p>
            </div>
            <div class="task-stack">
              {tasks_html}
            </div>
          </div>
          <aside class="workspace-side">
            {support_material}
            {image_box}
            {solution_notes}
          </aside>
        </div>

        {footer_boxes}

        <div class="sheet-footer">
          <span>Fußzeile mit Erklärung / Version / Ersteller</span>
          <span>Seite {page_number}</span>
        </div>
      </div>
    </section>
    """


def render_variant_hint(text: str) -> str:
    if not text:
        return ""
    return f'<p class="variant-hint">{escape(text)}</p>'


def config_variant_class(variant: dict[str, Any]) -> str:
    return "workspace-with-footer" if variant["show_memo"] else "workspace-blank"


def render_instruction_rows(level: dict[str, Any], variant: dict[str, Any]) -> str:
    if not variant["show_memo"]:
        return ""

    rows = [level["student_instruction"]]
    rows.extend(task["prompt"] for task in level["tasks"][:2])
    rows.append("Arbeite ruhig und Schritt für Schritt.")
    fallback_rows = [
        "Arbeite ruhig und Schritt für Schritt.",
        "Kontrolliere deine Lösung am Ende.",
    ]
    for item in fallback_rows:
        if len(rows) < 4:
            rows.append(item)
    rows = rows[:4]
    icons = [
        ROOT / "pictogramme" / "Lesen-1.png",
        ROOT / "pictogramme" / "Lesen-2.png",
        ROOT / "pictogramme" / "Betrachten-1.png",
        ROOT / "pictogramme" / "Verbinden-1.png",
    ]
    rendered = []
    for index, text in enumerate(rows):
        icon_path = icons[index] if icons[index].exists() else None
        icon_html = (
            f'<img class="instruction-icon" src="{icon_path.as_uri()}" alt="Symbol">'
            if icon_path
            else ""
        )
        row_class = "instruction-row instruction-row-accent" if index < 3 else "instruction-row"
        rendered.append(
            f'<div class="{row_class}"><div class="instruction-icon-box">{icon_html}</div>'
            f'<div class="instruction-row-text">{escape(text)}</div></div>'
        )
    return f'<div class="instruction-row-stack">{"".join(rendered)}</div>'


def render_footer_boxes() -> str:
    return """
    <div class="bottom-zone">
      <div class="points-card">
        <div class="points-diagonal"></div>
        <div class="points-copy">
          <p><strong>Punkte:</strong> ____</p>
          <p>von ____</p>
          <p>Das muss ich üben!</p>
          <p>Das kann ich manchmal!</p>
          <p>Das kann ich gut!</p>
        </div>
      </div>
      <div class="memo-card">
        <p class="memo-label">Memo:</p>
      </div>
    </div>
    """


def render_task(task: dict[str, Any], number: int) -> str:
    icon_path = TASK_ICON_MAP.get(task["task_type"])
    icon_html = ""
    if icon_path and icon_path.exists():
        icon_html = (
            f'<img class="task-icon" src="{icon_path.as_uri()}" '
            f'alt="{escape(task["task_type"])}">'
        )

    options_html = ""
    if task.get("options"):
        options = "".join(f"<li>{escape(str(option))}</li>" for option in task["options"])
        options_html = f'<ul class="task-options">{options}</ul>'

    hint_html = ""
    if task.get("hint"):
        hint_html = f'<p class="task-hint">Tipp: {escape(task["hint"])}</p>'

    return f"""
    <article class="task-card">
      <div class="task-card-header">
        <span class="task-number">{number}</span>
        {icon_html}
        <span class="task-type">{escape(task['task_type']).replace('_', ' ')}</span>
      </div>
      <p class="task-prompt">{escape(task['prompt'])}</p>
      {options_html}
      <div class="answer-box">
        <span>Erwartete Antwort:</span>
        <strong>{escape(task['expected_answer_format'])}</strong>
      </div>
      {hint_html}
    </article>
    """


def render_tag_list(items: list[str], label: str) -> str:
    if not items:
        return ""
    tags = "".join(f'<li>{escape(str(item))}</li>' for item in items)
    return f"""
    <section class="info-box">
      <h3>{escape(label)}</h3>
      <ul>{tags}</ul>
    </section>
    """


def render_image_box(level: dict[str, Any]) -> str:
    if not level["image_needed"]:
        return """
        <section class="info-box image-box">
          <h3>Bild</h3>
          <p>Kein zusaetzliches Bild noetig.</p>
        </section>
        """

    image_brief = level["image_brief"] or "Bildbeschreibung fehlt."
    return f"""
    <section class="info-box image-box">
      <h3>Bild</h3>
      <p>{escape(image_brief)}</p>
    </section>
    """


def render_memo_box() -> str:
    items = [
        "Das kann ich gut!",
        "Das kann ich manchmal!",
        "Das muss ich ueben!",
    ]
    content = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"""
    <aside class="memo-box">
      <p class="memo-title">Memo</p>
      <ul>{content}</ul>
    </aside>
    """


def build_css() -> str:
    return """
    @page {
      size: A4 portrait;
      margin: 0;
    }

    :root {
      --paper: #ffffff;
      --ink: #2a2a2a;
      --muted: #565656;
      --line: #808080;
      --line-soft: #a6a6a6;
      --green-a: #e8efd7;
      --green-b: #d7eb8a;
      --point-green: #9fca8d;
      --font-main: "OpenSan", "Open Sans", "Aptos", "Segoe UI", sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: var(--font-main);
      color: var(--ink);
      background: #ffffff;
    }

    .worksheet-set {
      width: 210mm;
      margin: 0 auto;
      padding: 0;
    }

    .page {
      position: relative;
      width: 210mm;
      height: 297mm;
      margin: 0 auto;
      padding: 8.5mm 8.5mm 0;
      background: var(--paper);
      page-break-after: always;
    }

    .page:last-child {
      page-break-after: auto;
    }

    .top-grid,
    .meta-grid {
      display: grid;
      grid-template-columns: 56mm 1fr;
      column-gap: 2.2mm;
    }

    .top-grid {
      height: 16mm;
      margin-bottom: 2mm;
    }

    .meta-grid {
      height: 10mm;
      margin-bottom: 2mm;
    }

    .subject-box,
    .title-box,
    .meta-box,
    .sheet-frame,
    .sheet-pill,
    .instruction-row,
    .instruction-icon-box,
    .task-card,
    .info-box,
    .points-card,
    .memo-card {
      border: 0.35mm solid var(--line);
      border-radius: 1.7mm;
      background: #ffffff;
    }

    .subject-box,
    .title-box,
    .meta-box {
      padding: 2.6mm 3mm;
      display: flex;
      align-items: center;
      font-size: 5.2mm;
    }

    .title-box {
      display: block;
      padding-top: 2.2mm;
      padding-left: 4.2mm;
    }

    .level-label {
      font-size: 3.2mm;
      margin-bottom: 0.6mm;
      text-transform: uppercase;
      color: var(--muted);
    }

    h1 {
      margin: 6px 0 4px;
      font-size: 7.2mm;
      line-height: 1;
      font-weight: 400;
    }

    .title-sub {
      margin: 0;
      font-size: 3.8mm;
      color: var(--muted);
    }

    .sheet-frame {
      position: relative;
      height: 271.5mm;
      padding: 6.7mm 4.2mm 4mm;
    }

    .sheet-pill {
      height: 10mm;
      display: flex;
      align-items: center;
      padding: 0 3mm;
      font-size: 6mm;
      margin-bottom: 9mm;
    }

    .instruction-row-stack {
      display: grid;
      gap: 4mm;
      margin: 0 4mm 5mm 4mm;
    }

    .instruction-row {
      height: 12mm;
      display: grid;
      grid-template-columns: 15mm 1fr;
      gap: 2mm;
      align-items: center;
      border-radius: 2mm;
      overflow: hidden;
    }

    .instruction-row-accent .instruction-row-text {
      background: linear-gradient(90deg, var(--green-a), var(--green-b));
    }

    .instruction-icon-box {
      width: 15mm;
      height: 12mm;
      display: grid;
      place-items: center;
      border: none;
      border-right: 0.35mm solid var(--line);
      border-radius: 0;
    }

    .instruction-icon {
      width: 13mm;
      height: 10mm;
      object-fit: contain;
    }

    .instruction-row-text {
      height: 100%;
      display: flex;
      align-items: center;
      padding: 0 3mm;
      font-size: 4.2mm;
      border-left: none;
      border-radius: 0 2mm 2mm 0;
    }

    .workspace {
      display: grid;
      grid-template-columns: 1fr 42mm;
      gap: 4mm;
    }

    .workspace-blank {
      min-height: 205mm;
    }

    .workspace-with-footer {
      min-height: 152mm;
      margin-top: 2mm;
    }

    .workspace-main,
    .workspace-side {
      min-height: 100%;
    }

    .workspace-main {
      padding: 1mm 0;
    }

    .instruction-copy {
      margin-bottom: 3mm;
    }

    .instruction-text {
      margin: 0;
      font-size: 4.1mm;
      line-height: 1.35;
      font-weight: 400;
    }

    .teacher-note,
    .difficulty-note,
    .variant-hint {
      margin: 2mm 0 0;
      color: var(--muted);
      line-height: 1.35;
      font-size: 3.5mm;
    }

    .task-stack {
      display: grid;
      gap: 3mm;
    }

    .workspace-side {
      display: grid;
      align-content: start;
      gap: 3mm;
    }

    .task-card {
      padding: 3mm;
      border-radius: 2mm;
    }

    .task-card-header {
      align-items: center;
      display: flex;
      gap: 2mm;
    }

    .task-number {
      min-width: 6mm;
      font-weight: 700;
      display: inline-flex;
    }

    .task-icon {
      width: 8mm;
      height: 8mm;
      object-fit: contain;
    }

    .task-type {
      font-size: 3.1mm;
      color: var(--muted);
    }

    .task-prompt {
      margin: 2mm 0 0;
      line-height: 1.35;
      font-size: 3.8mm;
    }

    .answer-box {
      margin-top: 2mm;
      font-size: 3.3mm;
      color: var(--muted);
      display: grid;
    }

    .task-hint {
      margin: 2mm 0 0;
      color: var(--muted);
      font-style: italic;
      font-size: 3.2mm;
    }

    .info-box {
      padding: 3mm;
      border-radius: 0;
    }

    .info-box h3 {
      margin: 0 0 1mm;
      font-size: 4mm;
      font-weight: 400;
    }

    .info-box ul,
    .task-options {
      margin: 0;
      padding-left: 4mm;
      font-size: 3.6mm;
      line-height: 1.35;
    }

    .bottom-zone {
      position: absolute;
      left: 4mm;
      right: 4mm;
      bottom: 4mm;
      height: 27mm;
      border-top: 0.35mm solid var(--line);
      display: grid;
      grid-template-columns: 40mm 1fr;
      gap: 6mm;
      padding-top: 3mm;
    }

    .points-card {
      position: relative;
      overflow: hidden;
      padding: 2mm;
    }

    .points-diagonal {
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(135deg, var(--point-green) 0 47%, transparent 47% 100%);
    }

    .points-copy {
      position: relative;
      z-index: 1;
      font-size: 2.8mm;
      line-height: 1.2;
    }

    .points-copy p {
      margin: 0 0 1.1mm;
    }

    .memo-card {
      padding: 2mm 3mm;
    }

    .memo-label {
      margin: 0;
      font-size: 5mm;
    }

    .sheet-footer {
      position: absolute;
      left: 0;
      right: 0;
      bottom: -5mm;
      display: flex;
      justify-content: space-between;
      font-size: 3.1mm;
      color: var(--ink);
    }

    @media (max-width: 960px) {
      .worksheet-set {
        width: 100%;
      }

      .page {
        width: 100vw;
        height: auto;
        min-height: 297mm;
        transform-origin: top center;
      }
    }
    """


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    validate_schema_file(args.schema)
    worksheet_set = load_json(args.input)
    validate_worksheet_set(worksheet_set)
    config = RenderConfig(template_variant=args.template, output_path=args.output)
    html = render_html(worksheet_set, config)
    write_output(config.output_path, html)
    print(f"Rendered {config.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
