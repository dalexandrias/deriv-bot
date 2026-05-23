"""Painel de sinais ativos -- feed compacto com barra de progresso textual."""
from datetime import datetime, timezone, timedelta
from textual.containers import Vertical
from textual.widgets import Static
from rich.text import Text

_BRT = timedelta(hours=-3)


def _progress_bar(elapsed: int, duration: int, width: int = 10) -> str:
    if duration <= 0:
        return "░" * width
    ratio = min(1.0, elapsed / duration)
    filled = int(ratio * width)
    return "▓" * filled + "░" * (width - filled)


class ActivePanel(Vertical):
    """Painel de sinais pendentes com feed compacto."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._signals: list = []
        self._next_candle: str = ""

    def compose(self):
        yield Static("", id="active-header")
        yield Vertical(id="active-feed")

    def update_active_signals(self, signals: list, next_candle_time: str = "") -> None:
        self._signals = signals
        self._next_candle = next_candle_time
        self._refresh_display()

    def _refresh_display(self) -> None:
        header = self.query_one("#active-header", Static)
        feed = self.query_one("#active-feed", Vertical)

        count = len(self._signals)
        h = Text()
        h.append("PENDENTES", style="bold dim")
        h.append(f"  {count} ativo{'s' if count != 1 else ''}", style="cyan")
        header.update(h)

        feed.remove_children()

        if not self._signals:
            empty = Text()
            empty.append("Nenhum sinal ativo", style="dim")
            if self._next_candle:
                try:
                    dt = datetime.fromisoformat(self._next_candle.replace("Z", "+00:00"))
                    dt_brt = dt.astimezone(timezone(timedelta(hours=-3)))
                    remaining = int((dt.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds())
                    if remaining > 0:
                        m, s = divmod(remaining, 60)
                        empty.append(f"  --  proximo candle {dt_brt.strftime('%H:%M')} (em {m}m{s:02d}s)", style="dim")
                except Exception:
                    pass
            feed.mount(Static(empty))
            return

        for signal in self._signals:
            direction = getattr(signal, "direction", "?")
            conf = getattr(signal, "confidence", 0)
            sig_id = getattr(signal, "id", "?")
            entry_str = getattr(signal, "entry_candle_time", "")
            duration = getattr(signal, "duration", 300)
            regime = getattr(signal, "regime", "-") or "-"
            strategy = getattr(signal, "strategy", "-") or "-"

            dir_s = "green" if direction == "CALL" else "red"
            conf_pct = int(conf * 100)
            conf_s = "green" if conf_pct >= 70 else "yellow" if conf_pct >= 50 else "red"

            try:
                entry_dt = datetime.fromisoformat(entry_str.replace("Z", "+00:00"))
                entry_brt = entry_dt.astimezone(timezone(_BRT))
                entry_fmt = entry_brt.strftime("%H:%M:%S")
                elapsed = int((datetime.now(timezone.utc) - entry_dt.astimezone(timezone.utc)).total_seconds())
                remaining = max(0, duration - elapsed)
                bar = _progress_bar(elapsed, duration)
            except Exception:
                entry_fmt = "?"
                remaining = 0
                bar = "░" * 10

            t = Text()
            t.append(f"#{sig_id}  ", style="dim")
            t.append(f"{direction:<4} ", style=dir_s)
            t.append(f"{conf_pct}%  ", style=conf_s)
            t.append(f"{regime} • {strategy}  ", style="dim")
            t.append(f"entry {entry_fmt}  ", style="dim")
            t.append(bar, style="cyan")
            rem_s = "yellow" if remaining > 60 else "red" if remaining > 0 else "dim"
            t.append(f"  {remaining}s restantes", style=rem_s)

            feed.mount(Static(t))

    def on_mount(self) -> None:
        self.set_interval(1, self._refresh_display)
