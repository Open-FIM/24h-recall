"""
OpenFIM 24h Recall Pipeline for OpenWebUI
=================================================
Purpose:
- Start baseline or post-intervention Intake24 recalls by participant ID.
- Retrieve saved Intake24 nutrient totals by participant ID + timepoint.
- Retrieve food-level recall tables by participant ID + timepoint.
- It is meant to be a testable workflow for Intake24-based multi-study recall collection.

Expected webhook endpoints:
- GET /generate-link/<participant_id>/<study_id>/<timepoint>
- GET /recall/<participant_id>/<study_id>/<timepoint>
- GET /recall-foods/<participant_id>/<study_id>/<timepoint>

Important:
- WEBHOOK_INTERNAL_BASE is for the pipeline container to call the webhook.
- The user-facing link returned to the browser should be the actual Intake24 link on port 8200,
  returned by /generate-link
"""

from typing import Generator, Iterator, List
from pydantic import BaseModel
import re
import os
import requests


WEBHOOK_INTERNAL_BASE = os.environ.get("WEBHOOK_INTERNAL_BASE", "http://localhost:5000")
INTAKE24_URL = os.environ.get("INTAKE24_URL", "http://localhost:8200")
SURVEY_ID = os.environ.get("SURVEY_ID", "openfim")
DEFAULT_STUDY_ID = os.environ.get("DEFAULT_STUDY_ID", "DEMO_STUDY")

TIMEPOINT_LABELS = {
    "0": "baseline",
    "1": "post-intervention",
}

TIMEPOINT_ALIASES = {
    "baseline": "0",
    "base": "0",
    "pre": "0",
    "pre-intervention": "0",
    "id-0": "0",
    "0": "0",
    "post": "1",
    "post-intervention": "1",
    "post intervention": "1",
    "follow-up": "1",
    "followup": "1",
    "end": "1",
    "id-1": "1",
    "1": "1",
}


def parse_timepoint(text: str) -> str | None:
    """Parse baseline/post-intervention timepoint from user text."""
    s = (text or "").strip().lower()
    for key, value in TIMEPOINT_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", s):
            return value
    return None


def parse_study_id(text: str) -> str | None:
    """Parse study IDs like STUDY_A, PILOT1, SITE_A, etc."""
    s = (text or "").strip()

    m = re.search(
        r"\b(?:study|study id|in)\s*[:#-]?\s*([A-Za-z][A-Za-z0-9_-]{1,30})\b",
        s,
        re.IGNORECASE,
    )
    if m:
        candidate = m.group(1).upper()
        # Avoid accidentally treating generic words as study IDs
        if candidate not in {"BASELINE", "POST", "RECALL", "TIMEPOINT", "PARTICIPANT"}:
            return candidate

    return None


def format_timepoint_label(timepoint: str | int | None) -> str:
    tp = str(timepoint) if timepoint is not None else ""
    return TIMEPOINT_LABELS.get(tp, f"timepoint {tp}")


