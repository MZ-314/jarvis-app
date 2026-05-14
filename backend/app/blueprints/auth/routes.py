# backend/app/blueprints/auth/routes.py

from flask import request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from app.extensions import db
from app.models import User
from . import auth_bp
from .utils import (
    validate_email,
    validate_username,
    validate_password,
    get_user_by_email,
    get_user_by_username,
    get_current_user,
    update_last_seen,
    auth_error,
    auth_success,
)


# ── POST /api/auth/register ───────────────────────────────────────────────────

@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True)
    if not data:
        return auth_error("Request body must be JSON.", 400)

    email    = (data.get("email")    or "").strip().lower()
    username = (data.get("username") or "").strip().lower()
    password =  data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()

    # Validate fields
    errors = {}
    if err := validate_email(email):       errors["email"]    = err
    if err := validate_username(username): errors["username"] = err
    if err := validate_password(password): errors["password"] = err
    if errors:
        return {"success": False, "errors": errors}, 422

    # Uniqueness checks
    if get_user_by_email(email):
        return auth_error("An account with this email already exists.", 409)
    if get_user_by_username(username):
        return auth_error("This username is already taken.", 409)

    # Create user
    user = User(
        email     = email,
        username  = username,
        full_name = full_name or None,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Issue tokens immediately so user is logged in after register
    access_token  = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return auth_success({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict(),
    }, 201)


# ── POST /api/auth/login ──────────────────────────────────────────────────────

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True)
    if not data:
        return auth_error("Request body must be JSON.", 400)

    identifier = (data.get("email") or data.get("username") or "").strip().lower()
    password   =  data.get("password") or ""

    if not identifier or not password:
        return auth_error("Email/username and password are required.", 400)

    # Accept either email or username
    user = get_user_by_email(identifier) or get_user_by_username(identifier)

    if not user or not user.check_password(password):
        return auth_error("Invalid credentials.", 401)

    if not user.is_active:
        return auth_error("This account has been deactivated.", 403)

    update_last_seen(user)

    access_token  = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return auth_success({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "user":          user.to_dict(),
    })


# ── POST /api/auth/refresh ────────────────────────────────────────────────────

@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity     = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return auth_success({"access_token": access_token})


# ── GET /api/auth/me ──────────────────────────────────────────────────────────

@auth_bp.get("/me")
@jwt_required()
def me():
    user = get_current_user()
    if not user:
        return auth_error("User not found.", 404)

    update_last_seen(user)
    return auth_success({"user": user.to_dict(include_private=True)})


# ── PATCH /api/auth/me ────────────────────────────────────────────────────────

@auth_bp.patch("/me")
@jwt_required()
def update_me():
    user = get_current_user()
    if not user:
        return auth_error("User not found.", 404)

    data = request.get_json(silent=True)
    if not data:
        return auth_error("Request body must be JSON.", 400)

    # Only allow safe fields to be updated
    allowed = ["full_name", "voice_id", "system_prompt", "preferred_lang"]
    for field in allowed:
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return auth_success({"user": user.to_dict(include_private=True)})


# ── POST /api/auth/change-password ───────────────────────────────────────────

@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    user = get_current_user()
    if not user:
        return auth_error("User not found.", 404)

    data = request.get_json(silent=True)
    if not data:
        return auth_error("Request body must be JSON.", 400)

    current_password = data.get("current_password") or ""
    new_password     = data.get("new_password")     or ""

    if not user.check_password(current_password):
        return auth_error("Current password is incorrect.", 401)

    if err := validate_password(new_password):
        return {"success": False, "errors": {"new_password": err}}, 422

    user.set_password(new_password)
    db.session.commit()

    return auth_success({"message": "Password updated successfully."})


# ── DELETE /api/auth/me ───────────────────────────────────────────────────────

@auth_bp.delete("/me")
@jwt_required()
def delete_account():
    user = get_current_user()
    if not user:
        return auth_error("User not found.", 404)

    data     = request.get_json(silent=True) or {}
    password = data.get("password") or ""

    if not user.check_password(password):
        return auth_error("Password is incorrect.", 401)

    db.session.delete(user)
    db.session.commit()

    return auth_success({"message": "Account deleted."})