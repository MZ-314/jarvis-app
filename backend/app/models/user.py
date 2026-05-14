# backend/app/models/user.py

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────────────────
    id         = db.Column(db.Integer, primary_key=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    email      = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # ── Profile ───────────────────────────────────────────────────────────────
    full_name  = db.Column(db.String(120), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)   # Backblaze B2 URL

    # ── Preferences (voice / AI behaviour) ───────────────────────────────────
    voice_id        = db.Column(db.String(100), nullable=True)   # Cartesia voice ID
    system_prompt   = db.Column(db.Text,        nullable=True)   # custom persona
    preferred_lang  = db.Column(db.String(10),  nullable=False, default="en")

    # ── Status ────────────────────────────────────────────────────────────────
    is_active       = db.Column(db.Boolean, nullable=False, default=True)
    is_verified     = db.Column(db.Boolean, nullable=False, default=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at  = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc),
                            nullable=False)
    updated_at  = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc),
                            nullable=False)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    conversations = db.relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",         # use .filter_by() instead of loading all at once
    )
    memories = db.relationship(
        "Memory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # ── Password helpers ──────────────────────────────────────────────────────
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # ── Serialiser ────────────────────────────────────────────────────────────
    def to_dict(self, include_private: bool = False) -> dict:
        data = {
            "id":             self.id,
            "email":          self.email,
            "username":       self.username,
            "full_name":      self.full_name,
            "avatar_url":     self.avatar_url,
            "voice_id":       self.voice_id,
            "preferred_lang": self.preferred_lang,
            "is_verified":    self.is_verified,
            "created_at":     self.created_at.isoformat(),
            "last_seen_at":   self.last_seen_at.isoformat() if self.last_seen_at else None,
        }
        if include_private:
            data["system_prompt"] = self.system_prompt
        return data

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"