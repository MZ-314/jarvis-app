# backend/app/middleware/auth_guard.py

import logging
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

from app.models import User

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _err(msg: str, status: int):
    return jsonify({"success": False, "error": msg}), status


# ── core guard ────────────────────────────────────────────────────────────────

def jwt_required_with_user(fn):
    """
    Drop-in replacement for @jwt_required() that also:
    - Loads the User row from Postgres
    - Attaches it to Flask's g.current_user
    - Rejects deleted / inactive accounts immediately
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as exc:
            logger.debug("JWT verification failed: %s", exc)
            return _err("Missing or invalid token", 401)

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return _err("Account not found", 401)

        if not user.is_active:
            return _err("Account is deactivated", 403)

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


# ── role / permission guard ───────────────────────────────────────────────────

def require_role(*roles: str):
    """
    Usage:
        @require_role("admin")
        @require_role("admin", "moderator")

    Must be applied AFTER @jwt_required_with_user so g.current_user exists.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user: User = getattr(g, "current_user", None)
            if user is None:
                return _err("Authentication required", 401)

            user_role = getattr(user, "role", "user")
            if user_role not in roles:
                logger.warning(
                    "Role check failed: user %s has role '%s', required %s",
                    user.id, user_role, roles,
                )
                return _err("Insufficient permissions", 403)

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── ownership guard ───────────────────────────────────────────────────────────

def require_ownership(model, id_param: str = "id", user_field: str = "user_id"):
    """
    Verifies that the authenticated user owns the requested resource.

    Usage:
        @require_ownership(Conversation, id_param="conversation_id")

    Fetches model by request view-arg `id_param`, checks row.<user_field> == g.current_user.id.
    Attaches the fetched object to g.owned_object for use in the route.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user: User = getattr(g, "current_user", None)
            if user is None:
                return _err("Authentication required", 401)

            resource_id = kwargs.get(id_param) or request.view_args.get(id_param)
            if not resource_id:
                return _err(f"Missing route parameter: {id_param}", 400)

            obj = model.query.get(resource_id)
            if not obj:
                return _err("Resource not found", 404)

            owner_id = getattr(obj, user_field, None)
            if str(owner_id) != str(user.id):
                logger.warning(
                    "Ownership check failed: user %s tried to access %s %s owned by %s",
                    user.id, model.__name__, resource_id, owner_id,
                )
                return _err("Access denied", 403)

            g.owned_object = obj
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── optional auth (sets g.current_user if token present, else None) ───────────

def optional_jwt(fn):
    """
    For public endpoints that behave differently when a valid token is present
    (e.g. returning personalised vs anonymous data).
    Never raises 401 — sets g.current_user = None if no/invalid token.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            g.current_user = User.query.get(user_id) if user_id else None
        except Exception:
            g.current_user = None
        return fn(*args, **kwargs)
    return wrapper


# ── request context helpers ───────────────────────────────────────────────────

def get_current_user() -> "User | None":
    """Convenience accessor for g.current_user anywhere in a request context."""
    return getattr(g, "current_user", None)


def get_jwt_claims() -> dict:
    """Returns the full JWT payload dict (empty dict if no token in context)."""
    try:
        return get_jwt()
    except Exception:
        return {}