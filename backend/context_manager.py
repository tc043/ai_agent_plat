"""
Context Manager for AI Agent Platform & Sandbox.
Manages conversation context windows with token budgeting.
"""

from backend.models import Conversation, ConversationMessage, ContextWindow
from datetime import datetime
import uuid


class ContextManager:
    """Manages conversation context with sliding window and summarization."""

    def __init__(self, max_tokens: int = 4096):
        self.conversations: dict[str, Conversation] = {}
        self.max_tokens = max_tokens

    def get_or_create(self, conversation_id: str | None = None) -> Conversation:
        if conversation_id and conversation_id in self.conversations:
            return self.conversations[conversation_id]
        conv = Conversation(id=conversation_id or str(uuid.uuid4()))
        self.conversations[conv.id] = conv
        return conv

    def add_message(self, conversation_id: str, role: str, content: str, steps=None):
        conv = self.get_or_create(conversation_id)
        msg = ConversationMessage(role=role, content=content, steps=steps or [])
        conv.messages.append(msg)
        conv.context_tokens = self._estimate_tokens(conv)
        # Trim if over budget
        if conv.context_tokens > self.max_tokens:
            self._trim_context(conv)
        return conv

    def get_context(self, conversation_id: str) -> list[dict]:
        conv = self.conversations.get(conversation_id)
        if not conv:
            return []
        return [{"role": "assistant" if m.role == "agent" else m.role, "content": m.content} for m in conv.messages]

    def get_stats(self, conversation_id: str) -> dict:
        conv = self.conversations.get(conversation_id)
        if not conv:
            return {"tokens": 0, "messages": 0, "max_tokens": self.max_tokens}
        return {
            "tokens": conv.context_tokens,
            "messages": len(conv.messages),
            "max_tokens": self.max_tokens,
            "usage_pct": round(conv.context_tokens / self.max_tokens * 100, 1),
        }

    def _estimate_tokens(self, conv: Conversation) -> int:
        return sum(len(m.content.split()) * 1.3 for m in conv.messages).__int__()

    def _trim_context(self, conv: Conversation):
        """Keep system + last N messages within budget."""
        while conv.context_tokens > self.max_tokens and len(conv.messages) > 2:
            removed = conv.messages.pop(0)
            conv.context_tokens = self._estimate_tokens(conv)
            if not conv.metadata.get("summary"):
                conv.metadata["summary"] = f"[Earlier context summarized: {removed.content[:100]}...]"

    def list_conversations(self) -> list[dict]:
        return [
            {"id": c.id, "messages": len(c.messages),
             "tokens": c.context_tokens, "created": c.created_at.isoformat()}
            for c in self.conversations.values()
        ]
