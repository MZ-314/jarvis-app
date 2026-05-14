# backend/app/models/memory.py

from datetime import datetime, timezone
from app.extensions import db


class Memory(db.Model):
    __tablename__ = "memories"

    # ── Primary key ───────────────────────────────────────────────────────────
    id              = db.Column(db.Integer, primary_key=True)

    # ── Foreign key ───────────────────────────────────────────────────────────
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                                nullable=False, index=True)

    # ── Content ───────────────────────────────────────────────────────────────
    content         = db.Column(db.Text, nullable=False)  # the memory text itself
    summary         = db.Column(db.Text, nullable=True)   # short one-liner for UI

    # ── Classification ────────────────────────────────────────────────────────
    memory_type     = db.Column(
                        db.Enum(
                            "fact",          # user stated something ("I use Python")
                            "preference",    # user preference ("I prefer dark mode")
                            "instruction",   # user told Jarvis to always do X
                            "context",       # background context from a conversation
                            "skill",         # something Jarvis learned user can do
                            name="memory_type"
                        ),
                        nullable=False,
                        default="fact",
                    )

    # ── Importance & recall ───────────────────────────────────────────────────
    importance      = db.Column(db.Float,   nullable=False, default=0.5)  # 0.0 → 1.0
    recall_count    = db.Column(db.Integer, nullable=False, default=0)    # times retrieved
    last_recalled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Vector search reference ───────────────────────────────────────────────
    # The actual embedding lives in Qdrant — this is just the pointer
    qdrant_id       = db.Column(db.String(100), nullable=True, unique=True, index=True)

    # ── Source tracking ───────────────────────────────────────────────────────
    source_conversation_id = db.Column(
                                db.Integer,
                                db.ForeignKey("conversations.id", ondelete="SET NULL"),
                                nullable=True,
                            )
    source_message_id      = db.Column(
                                db.Integer,
                                db.ForeignKey("messages.id", ondelete="SET NULL"),
                                nullable=True,
                            )

    # ── Flags ─────────────────────────────────────────────────────────────────
    is_active       = db.Column(db.Boolean, nullable=False, default=True)   # soft delete
    is_verified     = db.Column(db.Boolean, nullable=False, default=False)  # user confirmed

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at      = db.Column(db.DateTime(timezone=True),
                                default=lambda: datetime.now(timezone.utc),
                                nullable=False)
    updated_at      = db.Column(db.DateTime(timezone=True),
                                default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc),
                                nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user                = db.relationship("User", back_populates="memories")
    source_conversation = db.relationship("Conversation", foreign_keys=[source_conversation_id])
    source_message      = db.relationship("Message",      foreign_keys=[source_message_id])

    # ── Helpers ───────────────────────────────────────────────────────────────
    def mark_recalled(self) -> None:
        """Call this every time the memory is retrieved and injected into a prompt."""
        self.recall_count    += 1
        self.last_recalled_at = datetime.now(timezone.utc)

    # ── Serialiser ────────────────────────────────────────────────────────────
    def to_dict(self, include_source: bool = False) -> dict:
        data = {
            "id":              self.id,
            "user_id":         self.user_id,
            "content":         self.content,
            "summary":         self.summary,
            "memory_type":     self.memory_type,
            "importance":      self.importance,
            "recall_count":    self.recall_count,
            "last_recalled_at": self.last_recalled_at.isoformat()
                                if self.last_recalled_at else None,
            "qdrant_id":       self.qdrant_id,
            "is_active":       self.is_active,
            "is_verified":     self.is_verified,
            "created_at":      self.created_at.isoformat(),
            "updated_at":      self.updated_at.isoformat(),
        }
        if include_source:
            data["source_conversation_id"] = self.source_conversation_id
            data["source_message_id"]      = self.source_message_id
        return data

    def __repr__(self) -> str:
        return f"<Memory {self.id} type={self.memory_type} user={self.user_id}>"