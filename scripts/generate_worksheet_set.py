#!/usr/bin/env python3
"""Generate worksheet JSON via the OpenAI Responses API."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from render_worksheets import ValidationError, load_json, validate_worksheet_set


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "system-prompt.md"
SCHEMA_PATH = ROOT / "schemas" / "worksheet-set.schema.json"
OUTPUT_DIR = ROOT / "out" / "generated"
EXAMPLE_OUTPUT_PATH = ROOT / "examples" / "output-example.json"

API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.4-mini"


class GenerationError(Exception):
    """Raised when a worksheet set cannot be generated."""


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def load_schema() -> dict[str, Any]:
    return load_json(SCHEMA_PATH)


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    topic = str(payload.get("topic", "")).strip()
    learning_goal = str(payload.get("learning_goal", "")).strip()
    if not topic:
        raise GenerationError("Bitte ein Thema angeben.")
    if not learning_goal:
        raise GenerationError("Bitte ein Lernziel angeben.")

    target_group = str(payload.get("target_group", "")).strip() or (
        "Foerderschulbereich, fruehe Lernstufe"
    )
    focus = str(payload.get("focus", "")).strip()
    image_preference = str(payload.get("image_preference", "optional")).strip() or "optional"
    template_variant = str(payload.get("template_variant", "instructions")).strip() or "instructions"

    vocabulary_items = payload.get("known_vocabulary") or []
    if isinstance(vocabulary_items, str):
        vocabulary_items = [part.strip() for part in vocabulary_items.split(",")]

    known_vocabulary = [item.strip() for item in vocabulary_items if str(item).strip()]

    return {
        "topic": topic,
        "learning_goal": learning_goal,
        "target_group": target_group,
        "focus": focus,
        "image_preference": image_preference,
        "template_variant": template_variant,
        "known_vocabulary": known_vocabulary,
    }


def build_user_prompt(payload: dict[str, Any]) -> str:
    vocabulary = ", ".join(payload["known_vocabulary"]) if payload["known_vocabulary"] else "keine Vorgabe"
    focus = payload["focus"] or "klare Sprache, hohe Strukturierung, foerderschulgeeignete Differenzierung"
    return (
        "Erstelle einen kompletten Arbeitsblatt-Satz mit genau drei Niveaustufen.\n\n"
        f"Thema: {payload['topic']}\n"
        f"Lernziel: {payload['learning_goal']}\n"
        f"Zielgruppe: {payload['target_group']}\n"
        f"Didaktischer Fokus: {focus}\n"
        f"Bildbedarf: {payload['image_preference']}\n"
        f"Bekannter Wortschatz: {vocabulary}\n\n"
        "Wichtig:\n"
        "- Gib genau drei Stufen aus: sehr leicht, mittel, etwas schwerer.\n"
        "- Die Aufgaben muessen kindgerecht, konkret und sofort im Unterricht nutzbar sein.\n"
        "- Die Felder muessen zum JSON-Schema passen.\n"
        "- Formuliere die Schuelertexte auf Deutsch.\n"
        "- Schreibe keine Erklaerung ausserhalb des JSON."
    )


def build_request_payload(
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "worksheet_set",
                "schema": schema,
                "strict": True,
            }
        },
    }


def generate_worksheet_set(payload: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise GenerationError("OPENAI_API_KEY ist nicht gesetzt.")

    model_name = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    normalized = normalize_payload(payload)
    schema = load_schema()
    request_payload = build_request_payload(
        system_prompt=load_system_prompt(),
        user_prompt=build_user_prompt(normalized),
        schema=schema,
        model=model_name,
    )

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GenerationError(f"OpenAI-API-Fehler ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise GenerationError(f"OpenAI-API nicht erreichbar: {exc.reason}") from exc

    parsed = json.loads(raw)
    worksheet_set = extract_structured_output(parsed)
    validate_worksheet_set(worksheet_set)
    worksheet_set["_meta"] = {
        "model": model_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "template_variant": normalized["template_variant"],
    }
    return worksheet_set


def extract_structured_output(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("error"):
        raise GenerationError(str(response["error"]))

    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                refusal_text = content.get("refusal") or "Die Anfrage wurde abgelehnt."
                raise GenerationError(str(refusal_text))

            if content.get("type") in {"output_text", "text"}:
                text_value = content.get("text")
                if isinstance(text_value, dict):
                    text_value = text_value.get("value")
                if isinstance(text_value, str) and text_value.strip():
                    return parse_json_object(text_value)

    if isinstance(response.get("output_text"), str) and response["output_text"].strip():
        return parse_json_object(response["output_text"])

    raise GenerationError("Keine strukturierte JSON-Antwort in der API-Antwort gefunden.")


def parse_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise GenerationError(f"Antwort war kein gueltiges JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise GenerationError("Die Modellantwort ist kein JSON-Objekt.")
    return parsed


def save_generated_json(worksheet_set: dict[str, Any], topic: str | None = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    topic_slug = slugify(topic or worksheet_set.get("topic", "arbeitsblatt"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUTPUT_DIR / f"{timestamp}-{topic_slug}.json"
    path.write_text(json.dumps(worksheet_set, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_demo_worksheet_set() -> dict[str, Any]:
    worksheet_set = load_json(EXAMPLE_OUTPUT_PATH)
    validate_worksheet_set(worksheet_set)
    worksheet_set["_meta"] = {
        "model": "demo",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "template_variant": "instructions",
    }
    return worksheet_set


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "arbeitsblatt"


__all__ = [
    "DEFAULT_MODEL",
    "GenerationError",
    "load_demo_worksheet_set",
    "generate_worksheet_set",
    "normalize_payload",
    "save_generated_json",
]
