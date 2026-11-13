"""Short conversation history for ``mide chat`` (bounded by turns and characters)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChatHistory:
    """Keeps the last ``max_turns`` question/answer pairs within ``max_chars`` characters.

    The budget keeps the prompt small enough for the ``tiny`` profile context window.
    The most recent turn is always kept; its answer is cut if it alone exceeds the budget.
    """

    max_turns: int = 3
    max_chars: int = 1500
    turns: list[tuple[str, str]] = field(default_factory=list)

    def add(self, question: str, answer: str) -> None:
        """Record a turn, then truncate the history."""
        self.turns.append((question.strip(), answer.strip()))
        self.turns = self.turns[-self.max_turns :] if self.max_turns > 0 else []
        while len(self.turns) > 1 and self._size() > self.max_chars:
            self.turns.pop(0)
        if self.turns and self._size() > self.max_chars:
            q, a = self.turns[0]
            self.turns[0] = (q[: self.max_chars // 2], a[: max(0, self.max_chars - len(q[: self.max_chars // 2]))])

    def _size(self) -> int:
        return sum(len(q) + len(a) for q, a in self.turns)

    def clear(self) -> None:
        self.turns.clear()

    def render(self, language: str = "fr") -> str:
        """Format the history for inclusion in a prompt (empty string if none)."""
        if not self.turns:
            return ""
        q_label, a_label = ("Question", "Réponse") if language != "en" else ("Question", "Answer")
        return "\n".join(f"{q_label}: {q}\n{a_label}: {a}" for q, a in self.turns)
