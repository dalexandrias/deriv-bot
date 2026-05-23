"""Painel de histórico de sinais com header sumário, coluna Δ e streak no rodapé."""
from datetime import datetime, timezone, timedelta
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable
from textual.binding import Binding
from rich.text import Text

_BRT = timedelta(hours=-3)


class HistoryPanel(Vertical):
    """Histórico com filtros, coluna Δ e streak visual."""

    BINDINGS = [
        Binding("1", "filter_wins", "Só wins"),
        Binding("2", "filter_losses", "Só losses"),
        Binding("3", "filter_aborted", "Só aborted"),
        Binding("0", "filter_all", "Todos"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._all_signals: list = []
        self._filter: str = "all"
        self._streak: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="history-header")
        yield DataTable(id="history-table")
        yield Static("", id="history-streak")

    def on_mount(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.add_column("ID", width=5)
        table.add_column("Hora", width=6)
        table.add_column("Dir", width=4)
        table.add_column("Conf", width=5)
        table.add_column("Regime", width=8)
        table.add_column("Strat", width=8)
        table.add_column("Entrada", width=9)
        table.add_column("Saída", width=9)
        table.add_column("Δ", width=8)
        table.add_column("Res", width=7)

    def update_history(self, signals: list, streak: list[str] | None = None) -> None:
        self._all_signals = signals
        if streak is not None:
            self._streak = streak
        self._refresh_display()

    def _refresh_display(self) -> None:
        signals = self._filtered_signals()
        self._render_header(signals)
        self._render_table(signals)
        self._render_streak()

    def _filtered_signals(self) -> list:
        if self._filter == "wins":
            return [s for s in self._all_signals if s.outcome == "win"]
        if self._filter == "losses":
            return [s for s in self._all_signals if s.outcome == "loss"]
        if self._filter == "aborted":
            return [s for s in self._all_signals if s.status == "aborted"]
        return self._all_signals

    def _render_header(self, signals: list) -> None:
        resolved = [s for s in self._all_signals if s.status == "resolved"]
        total = len(resolved)
        wins = sum(1 for s in resolved if s.outcome == "win")
        losses = sum(1 for s in resolved if s.outcome == "loss")
        wr = wins / total if total else 0.0
        streak_let, streak_n = self._compute_streak()

        wr_s = "green" if wr >= 0.6 else "yellow" if wr >= 0.5 else "red"
        streak_s = "green" if streak_let == "W" else "red" if streak_let == "L" else "dim"

        filt_labels = {"wins": "[1]wins ", "losses": "[2]losses ", "aborted": "[3]aborted ", "all": ""}
        filt = filt_labels.get(self._filter, "")

        t = Text()
        t.append(f"{total} sinais  ", style="dim")
        t.append(f"{wins}W ", style="green")
        t.append("/ ")
        t.append(f"{losses}L  ", style="red")
        t.append(f"{wr:.0%} wr  ", style=wr_s)
        if streak_let:
            t.append("streak ", style="dim")
            t.append(f"{streak_let}{streak_n}", style=streak_s)
        if self._filter != "all":
            t.append(f"  [{self._filter}]", style="cyan")
        t.append("   [0]all [1]wins [2]losses [3]aborted", style="dim")

        self.query_one("#history-header", Static).update(t)

    def _render_table(self, signals: list) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear()

        for signal in signals:
            try:
                dt = datetime.fromisoformat(signal.created_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_brt = dt.astimezone(timezone(_BRT))
                hour = dt_brt.strftime("%H:%M")
            except Exception:
                hour = "?"

            dir_s = "green" if signal.direction == "CALL" else "red"
            direction = Text(signal.direction[0], style=dir_s)

            conf_pct = int(signal.confidence * 100) if signal.confidence else 0

            entry = f"{signal.quote_entry:.1f}" if signal.quote_entry else "-"
            exit_p = f"{signal.quote_exit:.1f}" if signal.quote_exit else "-"

            # Coluna Δ
            if signal.quote_entry and signal.quote_exit:
                delta = signal.quote_exit - signal.quote_entry
                is_win = (signal.direction == "PUT" and delta < 0) or \
                         (signal.direction == "CALL" and delta > 0)
                delta_s = "green" if is_win else "red"
                delta_text = Text(f"{delta:+.1f}", style=delta_s)
            else:
                delta_text = Text("-", style="dim")

            if signal.outcome == "win":
                outcome = Text("WIN", style="green bold")
            elif signal.outcome == "loss":
                outcome = Text("LOSS", style="red bold")
            else:
                outcome = Text(signal.status or "-", style="dim")

            table.add_row(
                str(signal.id),
                hour,
                direction,
                f"{conf_pct}%",
                signal.regime or "-",
                signal.strategy or "-",
                entry,
                exit_p,
                delta_text,
                outcome,
            )

    def _render_streak(self) -> None:
        if not self._streak:
            self.query_one("#history-streak", Static).update("")
            return
        t = Text("Sequência: ", style="dim")
        for letter in self._streak[-30:]:
            t.append(letter, style="green" if letter == "W" else "red")
            t.append(" ")
        self.query_one("#history-streak", Static).update(t)

    def _compute_streak(self) -> tuple[str, int]:
        resolved = [s for s in self._all_signals if s.status == "resolved"]
        if not resolved:
            return ("", 0)
        first = resolved[0].outcome
        count = 0
        for s in resolved:
            if s.outcome == first:
                count += 1
            else:
                break
        return ("W" if first == "win" else "L", count)

    def action_filter_wins(self) -> None:
        self._filter = "wins"
        self._refresh_display()

    def action_filter_losses(self) -> None:
        self._filter = "losses"
        self._refresh_display()

    def action_filter_aborted(self) -> None:
        self._filter = "aborted"
        self._refresh_display()

    def action_filter_all(self) -> None:
        self._filter = "all"
        self._refresh_display()
