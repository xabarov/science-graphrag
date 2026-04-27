"""Errors raised by LangGraph agent execution."""


class AgentGraphDeadlineExceeded(TimeoutError):
    """Raised when a single agent turn exceeds the configured wall-clock deadline."""

    def __init__(self, *, timeout_seconds: float, message: str | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message or f"agent graph exceeded {timeout_seconds}s deadline")
