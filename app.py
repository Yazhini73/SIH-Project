from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from image_processing.strip_layout import StripLayoutError, detect_and_crop, get_last_detection_debug
from services.overall_quality import calculate_overall
from services.prediction_service import ModelUnavailableError, PredictionError, PredictionService
from services.reference_service import ReferenceDataError, ReferenceService
from services.status_service import StatusConfigurationError, StatusService

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
HISTORY_FILE = ROOT / "reports" / "history.json"
HISTORY_FILE.parent.mkdir(exist_ok=True)


def _load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save_history(history: list[dict]) -> None:
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _reference_fields(parameter: str, value: float, reference: ReferenceService) -> dict:
    row = reference.nearest(parameter, value)
    return {
        "condition": row.get("Condition", row.get("condition", "")),
        "problem": row.get("Problem", row.get("problem", "")),
        "remedy": row.get("Remedy", row.get("remedy", "")),
    }


def _result(value: float, unit: str, parameter: str, status: str, fields: dict) -> dict:
    return {
        "value": round(value, 3),
        "unit": unit,
        "status": status,
        "status_color": StatusService.color(status),
        **fields,
    }


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/<page>")
def page(page: str):
    allowed = {"about", "how-it-works", "scan", "results", "dashboard", "history", "ai-model", "dataset", "feed-guide", "voice", "help"}
    if page not in allowed:
        return render_template("index.html"), 404
    return render_template(f"{page}.html" if page != "how-it-works" else "how_it_works.html")


@app.post("/api/analyze")
def analyze():
    upload = request.files.get("image") or request.files.get("strip_image")
    input_method = request.form.get("input_method", "upload").lower()
    moisture_raw = request.form.get("moisture", "").strip()
    if upload is None or not upload.filename:
        return _error("Please upload one complete test strip image.")
    if input_method not in {"upload", "camera"}:
        return _error("The image input method is invalid.")
    if not moisture_raw:
        return _error("Please enter the moisture percentage.")
    try:
        moisture = float(moisture_raw)
        if moisture < 0:
            raise ValueError
    except (TypeError, ValueError):
        return _error("Please enter a valid moisture percentage.")
    try:
        chambers = detect_and_crop(upload.read(), ROOT / "config/strip_config.json")
        prediction = PredictionService(ROOT / "models")
        reference = ReferenceService(ROOT / "dataset")
        status = StatusService(ROOT / "config/status_ranges.json")
        results = {}
        ph_acid = chambers["ph_acid"]
        ph_alkaline = chambers["ph_alkaline"]
        ph_height = min(ph_acid.shape[0], ph_alkaline.shape[0])
        ph_acid = cv2.resize(ph_acid, (ph_acid.shape[1], ph_height), interpolation=cv2.INTER_AREA)
        ph_alkaline = cv2.resize(ph_alkaline, (ph_alkaline.shape[1], ph_height), interpolation=cv2.INTER_AREA)
        ph_input = (ph_acid, ph_alkaline)
        for parameter, unit, chamber in (("ph", "pH", ph_input), ("ammonia", "ppm", chambers["ammonia"]), ("protein", "%", chambers["protein"])):
            value = prediction.predict(parameter, chamber)
            fields = _reference_fields(parameter, value, reference)
            results[parameter] = _result(value, unit, parameter, status.status(parameter, value), fields)
        moisture_status = status.status("moisture", moisture)
        moisture_fields = status.details("moisture", moisture_status)
        results["moisture"] = _result(moisture, "%", "moisture", moisture_status, {**moisture_fields, "input_method": "manual"})
        results["overall"] = calculate_overall({name: results[name] for name in ("ph", "ammonia", "protein", "moisture")})
    except StripLayoutError as exc:
        return _error(str(exc))
    except (ModelUnavailableError, PredictionError, ReferenceDataError, StatusConfigurationError) as exc:
        return _error(str(exc), 503)
    except Exception:
        app.logger.exception("Analysis failed")
        return _error("Analysis could not be completed. Please try again.", 500)
    record = {"created_at": datetime.now(timezone.utc).isoformat(), "input_method": input_method, **results}
    history = _load_history()
    history.append(record)
    _save_history(history)
    return jsonify({"results": results, "input_method": input_method, "created_at": record["created_at"], "strip_debug": get_last_detection_debug()})


@app.get("/api/history")
def history():
    return jsonify(_load_history())


@app.post("/api/report")
def report():
    payload = request.get_json(silent=True) or {}
    results = payload.get("results")
    language = payload.get("language", "en")
    if not results or "overall" not in results:
        return _error("No completed analysis result was provided.")
    output = ROOT / "reports" / "feedsense-report.pdf"
    font_name = "Helvetica"
    labels = {"ph": "pH", "ammonia": "Ammonia", "protein": "Protein", "moisture": "Moisture", "condition": "Condition", "problem": "Problem", "remedy": "Remedy", "overall": "Overall quality", "reason": "Reason", "input": "Input method"}
    if language == "ta":
        tamil_font = Path("C:/Windows/Fonts/Nirmala.ttf")
        if not tamil_font.exists():
            return _error("Tamil PDF font is not available on this Windows device.", 503)
        pdfmetrics.registerFont(TTFont("Nirmala", str(tamil_font)))
        font_name = "Nirmala"
        labels = {"ph": "pH", "ammonia": "அமோனியா", "protein": "புரதம்", "moisture": "ஈரப்பதம்", "condition": "நிலை", "problem": "பிரச்சினை", "remedy": "தீர்வு", "overall": "மொத்த தரம்", "reason": "காரணம்", "input": "உள்ளீட்டு முறை"}
    pdf = canvas.Canvas(str(output), pagesize=A4)
    text = pdf.beginText(48, 800)
    text.setFont(font_name, 11)
    text.textLine("FeedSense AI - தீவன தர அறிக்கை" if language == "ta" else "FeedSense AI - Feed Quality Report")
    text.textLine(("தேதி/நேரம்: " if language == "ta" else "Date/time: ") + datetime.now().strftime("%Y-%m-%d %H:%M"))
    text.textLine("")
    for name in ("ph", "ammonia", "protein", "moisture"):
        item = results.get(name, {})
        text.textLine(f"{labels[name]}: {item.get('value', 'Unavailable')} {item.get('unit', '')} - {item.get('status', 'Unavailable')}")
        for field in ("condition", "problem", "remedy"):
            if item.get(field):
                text.textLine(f"  {labels[field]}: {item[field]}")
        if item.get("input_method"):
            text.textLine(f"  {labels['input']}: {item['input_method']}")
    text.textLine("")
    text.textLine(f"{labels['overall']}: {results['overall'].get('status', 'Unavailable')}")
    text.textLine(f"{labels['reason']}: {results['overall'].get('reason', '')}")
    pdf.drawText(text)
    pdf.save()
    return send_file(output, as_attachment=True, download_name="feedsense-report.pdf")


if __name__ == "__main__":
    app.run(debug=True)
