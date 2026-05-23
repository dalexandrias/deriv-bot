"""Painel Visão Geral — tela consolidada de status, mercado, sinal ativo e mini-log."""
from collections import deque
from datetime import datetime, timezone, timedelta
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from rich.text import Text


_BRT = timedelta(hours=-3)


def _now_brt() -> datetime:
    return datetime.now(timezone.utc).astimezone(timezone(_BRT))


def _fmt_rsi(v: float) -> Text:
    arrow = " ▲" if v > 70 else " ▼" if v < 30 else ""
    style = "red" if v > 70 else "green" if v < 30 else "white"
    return Text(f"{v:.1f}{arrow}", style=style)


def _fmt_pos(v: str, green_val: str = "acima", red_val: str = "abaixo") -> Text:
    style = "green" if v == green_val else "red" if v == red_val else "white"
    return Text(v, style=style)


def _fmt_macd(hist: float) -> Text:
    style = "green" if hist > 0 else "red"
    return Text(f"{hist:+.3f}", style=style)


def _fmt_adx(v: float) -> Text:
    style = "yellow" if v > 25 else "dim" if v < 20 else "white"
    suffix = " ★" if v > 25 else ""
    return Text(f"{v:.1f}{suffix}", style=style)


def _build_market_block(title: str, ind: dict) -> Text:
    t = Text()
    t.append(f"{title}\n", style="bold dim")
    t.append("RSI    ", style="cyan dim")
    t.append_text(_fmt_rsi(ind.get("rsi", 0)))
    t.append("\n")
    t.append("BB     ", style="cyan dim")
    bb = ind.get("bb_position", "?")
    bb_s = "red" if bb == "acima" else "green" if bb == "abaixo" else "white"
    t.append(bb, style=bb_s)
    t.append("\n")
    t.append("EMA50  ", style="cyan dim")
    ema = ind.get("price_vs_ema50", "?")
    t.append_text(_fmt_pos(ema))
    t.append("\n")
    t.append("MACD   ", style="cyan dim")
    t.append_text(_fmt_macd(ind.get("macd_histogram", 0)))
    t.append("\n")
    t.append("ADX    ", style="cyan dim")
    t.append_text(_fmt_adx(ind.get("adx", 0)))
    t.append("\n")
    t.append("ATR    ", style="cyan dim")
    t.append(f"{ind.get('atr_pct', 0):.2f}%", style="white")
    return t


def _build_pre_block(pre: dict) -> Text:
    t = Text()
    t.append("PRÉ-ANÁLISE\n", style="bold dim")
    regime = pre.get("regime", "?")
    regime_s = "yellow" if regime == "TREND" else "dim"
    t.append("Regime      ", style="cyan dim")
    t.append(regime, style=regime_s)
    t.append("\n")
    window = pre.get("time_window", {}).get("window", "?")
    win_s = "green" if window == "FAVORÁVEL" else "red"
    t.append("Janela      ", style="cyan dim")
    t.append(window, style=win_s)
    t.append("\n")
    bias = pre.get("m15_bias", {}).get("bias", "?")
    bias_s = "green" if bias == "BULLISH" else "red" if bias == "BEARISH" else "white"
    t.append("Viés M15    ", style="cyan dim")
    t.append(bias, style=bias_s)
    t.append("\n")
    conf = pre.get("confluence", {})
    c_calls = conf.get("call_signals", 0)
    c_puts = conf.get("put_signals", 0)
    t.append("Confluência ", style="cyan dim")
    t.append(f"C{c_calls} P{c_puts}", style="white")
    t.append("\n")
    strat = pre.get("suggested_strategy", "?")
    t.append("Estratégia  ", style="cyan dim")
    t.append(strat, style="cyan")
    return t


