# backend/app/blueprints/auth/utils.py

import re
from datetime import datetime, timezone
from flask_jwt_extended import get_jwt, get_jwt_identity
from app.extensions import db
from app.models import User


# ── Validation helpers ────────────────────────────────────────────────────────

EMAIL_REGEX    = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
PASSWORD_MIN   = 8


def validate_email(email: str) -> str | None:
    """Returns error string or None if valid."""
    if not email:
        return "Email is required."
    if not EMAIL_REGEX.match(email.strip()):
        return "Invalid email format."
    return None


def validate_username(username: str) -> str | None:
    if not username:
        return "Username is required."
    if not USERNAME_REGEX.match(username.strip()):
        return "Username must be 3–30 characters: letters, numbers, underscores only."
    return None


def validate_password(password: str) -> str | None:
    if not password:
        return "Password is required."
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."
    return None


# ── User lookup helpers ───────────────────────────────────────────────────────

def get_user_by_email(email: str) -> User | None:
    return User.query.filter_by(email=email.strip().lower()).first()


def get_user_by_username(username: str) -> User | None:
    return User.query.filter_by(username=username.strip().lower()).first()


def get_current_user() -> User | None:
    """Resolve the JWT identity to a User object."""
    user_id = get_jwt_identity()
    if not user_id:
        return None
    return User.query.get(user_id)


# ── Token helpers ─────────────────────────────────────────────────────────────

def get_jwt_user_id() -> int | None:
    """Safely extract user_id (int) from JWT identity."""
    identity = get_jwt_identity()
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


# ── Activity tracker ──────────────────────────────────────────────────────────

def update_last_seen(user: User) -> None:
    """Stamp last_seen_at on the user row. Call after every authenticated request."""
    user.last_seen_at = datetime.now(timezone.utc)
    db.session.commit()


# ── Response builders ─────────────────────────────────────────────────────────

def auth_error(message: str, status: int = 401) -> tuple:
    return {"success": False, "error": message}, status


def auth_success(data: dict, status: int = 200) -> tuple:
    return {"success": True, **data}, status