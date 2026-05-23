"""Linha de status fina no topo do dashboard."""
from textual.containers import Horizontal
from textual.widgets import Static
from rich.text import Text


class StatusPanel(Horizontal):
    """Barra de status de 1 linha: dot + status + uptime + ultimo sinal + win rate."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compose(self):
        yield Static("●", id="connection-dot")
        yield Static("Desconectado", id="connection-status")
        yield Static("", id="uptime-counter")
        yield Static("", id="last-signal-info")
        yield Static("", id="win-rate-info")

    _STATUS_MAP = {
        "connected":      ("Conectado",        "green"),
        "connecting":     ("Conectando…",      "yellow"),
        "ready":          ("Pronto",            "green"),
        "waiting":        ("Aguardando candle", "yellow"),
        "analyzing":      ("Analisando",        "cyan"),
        "signal_emitted": ("Sinal emitido",     "green"),
        "idle":           ("Ocioso",            "dim"),
        "error":          ("Erro",              "red"),
    }

    def update_status(self, status: str, detail: str = "") -> None:
        label, color = self._STATUS_MAP.get(status, (status.capitalize(), "white"))
        text = f"{label}: {detail}" if detail else label
        self.query_one("#connection-status", Static).update(Text(text, style=color))
        self.query_one("#connection-dot", Static).update(Text("●", style=color))

    def set_connected(self, connected: bool) -> None:
        self.update_status("connected" if connected else "connecting")

    def update_uptime(self, uptime: str) -> None:
        self.query_one("#uptime-counter", Static).update(
            Text(f"UP {uptime}", style="dim")
        )

    def update_last_update(self, timestamp: str) -> None:
        pass

    def update_last_signal(self, signal_id: int, direction: str, outcome: str = "") -> None:
        if outcome:
            color = "green" if outcome == "WIN" else "red"
            text = f"#{signal_id} {direction} {outcome}"
            style = color
        else:
            text = f"#{signal_id} {direction} pending"
            style = "yellow"
        self.query_one("#last-signal-info", Static).update(Text(text, style=style))

    def update_win_rate(self, win_rate: float) -> None:
        color = "green" if win_rate >= 0.6 else "yellow" if win_rate >= 0.5 else "red"
        self.query_one("#win-rate-info", Static).update(
            Text(f"WR {win_rate:.1%}", style=color)
        )
