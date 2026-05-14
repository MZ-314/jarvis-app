# backend/app/blueprints/tools/__init__.py

from flask import Blueprint

tools_bp = Blueprint("tools", __name__)

from . import routes  # noqa: E402, F401