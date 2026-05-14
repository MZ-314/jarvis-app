# backend/app/blueprints/tools/routes.py

import httpx
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import tools_bp

# ── helpers ──────────────────────────────────────────────────────────────────

def _ok(data: dict, status: int = 200):
    return jsonify({"success": True, **data}), status

def _err(msg: str, status: int = 400):
    return jsonify({"success": False, "error": msg}), status

# ── web search (via DuckDuckGo Instant Answer API — no key needed) ────────────

@tools_bp.route("/search", methods=["POST"])
@jwt_required()
def web_search():
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return _err("query is required")

    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1,
            "skip_disambig": 1,
        }
        with httpx.Client(timeout=8.0) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        results = {
            "abstract": data.get("Abstract", ""),
            "abstract_source": data.get("AbstractSource", ""),
            "abstract_url": data.get("AbstractURL", ""),
            "answer": data.get("Answer", ""),
            "answer_type": data.get("AnswerType", ""),
            "related": [
                {"text": t.get("Text", ""), "url": t.get("FirstURL", "")}
                for t in (data.get("RelatedTopics") or [])
                if isinstance(t, dict) and t.get("Text")
            ][:5],
        }
        return _ok({"query": query, "results": results})

    except httpx.TimeoutException:
        return _err("Search request timed out", 504)
    except Exception as e:
        current_app.logger.error("web_search error: %s", e)
        return _err("Search failed", 500)

# ── unit converter ────────────────────────────────────────────────────────────

CONVERSIONS: dict[str, dict[str, float]] = {
    # length → base: metre
    "metre": 1.0, "meter": 1.0, "m": 1.0,
    "kilometre": 1e3, "kilometer": 1e3, "km": 1e3,
    "centimetre": 1e-2, "centimeter": 1e-2, "cm": 1e-2,
    "millimetre": 1e-3, "millimeter": 1e-3, "mm": 1e-3,
    "mile": 1609.344, "miles": 1609.344,
    "yard": 0.9144, "yards": 0.9144, "yd": 0.9144,
    "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
    "inch": 0.0254, "inches": 0.0254, "in": 0.0254,
    # mass → base: kilogram
    "kilogram": 1.0, "kg": 1.0,
    "gram": 1e-3, "g": 1e-3,
    "milligram": 1e-6, "mg": 1e-6,
    "pound": 0.453592, "pounds": 0.453592, "lb": 0.453592, "lbs": 0.453592,
    "ounce": 0.0283495, "ounces": 0.0283495, "oz": 0.0283495,
    "tonne": 1e3, "ton": 907.185,
    # volume → base: litre
    "litre": 1.0, "liter": 1.0, "l": 1.0,
    "millilitre": 1e-3, "milliliter": 1e-3, "ml": 1e-3,
    "gallon": 3.78541, "gallons": 3.78541,
    "quart": 0.946353, "quarts": 0.946353,
    "pint": 0.473176, "pints": 0.473176,
    "cup": 0.24, "cups": 0.24,
    "fluid ounce": 0.0295735, "fl oz": 0.0295735,
    # speed → base: m/s
    "m/s": 1.0, "metre per second": 1.0,
    "km/h": 1 / 3.6, "kph": 1 / 3.6,
    "mph": 0.44704, "miles per hour": 0.44704,
    "knot": 0.514444, "knots": 0.514444,
}

TEMP_UNITS = {"celsius", "c", "fahrenheit", "f", "kelvin", "k"}

def _convert_temp(value: float, from_u: str, to_u: str) -> float:
    # normalise to celsius first
    if from_u in ("fahrenheit", "f"):
        c = (value - 32) * 5 / 9
    elif from_u in ("kelvin", "k"):
        c = value - 273.15
    else:
        c = value
    if to_u in ("fahrenheit", "f"):
        return c * 9 / 5 + 32
    elif to_u in ("kelvin", "k"):
        return c + 273.15
    return c

@tools_bp.route("/convert", methods=["POST"])
@jwt_required()
def unit_convert():
    body = request.get_json(silent=True) or {}
    try:
        value = float(body["value"])
    except (KeyError, TypeError, ValueError):
        return _err("value must be a number")

    from_u = str(body.get("from", "")).strip().lower()
    to_u   = str(body.get("to",   "")).strip().lower()
    if not from_u or not to_u:
        return _err("from and to units are required")

    # temperature branch
    if from_u in TEMP_UNITS or to_u in TEMP_UNITS:
        if from_u not in TEMP_UNITS or to_u not in TEMP_UNITS:
            return _err("Cannot mix temperature with non-temperature units")
        result = _convert_temp(value, from_u, to_u)
        return _ok({"value": value, "from": from_u, "to": to_u, "result": round(result, 6)})

    # general conversion
    if from_u not in CONVERSIONS:
        return _err(f"Unknown unit: {from_u}")
    if to_u not in CONVERSIONS:
        return _err(f"Unknown unit: {to_u}")

    base   = value * CONVERSIONS[from_u]
    result = base / CONVERSIONS[to_u]
    return _ok({"value": value, "from": from_u, "to": to_u, "result": round(result, 6)})

