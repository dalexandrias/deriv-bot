from sqlalchemy.ext.asyncio import AsyncSession

from app.signals.repository import SignalRepository
from app.agent import memory_repository as mem
from loguru import logger


async def build_context_block(
    session: AsyncSession, repo: SignalRepository, config: dict
) -> str:
    try:
        parts = []

        cycles = await mem.get_recent_cycles(session, limit=5)
        if cycles:
            cycles.reverse()
            lines = ["## Últimos 5 ciclos (curto prazo)"]
            for i, c in enumerate(cycles):
                offset = i - len(cycles)
                dir_str = c["llm_direction"] or "NONE"
                conf_str = f"{c['llm_confidence']:.0%}" if c["llm_confidence"] is not None else "-"
                regime_str = c.get("regime") or "?"
                window_short = _short_window(c.get("time_window"))
                if c["emitted"]:
                    sig_str = f"→ #{c['signal_id']}"
                elif c.get("skip_reason"):
                    sig_str = f"({c['skip_reason']})"
                else:
                    sig_str = ""
                line = (
                    f"{offset:+d} {c['cycle_number']:04d} "
                    f"{regime_str}/{window_short}  {dir_str:4s} {conf_str:>5s}  {sig_str}"
                )
                lines.append(line)
            lines.append(f"  0 (ciclo atual)")
            parts.append("\n".join(lines))

        lessons = await mem.get_active_lessons(session, limit=5)
        if lessons:
            lines = ["## Lições aprendidas (top 5 ativas)"]
            for l in lessons:
                lines.append(f"- {l['content']}")
            parts.append("\n".join(lines))

        stats = await repo.get_pattern_stats()
        if stats:
            rows = [r for r in stats if (r.get("total") or 0) >= 3]
            if rows:
                rows.sort(key=lambda r: float(r.get("win_rate") or 0))
                top_losses = rows[:3]
                top_wins = [r for r in rows if (r.get("win_rate") or 0) >= 0.6][-3:]
                interesting = top_losses + top_wins

                lines = ["## Stats por padrão (resumo — top extremos)"]
                seen = set()
                for row in interesting:
                    key = (
                        row.get("direction", ""),
                        row.get("rsi_bucket", ""),
                        row.get("adx_bucket", ""),
                        row.get("regime", ""),
                        row.get("time_window", ""),
                    )
                    if key in seen:
                        continue
                    seen.add(key)

                    total = int(row.get("total") or 0)
                    wins = int(row.get("wins") or 0)
                    wr = float(row.get("win_rate") or 0)
                    quality = (
                        "favorável" if wr >= 0.6 else ("desfavorável" if wr < 0.4 else "neutro")
                    )
                    lines.append(
                        f"- {row.get('direction', '?')} | RSI={row.get('rsi_bucket', '?')} "
                        f"ADX={row.get('adx_bucket', '?')} Regime={row.get('regime', '?')} "
                        f"Win={row.get('time_window', '?')}: "
                        f"{wins}/{total} ({wr:.0%}) — {quality}"
                    )
                parts.append("\n".join(lines))

        return "\n\n".join(parts)

    except Exception as e:
        logger.error(f"Failed to build memory context block: {e}")
        return ""


def _short_window(window: str | None) -> str:
    if not window:
        return "?"
    window = window.lower()
    for label, key in [
        ("EU", "europe"), ("US", "us_overlap"), ("LU", "late_us"),
        ("AS", "asia"), ("MD", "midday"),
    ]:
        if key in window:
            return label
    return "OT"
