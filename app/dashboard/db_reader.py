"""Placeholder DB reader for TUI -- will be connected to PostgreSQL later."""
from app.signals.repository import SignalRepository


class DBReader:
    """Placeholder -- TUI stats will be added later via API."""

    def __init__(self):
        self.repo = None  # Not connected in TUI-only mode

    def get_overall_stats(self) -> dict:
        return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "avg_confidence": 0.0}

    def get_stats_by_field(self, field: str) -> list[dict]:
        return []

    def get_recent_signals(self, limit: int = 20) -> list:
        return []

    def get_active_signals(self) -> list:
        return []

    def get_stats_by_direction(self) -> list[dict]:
        return []

    def get_stats_by_confidence_bucket(self) -> list[dict]:
        return []

    def get_stats_by_hour_bucket(self) -> list[dict]:
        return []

    def get_recent_outcomes(self, n: int = 30) -> list[str]:
        return []

    def get_current_streak(self) -> tuple:
        return ("", 0)

    def get_signal_count_by_status(self) -> dict:
        return {}
