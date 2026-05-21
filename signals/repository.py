import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from signals.models import Signal
from utils.logger import logger


class SignalRepository:
    """SQLite repository for signals."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at    TEXT NOT NULL,
                symbol        TEXT NOT NULL,
                direction     TEXT NOT NULL,
                confidence    REAL NOT NULL,
                justification TEXT NOT NULL,
                duration      INTEGER NOT NULL,
                timeframe     TEXT NOT NULL,
                rsi           REAL,
                macd_signal   TEXT,
                trend         TEXT,
                bb_position   TEXT,
                quote_entry   REAL,
                quote_exit    REAL,
                outcome       TEXT,
                status        TEXT NOT NULL DEFAULT 'pending'
            )
            """)
            conn.commit()

    def insert(self, signal: Signal) -> int:
        """Insert a signal and return its id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO signals (
                created_at, symbol, direction, confidence, justification,
                duration, timeframe, rsi, macd_signal, trend, bb_position,
                quote_entry, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.created_at, signal.symbol, signal.direction,
                signal.confidence, signal.justification, signal.duration,
                signal.timeframe, signal.rsi, signal.macd_signal,
                signal.trend, signal.bb_position, signal.quote_entry,
                signal.status
            ))
            conn.commit()
            return cursor.lastrowid

    def update_outcome(self, signal_id: int, quote_exit: float, outcome: str) -> None:
        """Update signal with exit price and outcome."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE signals
            SET quote_exit = ?, outcome = ?, status = 'resolved'
            WHERE id = ?
            """, (quote_exit, outcome, signal_id))
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No signal found with id={signal_id}")

    def get_pending_alive(self) -> list[Signal]:
        """Fetch pending signals whose duration hasn't expired yet."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signals WHERE status = 'pending'")
            rows = cursor.fetchall()

        # Calculate expiry in Python
        now = datetime.now(timezone.utc)
        alive = []
        for row in rows:
            created = datetime.fromisoformat(row["created_at"])
            elapsed = (now - created).total_seconds()
            if elapsed < row["duration"]:
                alive.append(self._row_to_signal(row))
        return alive

    def get_pending_expired(self) -> list[Signal]:
        """Fetch pending signals whose duration has expired."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM signals WHERE status = 'pending'")
            rows = cursor.fetchall()

        # Calculate expiry in Python
        now = datetime.now(timezone.utc)
        expired = []
        for row in rows:
            created = datetime.fromisoformat(row["created_at"])
            elapsed = (now - created).total_seconds()
            if elapsed >= row["duration"]:
                expired.append(self._row_to_signal(row))
        return expired

    def mark_aborted(self, signal_id: int) -> None:
        """Mark a signal as aborted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE signals SET status = 'aborted' WHERE id = ?", (signal_id,))
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No signal found with id={signal_id}")

    def get_resolved(self, limit: int = 20, offset: int = 0) -> list[Signal]:
        """Fetch resolved signals for learning block."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM signals
            WHERE status = 'resolved'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
        return [self._row_to_signal(row) for row in rows]

    def get_pattern_stats(self) -> list[dict]:
        """Fetch win rates by pattern (direction, trend, macd_signal)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
            SELECT
                direction,
                trend,
                macd_signal,
                COUNT(*) AS total,
                SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) AS wins,
                ROUND(SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 2) AS win_rate
            FROM signals
            WHERE status = 'resolved'
            GROUP BY direction, trend, macd_signal
            HAVING total >= 3
            ORDER BY win_rate DESC
            """)
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def _row_to_signal(self, row: sqlite3.Row) -> Signal:
        """Convert a database row to a Signal dataclass."""
        return Signal(
            id=row["id"],
            created_at=row["created_at"],
            symbol=row["symbol"],
            direction=row["direction"],
            confidence=row["confidence"],
            justification=row["justification"],
            duration=row["duration"],
            timeframe=row["timeframe"],
            rsi=row["rsi"],
            macd_signal=row["macd_signal"],
            trend=row["trend"],
            bb_position=row["bb_position"],
            quote_entry=row["quote_entry"],
            quote_exit=row["quote_exit"],
            outcome=row["outcome"],
            status=row["status"],
        )
