# backend/app/models/message.py

from datetime import datetime, timezone
from app.extensions import db


class Message(db.Model):
    __tablename__ = "messages"

    # ── Primary key ───────────────────────────────────────────────────────────
    id              = db.Column(db.Integer, primary_key=True)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                                nullable=False, index=True)

    # ── Role ──────────────────────────────────────────────────────────────────
    role            = db.Column(
                        db.Enum("user", "assistant", "system", name="message_role"),
                        nullable=False,
                    )

    # ── Content ───────────────────────────────────────────────────────────────
    content         = db.Column(db.Text, nullable=False)
    content_type    = db.Column(
                        db.Enum("text", "voice_transcript", "tool_result", name="message_content_type"),
                        nullable=False,
                        default="text",
                    )

    # ── Voice metadata (populated only for voice messages) ───────────────────
    audio_url       = db.Column(db.String(500), nullable=True)  # Backblaze B2
    duration_ms     = db.Column(db.Integer,     nullable=True)  # audio length
    deepgram_confidence = db.Column(db.Float,   nullable=True)  # STT confidence score

    # ── Tool call metadata (populated only for tool_result messages) ──────────
    tool_name       = db.Column(db.String(100), nullable=True)
    tool_input      = db.Column(db.JSON,        nullable=True)
    tool_output     = db.Column(db.JSON,        nullable=True)

    # ── Token tracking ────────────────────────────────────────────────────────
    token_count     = db.Column(db.Integer, nullable=False, default=0)

    # ── Flags ─────────────────────────────────────────────────────────────────
    is_error        = db.Column(db.Boolean, nullable=False, default=False)
    is_hidden       = db.Column(db.Boolean, nullable=False, default=False)  # system messages

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at      = db.Column(db.DateTime(timezone=True),
                                default=lambda: datetime.now(timezone.utc),
                                nullable=False, index=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    conversation    = db.relationship("Conversation", back_populates="messages")
    user            = db.relationship("User")

    # ── Serialiser ────────────────────────────────────────────────────────────
    def to_dict(self, include_tool_data: bool = False) -> dict:
        data = {
            "id":                  self.id,
            "conversation_id":     self.conversation_id,
            "user_id":             self.user_id,
            "role":                self.role,
            "content":             self.content,
            "content_type":        self.content_type,
            "audio_url":           self.audio_url,
            "duration_ms":         self.duration_ms,
            "deepgram_confidence": self.deepgram_confidence,
            "token_count":         self.token_count,
            "is_error":            self.is_error,
            "is_hidden":           self.is_hidden,
            "created_at":          self.created_at.isoformat(),
        }
        if include_tool_data:
            data["tool_name"]   = self.tool_name
            data["tool_input"]  = self.tool_input
            data["tool_output"] = self.tool_output
        return data

    def __repr__(self) -> str:
        return f"<Message {self.id} role={self.role} conv={self.conversation_id}>"