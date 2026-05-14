# backend/app/blueprints/memory/__init__.py

from flask import Blueprint

memory_bp = Blueprint("memory", __name__)

from . import routes  # noqa: E402, F401