# ── code snippet executor stub ────────────────────────────────────────────────
# Real sandboxed execution is deferred (needs a secure runner).
# Returns a structured stub so the mobile client can render the UI now.

@tools_bp.route("/execute", methods=["POST"])
@jwt_required()
def execute_code():
    body     = request.get_json(silent=True) or {}
    language = str(body.get("language", "python")).strip().lower()
    code     = str(body.get("code", "")).strip()

    if not code:
        return _err("code is required")

    supported = {"python", "javascript", "bash"}
    if language not in supported:
        return _err(f"Supported languages: {', '.join(supported)}")

    # Stub — replace with Piston API or Judge0 integration later
    return _ok({
        "language": language,
        "code": code,
        "output": None,
        "error": None,
        "status": "sandbox_not_configured",
        "message": "Code execution sandbox is not yet configured. Integrate Piston or Judge0.",
    }, 202)

# ── engineering formula resolver ──────────────────────────────────────────────

import math

FORMULAS: dict[str, dict] = {
    "ohms_law_voltage": {
        "description": "V = I × R",
        "params": ["current_A", "resistance_ohm"],
        "fn": lambda p: p["current_A"] * p["resistance_ohm"],
        "unit": "V",
    },
    "ohms_law_current": {
        "description": "I = V / R",
        "params": ["voltage_V", "resistance_ohm"],
        "fn": lambda p: p["voltage_V"] / p["resistance_ohm"],
        "unit": "A",
    },
    "ohms_law_resistance": {
        "description": "R = V / I",
        "params": ["voltage_V", "current_A"],
        "fn": lambda p: p["voltage_V"] / p["current_A"],
        "unit": "Ω",
    },
    "power_electrical": {
        "description": "P = V × I",
        "params": ["voltage_V", "current_A"],
        "fn": lambda p: p["voltage_V"] * p["current_A"],
        "unit": "W",
    },
    "kinetic_energy": {
        "description": "KE = 0.5 × m × v²",
        "params": ["mass_kg", "velocity_ms"],
        "fn": lambda p: 0.5 * p["mass_kg"] * p["velocity_ms"] ** 2,
        "unit": "J",
    },
    "potential_energy": {
        "description": "PE = m × g × h",
        "params": ["mass_kg", "height_m"],
        "fn": lambda p: p["mass_kg"] * 9.81 * p["height_m"],
        "unit": "J",
    },
    "force_newtons": {
        "description": "F = m × a",
        "params": ["mass_kg", "acceleration_ms2"],
        "fn": lambda p: p["mass_kg"] * p["acceleration_ms2"],
        "unit": "N",
    },
    "stress": {
        "description": "σ = F / A",
        "params": ["force_N", "area_m2"],
        "fn": lambda p: p["force_N"] / p["area_m2"],
        "unit": "Pa",
    },
    "reynolds_number": {
        "description": "Re = (ρ × v × L) / μ",
        "params": ["density_kgm3", "velocity_ms", "length_m", "dynamic_viscosity_Pas"],
        "fn": lambda p: (p["density_kgm3"] * p["velocity_ms"] * p["length_m"]) / p["dynamic_viscosity_Pas"],
        "unit": "dimensionless",
    },
    "capacitor_energy": {
        "description": "E = 0.5 × C × V²",
        "params": ["capacitance_F", "voltage_V"],
        "fn": lambda p: 0.5 * p["capacitance_F"] * p["voltage_V"] ** 2,
        "unit": "J",
    },
}

@tools_bp.route("/formulas", methods=["GET"])
@jwt_required()
def list_formulas():
    return _ok({
        "formulas": [
            {"id": k, "description": v["description"], "params": v["params"], "unit": v["unit"]}
            for k, v in FORMULAS.items()
        ]
    })

@tools_bp.route("/formulas/<formula_id>", methods=["POST"])
@jwt_required()
def run_formula(formula_id: str):
    if formula_id not in FORMULAS:
        return _err(f"Unknown formula: {formula_id}. GET /tools/formulas for the list.", 404)

    formula = FORMULAS[formula_id]
    body    = request.get_json(silent=True) or {}

    params: dict[str, float] = {}
    missing = []
    for p in formula["params"]:
        if p not in body:
            missing.append(p)
        else:
            try:
                params[p] = float(body[p])
            except (TypeError, ValueError):
                return _err(f"Parameter '{p}' must be a number")

    if missing:
        return _err(f"Missing parameters: {', '.join(missing)}")

    try:
        result = formula["fn"](params)
        if not math.isfinite(result):
            return _err("Result is not finite (division by zero or overflow)")
    except ZeroDivisionError:
        return _err("Division by zero in formula")
    except Exception as e:
        current_app.logger.error("Formula %s error: %s", formula_id, e)
        return _err("Formula evaluation failed", 500)

    return _ok({
        "formula": formula_id,
        "description": formula["description"],
        "inputs": params,
        "result": round(result, 8),
        "unit": formula["unit"],
    })