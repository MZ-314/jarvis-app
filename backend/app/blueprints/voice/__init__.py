# backend/app/blueprints/voice/__init__.py

from flask import Blueprint

voice_bp = Blueprint("voice", __name__)

from . import routes  # noqa: E402, F401