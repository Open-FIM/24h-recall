"""
OpenFIM 24h Recall — Intake24 Webhook Receiver

Receives completed Intake24 recall data and stores it in PostgreSQL.
Also generates participant-facing Intake24 links.

dietary_recalls preserves repeated submissions using:
participant_id, study_id, timepoint, recall_number, and attempt_number.

Preferred Intake24 username format:
PARTICIPANT:STUDY:TIMEPOINT:RECALL_NUMBER
Example: P001:STUDY_A:0:1

Backward-compatible formats:
PARTICIPANT:STUDY:TIMEPOINT
PARTICIPANT:TIMEPOINT
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import jwt
import psycopg2
from flask import Flask, jsonify, redirect, request

app = Flask(__name__)

# ── Configuration ─────────────────────────────────────────────

INTAKE24_URL = os.environ.get("INTAKE24_URL", "http://localhost:8200").rstrip("/")
SURVEY_ID = os.environ.get("SURVEY_ID", "openfim")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
DEFAULT_STUDY_ID = os.environ.get("DEFAULT_STUDY_ID", "DEMO_STUDY")
OPENFIM_DATA_DIR = os.environ.get("OPENFIM_DATA_DIR", "./data")

MAX_RECALL_NUMBER = int(os.environ.get("MAX_RECALL_NUMBER", "3"))
JWT_EXP_DAYS = int(os.environ.get("JWT_EXP_DAYS", "365"))

PG_RECALLS = {
    "host": os.environ.get("RECALLS_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("RECALLS_DB_PORT", "5432")),
    "database": os.environ.get("RECALLS_DB_NAME", "openfim_recalls"),
    "user": os.environ.get("RECALLS_DB_USER", "postgres"),
    "password": os.environ.get("RECALLS_DB_PASSWORD", ""),
}

PG_CONFIG = {
    "host": os.environ.get("FOODS_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("FOODS_DB_PORT", "5432")),
    "database": os.environ.get("FOODS_DB_NAME", "intake24_foods_dev"),
    "user": os.environ.get("FOODS_DB_USER", "postgres"),
    "password": os.environ.get("FOODS_DB_PASSWORD", ""),
}


# ── Database helpers ──────────────────────────────────────────

def get_recalls_conn():
    return psycopg2.connect(**PG_RECALLS)


def init_db() -> None:
    conn = get_recalls_conn()
    conn.close()
    print(f"[Webhook] Connected to {PG_RECALLS['database']}")


# ── Intake24 username parsing ─────────────────────────────────

def parse_username(username: str) -> tuple[str, str, int, int]:
    """
    Parse Intake24 username into participant_id, study_id, timepoint, recall_number.

    Preferred format:
        PARTICIPANT:STUDY:TIMEPOINT:RECALL_NUMBER

    Backward-compatible formats:
        PARTICIPANT:STUDY:TIMEPOINT
        PARTICIPANT:TIMEPOINT
    """
    parts = [p.strip() for p in str(username).split(":")]

    if len(parts) == 4:
        participant_id, study_id, timepoint_raw, recall_number_raw = parts
    elif len(parts) == 3:
        participant_id, study_id, timepoint_raw = parts
        recall_number_raw = "1"
    elif len(parts) == 2:
        participant_id, timepoint_raw = parts
        study_id = DEFAULT_STUDY_ID
        recall_number_raw = "1"
    else:
        raise ValueError(
            "username must be participant:study:timepoint:recall_number, "
            "participant:study:timepoint, or participant:timepoint"
        )

    participant_id = participant_id.upper()
    study_id = study_id.upper()

    try:
        timepoint = int(timepoint_raw)
        recall_number = int(recall_number_raw)
    except ValueError as exc:
        raise ValueError("timepoint and recall_number must be integers") from exc

    validate_recall_number(recall_number)

    return participant_id, study_id, timepoint, recall_number


def validate_recall_number(recall_number: int) -> None:
    if recall_number < 1 or recall_number > MAX_RECALL_NUMBER:
        raise ValueError(f"recall_number must be between 1 and {MAX_RECALL_NUMBER}")


# ── Recall storage ────────────────────────────────────────────

def save_recall(
    participant_id: str,
    study_id: str,
    timepoint: int,
    recall_number: int,
    recall_data: dict[str, Any],
) -> int:
    """
    Save one dietary recall submission.

    timepoint = study-specific visit/timepoint, such as 0, 6, 12, 18, 24
    recall_number = planned recall slot within that timepoint, such as R1, R2, R3
    attempt_number = submission version for that participant/study/timepoint/recall_number

    This preserves repeated submissions instead of overwriting them.
    """
    validate_recall_number(recall_number)

    nutrients = extract_nutrients(recall_data)
    completed_at = datetime.now(timezone.utc).isoformat()

    conn = get_recalls_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT COALESCE(MAX(attempt_number), 0)
            FROM dietary_recalls
            WHERE participant_id = %s
              AND study_id = %s
              AND timepoint = %s
              AND recall_number = %s
            """,
            (participant_id, study_id, timepoint, recall_number),
        )

        attempt_number = cur.fetchone()[0] + 1

        cur.execute(
            """
            INSERT INTO dietary_recalls
              (participant_id, study_id, timepoint, recall_number, attempt_number,
               completed_at, recall_json, nutrient_totals)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                participant_id,
                study_id,
                timepoint,
                recall_number,
                attempt_number,
                completed_at,
                json.dumps(recall_data),
                json.dumps(nutrients),
            ),
        )

        conn.commit()
        return attempt_number

    finally:
        cur.close()
        conn.close()


# ── Nutrient and food extraction ──────────────────────────────

def extract_nutrients(data: dict[str, Any]) -> dict[str, Any]:
    """Extract key nutrient totals from Intake24 submission data."""
    try:
        meals = data.get("data", {}).get("meals", [])
        totals = {
            "total_kcal": 0,
            "protein_g": 0,
            "fat_g": 0,
            "carbs_g": 0,
            "sugar_g": 0,
            "fibre_g": 0,
            "sodium_mg": 0,
            "meals": [],
        }

        for meal in meals:
            meal_summary = {"name": meal.get("name", ""), "foods": []}

            for food in meal.get("foods", []):
                nutrients = food.get("nutrients", {}) or {}
                portion = food.get("portionSize", {}) or {}

                totals["total_kcal"] += nutrients.get("1", 0)
                totals["protein_g"] += nutrients.get("11", 0)
                totals["fat_g"] += nutrients.get("49", 0)
                totals["carbs_g"] += nutrients.get("13", 0)
                totals["sugar_g"] += nutrients.get("22", nutrients.get("23", 0))
                totals["fibre_g"] += nutrients.get("17", nutrients.get("15", 0))
                totals["sodium_mg"] += nutrients.get("138", nutrients.get("38", 0))

                meal_summary["foods"].append(
                    {
                        "name": food.get("localName") or food.get("englishName", ""),
                        "weight": portion.get("servingWeight", portion.get("weight", 0)),
                        "kcal": round(nutrients.get("1", 0), 1),
                    }
                )

            totals["meals"].append(meal_summary)

        for key in ["total_kcal", "protein_g", "fat_g", "carbs_g", "sugar_g", "fibre_g", "sodium_mg"]:
            totals[key] = round(totals[key], 1)

        return totals

    except Exception as exc:
        return {"error": str(exc), "raw": str(data)[:500]}


def lookup_alt_names(food_codes: list[str]) -> dict[str, str]:
    """Look up additional food descriptions from the optional Intake24 food database."""
    if not food_codes:
        return {}

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT code, alt_names FROM foods WHERE code = ANY(%s)", (food_codes,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = {}
        for code, alt_names in rows:
            if alt_names and isinstance(alt_names, dict):
                result[code] = alt_names.get("en", "")
            else:
                result[code] = ""
        return result

    except Exception as exc:
        print(f"[Webhook] alt_names lookup failed: {exc}")
        return {}


def build_food_list(recall_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Build structured food-level rows from Intake24 recall JSON."""
    try:
        meals = recall_json.get("data", {}).get("meals", [])
        foods_flat = []

        for meal in meals:
            for food in meal.get("foods", []):
                nutrient_table_id = food.get("nutrientTableId", "")
                nutrient_table_code = food.get("nutrientTableCode", "")
                intake24_code = food.get("code", "")
                name = food.get("englishName") or food.get("localName", "")
                portion = food.get("portionSize", {}) or {}
                serving_weight = portion.get("servingWeight", 0)
                nutrients = food.get("nutrients", {}) or {}
                kcal = round(nutrients.get("1", 0), 1)

                if nutrient_table_id == "USDA":
                    source = "USDA FNDDS"
                    food_code = nutrient_table_code
                else:
                    source = nutrient_table_id or "Unknown"
                    food_code = nutrient_table_code

                method = portion.get("method", "")
                if method in ("standard-unit", "standard-portion"):
                    unit = portion.get("unit", {})
                    quantity = portion.get("quantity", 1)
                    unit_name = unit.get("name", "") if isinstance(unit, dict) else ""
                    portion_str = f"{quantity} {unit_name}".strip()
                elif method == "as-served":
                    quantity = portion.get("quantity", 1)
                    portion_str = f"{quantity} serving(s)"
                elif method == "guide-image":
                    quantity = portion.get("quantity", 1)
                    portion_str = f"{quantity} item(s)"
                elif method == "drink-scale":
                    portion_str = f"{round(serving_weight, 1)} mL/g"
                else:
                    quantity = portion.get("quantity", 1)
                    portion_str = f"{quantity}"

                foods_flat.append(
                    {
                        "meal": meal.get("name", ""),
                        "food_code": food_code,
                        "intake24_code": intake24_code,
                        "source": source,
                        "name": name,
                        "additional_description": "",
                        "portion": portion_str,
                        "grams": round(serving_weight, 1),
                        "kcal": kcal,
                    }
                )

        all_intake24_codes = [f["intake24_code"] for f in foods_flat if f.get("intake24_code")]
        alt_names_map = lookup_alt_names(all_intake24_codes)

        for food in foods_flat:
            food["additional_description"] = alt_names_map.get(food.get("intake24_code", ""), "")
            food.pop("intake24_code", None)

        return foods_flat

    except Exception as exc:
        print(f"[Webhook] build_food_list error: {exc}")
        return []


# ── Callback endpoint ─────────────────────────────────────────

@app.route("/intake24/callback", methods=["POST"])
def intake24_callback():
    try:
        data = request.get_json(force=True)
        print(f"[Webhook] Received data: {json.dumps(data)[:200]}")

        try:
            username = data["data"]["user"]["aliases"][0]["username"]
        except (KeyError, IndexError, TypeError):
            username = data.get("userId") or data.get("username")

        if not username:
            print("[Webhook] No participant ID found in data")
            return jsonify({"status": "error", "message": "no participant ID"}), 400

        try:
            participant_id, study_id, timepoint, recall_number = parse_username(username)
        except ValueError as exc:
            print(f"[Webhook] Invalid username format: {username}")
            return jsonify({"status": "error", "message": str(exc)}), 400

        try:
            attempt = save_recall(participant_id, study_id, timepoint, recall_number, data)
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 409

        print(
            f"[Webhook] Saved recall for {participant_id}/{study_id} "
            f"timepoint {timepoint} recall {recall_number} attempt {attempt}"
        )

        return jsonify(
            {
                "status": "ok",
                "participant_id": participant_id,
                "study_id": study_id,
                "timepoint": timepoint,
                "recall_number": recall_number,
                "attempt_number": attempt,
            }
        ), 200

    except Exception as exc:
        print(f"[Webhook] Error: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


# ── Link generation ───────────────────────────────────────────

def generate_link(participant_id, study_id, timepoint, recall_number=1):
    """Generate a participant-facing Intake24 recall link."""
    if not JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET is not set. Set it in the environment before generating Intake24 links."
        )

    participant_id = str(participant_id).strip().upper()
    study_id = str(study_id).strip().upper() or DEFAULT_STUDY_ID
    timepoint = int(timepoint)
    recall_number = int(recall_number)
    validate_recall_number(recall_number)

    intake24_username = f"{participant_id}:{study_id}:{timepoint}:{recall_number}"

    payload = {
        "username": intake24_username,
        "iat": int(time.time()),
        "exp": int(time.time()) + (JWT_EXP_DAYS * 24 * 3600),
        "sub": SURVEY_ID,
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return f"{INTAKE24_URL}/{SURVEY_ID}/create-user/{token}"


@app.route("/generate-link/<participant_id>/<study_id>/<int:timepoint>", methods=["GET"])
def get_link(participant_id, study_id, timepoint):
    link = generate_link(participant_id, study_id, timepoint, recall_number=1)
    return jsonify(
        {
            "participant_id": participant_id.strip().upper(),
            "study_id": study_id.strip().upper(),
            "timepoint": timepoint,
            "recall_number": 1,
            "link": link,
            "message": f"Open Intake24 here: {link}",
        }
    )


@app.route("/generate-link/<participant_id>/<study_id>/<int:timepoint>/<int:recall_number>", methods=["GET"])
def get_link_with_recall_number(participant_id, study_id, timepoint, recall_number):
    try:
        link = generate_link(participant_id, study_id, timepoint, recall_number)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    return jsonify(
        {
            "participant_id": participant_id.strip().upper(),
            "study_id": study_id.strip().upper(),
            "timepoint": timepoint,
            "recall_number": recall_number,
            "link": link,
            "message": f"Open Intake24 here: {link}",
        }
    )


@app.route("/open-intake24/<participant_id>/<study_id>/<int:timepoint>", methods=["GET"])
def open_intake24(participant_id, study_id, timepoint):
    link = generate_link(participant_id, study_id, timepoint, recall_number=1)
    return redirect(link, code=302)


@app.route("/open-intake24/<participant_id>/<study_id>/<int:timepoint>/<int:recall_number>", methods=["GET"])
def open_intake24_with_recall_number(participant_id, study_id, timepoint, recall_number):
    link = generate_link(participant_id, study_id, timepoint, recall_number)
    return redirect(link, code=302)


# ── Recall lookup helpers ─────────────────────────────────────

def _fetch_recall_row(participant_id: str, study_id: str, timepoint: int, recall_number: int):
    participant_id = participant_id.strip().upper()
    study_id = study_id.strip().upper()
    validate_recall_number(recall_number)

    conn = get_recalls_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT participant_id, study_id, timepoint, recall_number, attempt_number,
                   completed_at, nutrient_totals, recall_json
            FROM dietary_recalls
            WHERE participant_id = %s
              AND study_id = %s
              AND timepoint = %s
              AND recall_number = %s
            ORDER BY attempt_number DESC
            LIMIT 1
            """,
            (participant_id, study_id, timepoint, recall_number),
        )
        return cur.fetchone()

    finally:
        cur.close()
        conn.close()


# ── Recall summary endpoints ──────────────────────────────────

@app.route("/recall/<participant_id>/<study_id>/<int:timepoint>", methods=["GET"])
def get_recall_by_timepoint(participant_id, study_id, timepoint):
    """Return latest recall attempt for participant/study/timepoint/recall 1."""
    return get_recall_by_timepoint_and_recall_number(participant_id, study_id, timepoint, 1)


@app.route("/recall/<participant_id>/<study_id>/<int:timepoint>/<int:recall_number>", methods=["GET"])
def get_recall_by_timepoint_and_recall_number(participant_id, study_id, timepoint, recall_number):
    """Return latest recall attempt for participant/study/timepoint/recall_number."""
    try:
        row = _fetch_recall_row(participant_id, study_id, timepoint, recall_number)
    except ValueError as exc:
        return jsonify({"found": False, "error": str(exc)}), 400

    if row:
        return jsonify(
            {
                "found": True,
                "participant_id": row[0],
                "study_id": row[1],
                "timepoint": row[2],
                "recall_number": row[3],
                "attempt_number": row[4],
                "completed_at": row[5],
                "nutrients": json.loads(row[6]) if row[6] else {},
            }
        )

    return jsonify({"found": False}), 404


# ── Food-level recall endpoints ───────────────────────────────

@app.route("/recall-foods/<participant_id>/<study_id>/<int:timepoint>", methods=["GET"])
def get_recall_foods_by_timepoint(participant_id, study_id, timepoint):
    """Return food-level rows for participant/study/timepoint/recall 1."""
    return get_recall_foods_by_timepoint_and_recall_number(participant_id, study_id, timepoint, 1)


@app.route("/recall-foods/<participant_id>/<study_id>/<int:timepoint>/<int:recall_number>", methods=["GET"])
def get_recall_foods_by_timepoint_and_recall_number(participant_id, study_id, timepoint, recall_number):
    """Return food-level rows for participant/study/timepoint/recall_number."""
    try:
        row = _fetch_recall_row(participant_id, study_id, timepoint, recall_number)
    except ValueError as exc:
        return jsonify({"found": False, "error": str(exc)}), 400

    if not row or not row[7]:
        return jsonify({"found": False}), 404

    recall_json = json.loads(row[7])
    food_list = build_food_list(recall_json)

    return jsonify(
        {
            "found": True,
            "participant_id": row[0],
            "study_id": row[1],
            "timepoint": row[2],
            "recall_number": row[3],
            "attempt_number": row[4],
            "completed_at": row[5],
            "foods": food_list,
            "total_foods": len(food_list),
        }
    )


# ── Start ─────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(OPENFIM_DATA_DIR, exist_ok=True)
    init_db()
    port = int(os.environ.get("WEBHOOK_PORT", "5000"))
    print(f"[OpenFIM 24h Recall Webhook] Starting on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