def get_intake24_link(
    participant_id: str,
    timepoint: str = "0",
    study_id: str = DEFAULT_STUDY_ID,
) -> str:
    """
    Ask the webhook internally to generate the Intake24 JWT link,
    then return the actual Intake24 link to the user.

    This avoids sending the user's browser to port 5000.
    """
    participant_id = str(participant_id).strip().upper()
    study_id = str(study_id).strip().upper() or DEFAULT_STUDY_ID
    timepoint = str(timepoint).strip()

    try:
        r = requests.get(
            f"{WEBHOOK_INTERNAL_BASE}/generate-link/{participant_id}/{study_id}/{timepoint}",
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            link = data.get("link") or data.get("url")
            if link:
                return link
        print(f"[Recall Pipeline] Link generation failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[Recall Pipeline] Link generation failed: {e}")

    # Fallback only. This will not include the participant/timepoint JWT.
    return f"{INTAKE24_URL}/{SURVEY_ID}"


def get_intake24_recall(
    participant_id: str,
    timepoint: str = "0",
    study_id: str = DEFAULT_STUDY_ID,
) -> dict | None:
    """Retrieve latest Intake24 nutrient totals for participant/study/timepoint."""
    participant_id = str(participant_id).strip().upper()
    study_id = str(study_id).strip().upper() or DEFAULT_STUDY_ID
    timepoint = str(timepoint).strip()

    try:
        r = requests.get(
            f"{WEBHOOK_INTERNAL_BASE}/recall/{participant_id}/{study_id}/{timepoint}",
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("found"):
                data["participant_id"] = participant_id
                data["study_id"] = study_id
                data["timepoint"] = timepoint
                return data
    except Exception as e:
        print(f"[Recall Pipeline] Recall lookup failed: {e}")

    return None


def get_food_level_recall_list(
    participant_id: str,
    timepoint: str = "0",
    study_id: str = DEFAULT_STUDY_ID,
) -> list:
    """Retrieve food-level recall rows for participant/study/timepoint."""
    participant_id = str(participant_id).strip().upper()
    study_id = str(study_id).strip().upper() or DEFAULT_STUDY_ID
    timepoint = str(timepoint).strip()

    try:
        r = requests.get(
            f"{WEBHOOK_INTERNAL_BASE}/recall-foods/{participant_id}/{study_id}/{timepoint}",
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("found"):
                return data.get("foods", []) or []
    except Exception as e:
        print(f"[Recall Pipeline] food-level recall list lookup failed: {e}")

    return []


def format_recall_summary(recall_data: dict) -> str:
    """Format nutrient totals from saved Intake24 recall."""
    if not recall_data:
        return ""

    n = recall_data.get("nutrients", {}) or recall_data.get("nutrient_totals", {}) or {}
    meals = n.get("meals", []) or []

    meal_lines = []
    for meal in meals:
        foods = ", ".join(
            f"{f.get('name', '')} ({f.get('kcal', 0)} kcal)"
            for f in meal.get("foods", [])
        )
        meal_lines.append(f"- **{meal.get('name', 'Meal')}**: {foods}")

    meals_str = "\n".join(meal_lines) or "No meal-level detail recorded."
    participant_id = recall_data.get("participant_id", "")
    timepoint = recall_data.get("timepoint", "")
    label = format_timepoint_label(timepoint)

    return (
        f"## Intake24 Recall — {participant_id}, {label}\n\n"
        f"*Submitted: {recall_data.get('completed_at', '')[:10]}*\n\n"
        f"{meals_str}\n\n"
        f"**Daily totals:**\n"
        f"- Calories: {round(n.get('total_kcal', 0))} kcal\n"
        f"- Protein: {round(n.get('protein_g', 0))} g\n"
        f"- Fat: {round(n.get('fat_g', 0))} g\n"
        f"- Carbs: {round(n.get('carbs_g', 0))} g\n"
        f"- Fibre: {round(n.get('fibre_g', 0))} g\n"
        f"- Sodium: {round(n.get('sodium_mg', 0))} mg"
    )


def format_food_level_recall_section(foods: list, completed_at: str = "") -> str:
    """Format food-level recall record as a markdown table."""
    if not foods:
        return "No food-level recall rows were returned for this recall."

    date_str = completed_at[:10] if completed_at else ""
    lines = [
        "## Food-Level Recall Record",
        f"*Dietary recall date: {date_str}*\n",
        "| Meal | Food Code | Source | Food Name | Additional Description | Portion | Grams | kcal |",
        "|------|-----------|--------|-----------|------------------------|---------|-------|------|",
    ]

    for food in foods:
        lines.append(
            f"| {food.get('meal', '')} "
            f"| {food.get('food_code', '')} "
            f"| {food.get('source', '')} "
            f"| {food.get('name', '')} "
            f"| {food.get('additional_description', '')} "
            f"| {food.get('portion', '')} "
            f"| {food.get('grams', '')}g "
            f"| {food.get('kcal', '')} |"
        )
    return "\n".join(lines)


def looks_like_recall_link_request(msg: str) -> bool:
    m = msg.lower()
    recall_words = [
        "recall",
        "intake24",
        "dietary recall",
        "baseline",
        "post-intervention",
        "post intervention",
        "follow-up",
        "followup",
        "id-0",
        "id-1",
    ]
    action_words = [
        "link",
        "start",
        "open",
        "update",
        "redo",
        "new",
        "complete",
        "create",
        "generate",
        "do",
        "begin",
        "launch",
    ]
    lookup_words = ["show", "view", "check", "retrieve", "report", "what did", "what is", "food record", "food code", "24h recall"]

    if any(w in m for w in lookup_words):
        return False
    return any(w in m for w in recall_words) and any(w in m for w in action_words)


def handle_recall_link_request(user_message: str) -> str | None:
    if not looks_like_recall_link_request(user_message):
        return None

    participant_id = parse_participant_id(user_message)
    timepoint = parse_timepoint(user_message)
    study_id = parse_study_id(user_message) or DEFAULT_STUDY_ID

    if not participant_id:
        return (
            "Which participant ID should I use?\n\n"
            "For example:\n\n"
            "`start baseline recall for P001 in STUDY_A`"
        )

    if not timepoint:
        return (
            f"Which recall timepoint should I create for **{participant_id}**?\n\n"
            "- Type **baseline** for ID-0\n"
            "- Type **post-intervention** for ID-1"
        )

    label = format_timepoint_label(timepoint)
    link = get_intake24_link(participant_id, timepoint, study_id)

    return (
        f"Here is the **{label} dietary recall link** for participant **{participant_id}** "
        f"in study **{study_id}**:\n\n"
        f"**[Open Intake24 {label} recall]({link})**\n\n"
        "Share only this participant-facing Intake24 link with the participant. "
        "Do not share internal webhook, localhost, Docker, admin, or server-side URLs.\n\n"
        "After the participant completes Intake24, come back and type:\n\n"
        f"`show {label} recall for {participant_id} in {study_id}`\n\n"
        "or\n\n"
        f"`show food record for {participant_id} in {study_id} at {label}`"
    )


def handle_recall_lookup_request(user_message: str) -> str | None:
    msg = user_message.lower()
    wants_lookup = any(w in msg for w in ["show", "view", "check", "retrieve", "what did", "what is"])
    mentions_recall = any(w in msg for w in ["recall", "intake24", "baseline", "post-intervention", "post intervention", "id-0", "id-1"])

    if not wants_lookup or not mentions_recall:
        return None

    participant_id = parse_participant_id(user_message)
    timepoint = parse_timepoint(user_message)
    study_id = parse_study_id(user_message) or DEFAULT_STUDY_ID

    if not participant_id:
        return "Which participant ID should I look up? For example: `show baseline recall for P001`."
    if not timepoint:
        return (
            f"Which timepoint should I look up for **{participant_id}**?\n\n"
            "- **baseline** / ID-0\n"
            "- **post-intervention** / ID-1"
        )

    recall_data = get_intake24_recall(participant_id, timepoint, study_id)
    if not recall_data:
        label = format_timepoint_label(timepoint)
        return (
        f"No {label} recall was found for **{participant_id}** in study **{study_id}**.\n\n"
        f"To create one, type: `start {label} recall for {participant_id} in {study_id}`"
        )

    return format_recall_summary(recall_data)


def handle_food_level_report_request(user_message: str) -> str | None:
    msg = user_message.lower()
    wants_food_level_report = any(w in msg for w in ["24h recall", "food code", "food record", "food record"])
    if not wants_food_level_report:
        return None

    participant_id = parse_participant_id(user_message)
    timepoint = parse_timepoint(user_message)
    study_id = parse_study_id(user_message) or DEFAULT_STUDY_ID

    if not participant_id:
        return "Which participant ID should I use? For example: `show food record for P001 in STUDY_A at timepoint 0`."
    if not timepoint:
        return (
            f"Which timepoint should I use for **{participant_id}**?\n\n"
            "- **baseline** / ID-0\n"
            "- **post-intervention** / ID-1"
        )

    recall_info = get_intake24_recall(participant_id, timepoint, study_id)
    foods = get_food_level_recall_list(participant_id, timepoint, study_id)

    if not recall_info and not foods:
        label = format_timepoint_label(timepoint)
        return (
            f"No food-level recall record was found for **{participant_id}** "
            f"in study **{study_id}**, {label}.\n\n"
            f"To create the recall, type: `start {label} recall for {participant_id} in {study_id}`"
        )

    completed_at = recall_info.get("completed_at", "") if recall_info else ""
    return format_food_level_recall_section(foods, completed_at)


class Pipeline:
    class Valves(BaseModel):
        # Expose this so you can adjust if Docker networking changes.
        WEBHOOK_INTERNAL_BASE: str = WEBHOOK_INTERNAL_BASE
        INTAKE24_URL: str = INTAKE24_URL

    def __init__(self):
        self.name = "OpenFIM 24h Recall"
        self.valves = self.Valves()

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> str | Generator | Iterator:
        global WEBHOOK_INTERNAL_BASE, INTAKE24_URL
        WEBHOOK_INTERNAL_BASE = self.valves.WEBHOOK_INTERNAL_BASE.rstrip("/")
        INTAKE24_URL = self.valves.INTAKE24_URL.rstrip("/")

        print("[OpenFIM 24h Recall] VERSION: split-recall-v1")

        food_level_response = handle_food_level_report_request(user_message)
        if food_level_response:
            return food_level_response

        recall_link_response = handle_recall_link_request(user_message)
        if recall_link_response:
            return recall_link_response

        recall_lookup_response = handle_recall_lookup_request(user_message)
        if recall_lookup_response:
            return recall_lookup_response

        return (
            "I can help with Intake24 recalls and food-level recall reports.\n\n"
            "Try one of these:\n\n"
            "- `start baseline recall for P001 in STUDY_A`\n"
            "- `start post-intervention recall for P001 in STUDY_A`\n"
            "- `show baseline recall for P001 in STUDY_A`\n"
            "- `show food record for P001 in STUDY_A at baseline`"
        )
