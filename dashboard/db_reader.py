"""Wrapper sobre SignalRepository para leitura de dados históricos na UI."""
from signals.repository import SignalRepository
from signals.models import Signal


class DBReader:
    """Wrapper para leitura de dados do SQLite na UI."""

    def __init__(self, db_path: str = "data/signals.db"):
        self.repo = SignalRepository(db_path)

    def get_overall_stats(self) -> dict:
        """Retorna estatísticas gerais de sinais resolvidos."""
        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome='loss' THEN 1 ELSE 0 END) as losses,
                    AVG(confidence) as avg_confidence
                FROM signals
                WHERE status = 'resolved'
            """)
            row = cursor.fetchone()

        total, wins, losses, avg_conf = row
        if total is None or total == 0:
            return {
                "total": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "avg_confidence": 0.0,
            }

        return {
            "total": total,
            "wins": wins or 0,
            "losses": losses or 0,
            "win_rate": round((wins or 0) / total, 2),
            "avg_confidence": round(avg_conf or 0, 2),
        }

    def get_stats_by_field(self, field: str) -> list[dict]:
        """Retorna win rates agrupados por um campo."""
        # Whitelist de campos permitidos
        allowed_fields = {"regime", "strategy", "time_window", "direction"}
        if field not in allowed_fields:
            raise ValueError(f"Campo não permitido: {field}")

        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT
                    COALESCE({field}, 'UNKNOWN') as value,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 2) as win_rate
                FROM signals
                WHERE status = 'resolved'
                GROUP BY {field}
                HAVING total >= 1
                ORDER BY win_rate DESC
            """)
            rows = cursor.fetchall()

        return [
            {
                "value": row["value"],
                "total": row["total"],
                "wins": row["wins"],
                "win_rate": row["win_rate"],
            }
            for row in rows
        ]

    def get_recent_signals(self, limit: int = 20) -> list[Signal]:
        """Retorna sinais recentes (qualquer status)."""
        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM signals
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

        return [self.repo._row_to_signal(row) for row in rows]

    def get_active_signals(self) -> list[Signal]:
        """Retorna sinais pendentes (ativos)."""
        return self.repo.get_pending_alive()

    def get_stats_by_direction(self) -> list[dict]:
        """Retorna win rates por direção (CALL/PUT)."""
        return self.get_stats_by_field("direction")

    def get_stats_by_confidence_bucket(self) -> list[dict]:
        """Retorna win rates por faixa de confiança: 50-60, 60-70, 70-80, 80+."""
        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    CASE
                        WHEN confidence >= 0.80 THEN '80%+'
                        WHEN confidence >= 0.70 THEN '70-79%'
                        WHEN confidence >= 0.60 THEN '60-69%'
                        ELSE '50-59%'
                    END as bucket,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN outcome='win' THEN 1.0 ELSE 0 END) / COUNT(*), 2) as win_rate
                FROM signals
                WHERE status = 'resolved'
                GROUP BY bucket
                ORDER BY bucket
            """)
            rows = cursor.fetchall()

        return [
            {"value": row["bucket"], "total": row["total"], "wins": row["wins"], "win_rate": row["win_rate"]}
            for row in rows
        ]

    def get_stats_by_hour_bucket(self) -> list[dict]:
        """Retorna win rates por janela horária BRT (UTC-3): 00-06, 06-12, 12-18, 18-24."""
        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # SQLite: strftime usa UTC; subtrair 3h para BRT
            cursor.execute("""
                SELECT
                    CASE
                        WHEN CAST(strftime('%H', datetime(created_at, '-3 hours')) AS INTEGER) < 6  THEN '00-06h'
                        WHEN CAST(strftime('%H', datetime(created_at, '-3 hours')) AS INTEGER) < 12 THEN '06-12h'
                        WHEN CAST(strftime('%H', datetime(created_at, '-3 hours')) AS INTEGER) < 18 THEN '12-18h'
                        ELSE '18-24h'
                    END as bucket,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                    ROUND(SUM(CASE WHEN outcome='win' THEN 1.0 ELSE 0 END) / COUNT(*), 2) as win_rate
                FROM signals
                WHERE status = 'resolved'
                GROUP BY bucket
                ORDER BY bucket
            """)
            rows = cursor.fetchall()

        return [
            {"value": row["bucket"], "total": row["total"], "wins": row["wins"], "win_rate": row["win_rate"]}
            for row in rows
        ]

    def get_recent_outcomes(self, n: int = 30) -> list[str]:
        """Retorna lista dos últimos n outcomes: ['W','L','W',...]"""
        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT outcome FROM signals
                WHERE status = 'resolved'
                ORDER BY created_at DESC
                LIMIT ?
            """, (n,))
            rows = cursor.fetchall()

        outcomes = []
        for (outcome,) in reversed(rows):
            outcomes.append("W" if outcome == "win" else "L")
        return outcomes

    def get_current_streak(self) -> tuple[str, int]:
        """Retorna (letra, contagem) do streak atual. Ex: ('L', 3)."""
        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT outcome FROM signals
                WHERE status = 'resolved'
                ORDER BY created_at DESC
                LIMIT 50
            """)
            rows = cursor.fetchall()

        if not rows:
            return ("", 0)

        first = rows[0][0]
        count = 0
        for (outcome,) in rows:
            if outcome == first:
                count += 1
            else:
                break

        letter = "W" if first == "win" else "L"
        return (letter, count)

    def get_signal_count_by_status(self) -> dict:
        """Retorna contagem de sinais por status."""
        import sqlite3

        with sqlite3.connect(self.repo.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    status,
                    COUNT(*) as count
                FROM signals
                GROUP BY status
            """)
            rows = cursor.fetchall()

        return {status: count for status, count in rows}
