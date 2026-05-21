from signals.repository import SignalRepository


def build_context_block(repo: SignalRepository, config: dict) -> str:
    """
    Build a learning context block from resolved signals.
    Injects recent signals + pattern statistics into the LLM prompt.

    Args:
        repo: SignalRepository instance
        config: Configuration dict with "learning_history_size" key

    Returns:
        Formatted string block for LLM injection, or empty string if no history
    """
    n = int(config.get("learning_history_size", 20))
    recent = repo.get_resolved(limit=n)

    if not recent:
        return ""  # No learning history yet

    lines = ["## Histórico recente de sinais (últimos resolvidos)"]
    for s in recent:
        lines.append(
            f"- #{s.id} {s.direction} | {s.outcome.upper() if s.outcome else 'PENDING'} "
            f"| RSI={s.rsi} trend={s.trend} macd={s.macd_signal} "
            f"| conf={s.confidence:.0%}"
        )

    stats = repo.get_pattern_stats()
    if stats:
        lines.append("\n## Taxa de acerto por padrão (sinais resolvidos)")
        for row in stats:
            total = row["total"]
            wins = row["wins"]
            win_rate = row["win_rate"]
            lines.append(
                f"- {row['direction']} | trend={row['trend']} macd={row['macd_signal']}: "
                f"{wins}/{total} acertos ({win_rate:.0%})"
            )

    return "\n".join(lines)
