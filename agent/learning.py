from signals.repository import SignalRepository
from utils.logger import logger


def build_context_block(repo: SignalRepository, config: dict) -> str:
    """
    Build a learning context block from resolved signals.
    Injects recent signals + pattern statistics into the LLM prompt.
    Returns empty string if no learning history available.
    """
    try:
        # Parse learning_history_size with safe conversion
        try:
            n = int(config.get("learning_history_size", 20))
        except (ValueError, TypeError):
            logger.warning(f"Invalid learning_history_size config, using default 20")
            n = 20

        # Ensure n is positive
        if n <= 0:
            n = 20

        recent = repo.get_resolved(limit=n)

        if not recent:
            return ""  # No learning history yet

        lines = ["## Histórico recente de sinais (últimos resolvidos)"]
        for s in recent:
            # Safe access to outcome with type check
            outcome_str = (s.outcome.upper() if s.outcome and isinstance(s.outcome, str)
                          else "PENDING")

            # Safe access to confidence with type validation
            try:
                confidence = float(s.confidence) if s.confidence is not None else 0.0
            except (ValueError, TypeError):
                logger.warning(f"Invalid confidence for signal #{s.id}: {s.confidence}, using 0.0")
                confidence = 0.0

            lines.append(
                f"- #{s.id} {s.direction} | {outcome_str} "
                f"| RSI={s.rsi} ADX={s.adx} ATR%={s.atr_pct} "
                f"| conf={confidence:.0%}"
            )

        stats = repo.get_pattern_stats()
        if stats:
            lines.append("\n## Taxa de acerto por padrão (n≥5, sinais resolvidos)")
            omitted = 0
            for row in stats:
                # Safe dictionary access with .get() and defaults
                direction = row.get("direction", "UNKNOWN")
                rsi_bucket = row.get("rsi_bucket", "UNKNOWN")
                adx_bucket = row.get("adx_bucket", "UNKNOWN")
                total = row.get("total", 0)
                wins = row.get("wins", 0)
                win_rate = row.get("win_rate", 0.0)

                # Validate numeric values
                try:
                    total = int(total) if total is not None else 0
                    wins = int(wins) if wins is not None else 0
                    win_rate = float(win_rate) if win_rate is not None else 0.0
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid stats row (direction={direction}, rsi_bucket={rsi_bucket}), skipping"
                    )
                    continue

                # Skip patterns with insufficient sample size
                if total < 5:
                    omitted += 1
                    continue

                quality = "favorável" if win_rate >= 0.6 else ("desfavorável" if win_rate < 0.4 else "neutro")
                lines.append(
                    f"- {direction} | RSI={rsi_bucket} ADX={adx_bucket}: "
                    f"{wins}/{total} acertos ({win_rate:.0%}) — {quality}"
                )

            if omitted:
                lines.append(f"({omitted} padrão(ns) com n<5 omitido(s) — sem significância estatística)")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Failed to build learning context block: {e}")
        return ""  # Return empty string on any unexpected error