class OverviewPanel(Vertical):
    """Tela consolidada: status bar + mercado + pré-análise + sinal ativo + mini-log."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._log_buf: deque[Text] = deque(maxlen=8)
        self._uptime = "00:00:00"
        self._last_signal_text = "–"
        self._win_rate = 0.0
        self._status = "Desconectado"
        self._status_style = "red"

    def compose(self):
        yield Static("", id="overview-status-bar")
        with Horizontal(id="overview-market-row"):
            yield Static("", id="overview-m5")
            yield Static("", id="overview-m15")
            yield Static("", id="overview-preanalysis")
        with Horizontal(id="overview-bottom-row"):
            yield Static("Aguardando sinal…", id="overview-signal")
            yield Static("", id="overview-minilog")

    # ── Status ────────────────────────────────────────────────────────────

    def update_status_bar(self, status: str, style: str, uptime: str,
                          last_signal: str, win_rate: float) -> None:
        self._uptime = uptime
        self._last_signal_text = last_signal
        self._win_rate = win_rate
        self._status = status
        self._status_style = style
        self._render_status_bar()

    def _render_status_bar(self) -> None:
        t = Text()
        t.append("● ", style=self._status_style)
        t.append(self._status, style=self._status_style)
        t.append("    UPTIME ", style="dim")
        t.append(self._uptime, style="white")
        t.append("    ÚLTIMO ", style="dim")
        t.append(self._last_signal_text, style="white")
        t.append("    WIN RATE ", style="dim")
        wr_s = "green" if self._win_rate >= 0.6 else "yellow" if self._win_rate >= 0.5 else "red"
        t.append(f"{self._win_rate:.1%}", style=wr_s)
        self.query_one("#overview-status-bar", Static).update(t)

    def update_uptime(self, uptime: str) -> None:
        self._uptime = uptime
        self._render_status_bar()

    def update_win_rate(self, win_rate: float) -> None:
        self._win_rate = win_rate
        self._render_status_bar()

    def set_status(self, status: str, style: str) -> None:
        self._status = status
        self._status_style = style
        self._render_status_bar()

    # ── Mercado ───────────────────────────────────────────────────────────

    def update_market(self, m5: dict, m15: dict, pre: dict) -> None:
        self.query_one("#overview-m5", Static).update(_build_market_block("MERCADO M5", m5))
        self.query_one("#overview-m15", Static).update(_build_market_block("MERCADO M15", m15))
        self.query_one("#overview-preanalysis", Static).update(_build_pre_block(pre))

    # ── Sinal ativo ───────────────────────────────────────────────────────

    def update_active_signal(self, signal=None) -> None:
        widget = self.query_one("#overview-signal", Static)
        if signal is None:
            widget.update(Text("Sem sinal ativo", style="dim"))
            return

        direction = getattr(signal, "direction", "?")
        conf = getattr(signal, "confidence", 0)
        sig_id = getattr(signal, "id", "?")
        entry_str = getattr(signal, "entry_candle_time", "")
        duration = getattr(signal, "duration", 300)

        dir_s = "green" if direction == "CALL" else "red"
        conf_pct = int(conf * 100)

        try:
            entry_dt = datetime.fromisoformat(entry_str.replace("Z", "+00:00"))
            entry_brt = entry_dt.astimezone(timezone(_BRT))
            entry_fmt = entry_brt.strftime("%H:%M")
            elapsed = int((datetime.now(timezone.utc) - entry_dt.astimezone(timezone.utc)).total_seconds())
            remaining = max(0, duration - elapsed)
            bar_filled = min(10, int((elapsed / duration) * 10)) if duration else 0
            bar = "▓" * bar_filled + "░" * (10 - bar_filled)
        except Exception:
            entry_fmt = "?"
            remaining = 0
            bar = "░" * 10

        t = Text()
        t.append("SINAL ATIVO\n", style="bold dim")
        t.append(f"#{sig_id} ", style="dim")
        t.append(direction, style=dir_s)
        t.append(f" {conf_pct}%", style="white")
        t.append(f"  entry {entry_fmt}", style="dim")
        t.append(f"\n{bar} ", style="cyan")
        t.append(f"{remaining}s restantes", style="dim")

        widget.update(t)

    # ── Mini-log ──────────────────────────────────────────────────────────

    def add_log(self, level: str, time_str: str, name: str, message: str) -> None:
        level_s = {"DEBUG": "dim", "INFO": "white", "WARNING": "yellow", "ERROR": "red"}.get(level, "white")
        truncated = message[:60] + "…" if len(message) > 60 else message
        line = Text()
        line.append(f"{time_str:8} ", style="dim")
        line.append(f"{level:5} ", style=level_s)
        line.append(truncated)
        self._log_buf.append(line)
        self._render_minilog()

    def _render_minilog(self) -> None:
        t = Text()
        t.append("LOGS RECENTES\n", style="bold dim")
        for line in self._log_buf:
            t.append_text(line)
            t.append("\n")
        self.query_one("#overview-minilog", Static).update(t)
