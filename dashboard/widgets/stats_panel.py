"""Painel de estatísticas — bloco Geral + 6 quebras em grid 2×3 com barras textuais."""
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from rich.text import Text


def _bar(wins: int, total: int, width: int = 10) -> str:
    if total == 0:
        return "░" * width
    filled = int((wins / total) * width)
    return "▓" * filled + "░" * (width - filled)


def _wr_style(wr: float) -> str:
    return "green" if wr >= 0.6 else "yellow" if wr >= 0.5 else "red"


def _build_breakdown_block(title: str, rows: list[dict]) -> Text:
    t = Text()
    t.append(f"{title}\n", style="bold dim")
    for row in rows:
        label = str(row.get("value", "?"))[:8]
        total = row.get("total", 0)
        wins = row.get("wins", 0)
        wr = row.get("win_rate", 0.0) or 0.0
        bar = _bar(wins, total)
        t.append(f"{label:<10}", style="cyan dim")
        t.append(f"{total:>4} ", style="white")
        t.append(f"{wins:>3}W ", style="green")
        t.append(f"{wr:>4.0%} ", style=_wr_style(wr))
        t.append(bar + "\n", style="cyan")
    return t


class StatsPanel(Vertical):
    """Painel de estatísticas com bloco Geral e 6 quebras."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compose(self):
        yield Static("", id="stats-general")
        with Horizontal(id="stats-grid"):
            yield Static("", id="stats-regime", classes="stats-block")
            yield Static("", id="stats-direction", classes="stats-block")
            yield Static("", id="stats-strategy", classes="stats-block")
            yield Static("", id="stats-conf", classes="stats-block")
            yield Static("", id="stats-hour", classes="stats-block")
            yield Static("", id="stats-recent", classes="stats-block")

    def update_all_stats(
        self,
        overall: dict,
        streak: tuple[str, int],
        by_regime: list[dict],
        by_direction: list[dict],
        by_strategy: list[dict],
        by_conf: list[dict],
        by_hour: list[dict],
        recent_outcomes: list[str],
    ) -> None:
        self._render_general(overall, streak)
        self.query_one("#stats-regime", Static).update(_build_breakdown_block("POR REGIME", by_regime))
        self.query_one("#stats-direction", Static).update(_build_breakdown_block("POR DIREÇÃO", by_direction))
        self.query_one("#stats-strategy", Static).update(_build_breakdown_block("POR ESTRATÉGIA", by_strategy))
        self.query_one("#stats-conf", Static).update(_build_breakdown_block("FAIXA CONFIANÇA", by_conf))
        self.query_one("#stats-hour", Static).update(_build_breakdown_block("HORA BRT", by_hour))
        self._render_recent(recent_outcomes)

    def update_overall_stats(self, stats: dict) -> None:
        self._render_general(stats, ("", 0))

    def update_breakdown_stats(self, breakdown: dict) -> None:
        regime = breakdown.get("regime", [])
        self.query_one("#stats-regime", Static).update(_build_breakdown_block("POR REGIME", regime))

    def _render_general(self, stats: dict, streak: tuple[str, int]) -> None:
        total = stats.get("total", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        wr = stats.get("win_rate", 0.0) or 0.0
        avg_conf = stats.get("avg_confidence", 0.0) or 0.0
        streak_let, streak_n = streak

        wr_s = _wr_style(wr)
        streak_s = "green" if streak_let == "W" else "red" if streak_let == "L" else "dim"

        t = Text()
        t.append("GERAL\n", style="bold dim")
        t.append("TOTAL  ", style="cyan dim")
        t.append(f"{total:<8}", style="white")
        t.append("WINS  ", style="cyan dim")
        t.append(f"{wins:<8}", style="green")
        t.append("LOSSES  ", style="cyan dim")
        t.append(f"{losses:<8}", style="red")
        t.append("WIN RATE  ", style="cyan dim")
        t.append(f"{wr:<8.1%}", style=wr_s)
        t.append("CONF MÉDIA  ", style="cyan dim")
        t.append(f"{avg_conf:<6.0%}", style="white")
        if streak_let:
            t.append("STREAK  ", style="cyan dim")
            t.append(f"{streak_let}{streak_n}", style=streak_s)

        self.query_one("#stats-general", Static).update(t)

    def _render_recent(self, outcomes: list[str]) -> None:
        t = Text()
        t.append("PERFORMANCE RECENTE\n", style="bold dim")

        last10 = outcomes[-10:]
        last50 = outcomes[-50:]

        if last10:
            w10 = last10.count("W")
            wr10 = w10 / len(last10)
            bar10 = _bar(w10, len(last10))
            t.append("Últimos 10  ", style="cyan dim")
            t.append(bar10, style="cyan")
            t.append(f"  {wr10:.0%}\n", style=_wr_style(wr10))

        if last50:
            w50 = last50.count("W")
            wr50 = w50 / len(last50)
            bar50 = _bar(w50, len(last50))
            t.append("Últimos 50  ", style="cyan dim")
            t.append(bar50, style="cyan")
            t.append(f"  {wr50:.0%}\n", style=_wr_style(wr50))

        if outcomes:
            t.append("Sequência   ", style="cyan dim")
            for letter in outcomes[-20:]:
                t.append(letter, style="green" if letter == "W" else "red")
                t.append(" ")

        self.query_one("#stats-recent", Static).update(t)
