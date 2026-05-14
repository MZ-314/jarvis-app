# backend/app/models/conversation.py

from datetime import datetime, timezone
from app.extensions import db


class Conversation(db.Model):
    __tablename__ = "conversations"

    # ── Primary key ───────────────────────────────────────────────────────────
    id          = db.Column(db.Integer, primary_key=True)

    # ── Foreign key ───────────────────────────────────────────────────────────
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                            nullable=False, index=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    title       = db.Column(db.String(255), nullable=True)   # auto-generated summary
    mode        = db.Column(
                    db.Enum("voice", "text", name="conversation_mode"),
                    nullable=False,
                    default="voice",
                )
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    is_pinned   = db.Column(db.Boolean, nullable=False, default=False)
    is_deleted  = db.Column(db.Boolean, nullable=False, default=False)

    # ── Summary (populated by Celery summarisation task) ─────────────────────
    summary            = db.Column(db.Text, nullable=True)
    summary_updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Token tracking (for Groq free tier awareness) ─────────────────────────
    total_tokens = db.Column(db.Integer, nullable=False, default=0)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at  = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc),
                            nullable=False)
    updated_at  = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc),
                            nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user     = db.relationship("User", back_populates="conversations")
    messages = db.relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="Message.created_at.asc()",  # always chronological
    )

    # ── Serialiser ────────────────────────────────────────────────────────────
    def to_dict(self, include_messages: bool = False) -> dict:
        data = {
            "id":           self.id,
            "user_id":      self.user_id,
            "title":        self.title,
            "mode":         self.mode,
            "is_archived":  self.is_archived,
            "is_pinned":    self.is_pinned,
            "is_deleted":   self.is_deleted,
            "summary":      self.summary,
            "total_tokens": self.total_tokens,
            "created_at":   self.created_at.isoformat(),
            "updated_at":   self.updated_at.isoformat(),
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data

    def __repr__(self) -> str:
        return f"<Conversation {self.id} user={self.user_id} mode={self.mode}>"