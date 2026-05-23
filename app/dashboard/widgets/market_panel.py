"""Painel de mercado: tabela comparativa M5xM15 + pre-analise + timing."""
from datetime import datetime, timezone, timedelta
from textual.containers import Vertical
from textual.widgets import Static
from rich.table import Table
from rich.text import Text

_BRT = timedelta(hours=-3)


def _tz_brt():
    return timezone(_BRT)


def _rsi_text(v: float) -> Text:
    arrow = " ▲" if v > 70 else " ▼" if v < 30 else ""
    style = "red" if v > 70 else "green" if v < 30 else "white"
    return Text(f"{v:.1f}{arrow}", style=style)


def _pos_text(v: str, green="acima", red="abaixo") -> Text:
    style = "green" if v == green else "red" if v == red else "white"
    arrow = " ↑" if v == green else " ↓" if v == red else ""
    return Text(f"{v}{arrow}", style=style)


def _macd_text(hist: float) -> Text:
    return Text(f"{hist:+.3f}", style="green" if hist > 0 else "red")


def _adx_text(v: float) -> Text:
    suffix = " ★" if v > 25 else ""
    style = "yellow" if v > 25 else "dim" if v < 20 else "white"
    return Text(f"{v:.1f}{suffix}", style=style)


def _conf_bar(call: int, put: int) -> Text:
    max_s = max(call, put, 1)
    call_bar = "▓" * call + "░" * (5 - call)
    put_bar = "▓" * put + "░" * (5 - put)
    t = Text()
    t.append("CALL ", style="green dim")
    t.append(call_bar, style="green")
    t.append(f" {call}  ", style="green")
    t.append("PUT ", style="red dim")
    t.append(put_bar, style="red")
    t.append(f" {put}", style="red")
    return t


class MarketPanel(Vertical):
    """Painel de indicadores de mercado comparativo M5xM15."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_candle_time: str = ""
        self._next_entry_time: str = ""

    def compose(self):
        yield Static("", id="market-comparison")
        yield Static("", id="pre-analysis-section")
        yield Static("", id="timing-section")

    def update_market_data(self, m5: dict, m15: dict, pre: dict,
                           last_candle_time: str = "", next_entry_time: str = "") -> None:
        self._last_candle_time = last_candle_time
        self._next_entry_time = next_entry_time
        self._render_comparison(m5, m15)
        self._render_pre_analysis(pre)
        self._render_timing()

    def _render_comparison(self, m5: dict, m15: dict) -> None:
        table = Table(show_header=True, box=None, padding=(0, 1), expand=True)
        table.add_column("INDICADOR", style="cyan dim", min_width=22)
        table.add_column("M5", min_width=18)
        table.add_column("M15", min_width=18)

        table.add_row("RSI-14", _rsi_text(m5.get("rsi", 0)), _rsi_text(m15.get("rsi", 0)))
        table.add_row("Bollinger",
                      _pos_text(m5.get("bb_position", "?"), "dentro", "fora"),
                      _pos_text(m15.get("bb_position", "?"), "dentro", "fora"))
        table.add_row("vs EMA-50",
                      _pos_text(m5.get("price_vs_ema50", "?")),
                      _pos_text(m15.get("price_vs_ema50", "?")))
        table.add_row("MACD hist",
                      _macd_text(m5.get("macd_histogram", 0)),
                      _macd_text(m15.get("macd_histogram", 0)))
        table.add_row("ADX-14",
                      _adx_text(m5.get("adx", 0)),
                      _adx_text(m15.get("adx", 0)))
        table.add_row("ATR %",
                      Text(f"{m5.get('atr_pct', 0):.2f}%"),
                      Text(f"{m15.get('atr_pct', 0):.2f}%"))

        self.query_one("#market-comparison", Static).update(table)

    def _render_pre_analysis(self, pre: dict) -> None:
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("K", style="cyan dim", min_width=22)
        table.add_column("V")

        table.add_row("PRE-ANALISE", "")

        regime = pre.get("regime", "?")
        table.add_row("Regime", Text(regime, style="yellow" if regime == "TREND" else "dim"))

        window = pre.get("time_window", {}).get("window", "?")
        table.add_row("Janela", Text(window, style="green" if window == "FAVORAVEL" else "red"))

        bias = pre.get("m15_bias", {}).get("bias", "?")
        table.add_row("Vies M15", Text(bias, style="green" if bias == "BULLISH" else "red" if bias == "BEARISH" else "white"))

        conf = pre.get("confluence", {})
        table.add_row("Confluencia", _conf_bar(conf.get("call_signals", 0), conf.get("put_signals", 0)))

        strat = pre.get("suggested_strategy", "?")
        table.add_row("Estrategia", Text(strat, style="cyan"))

        self.query_one("#pre-analysis-section", Static).update(table)

    def _render_timing(self) -> None:
        t = Text()
        t.append("TIMING\n", style="bold dim")

        if self._last_candle_time:
            try:
                dt = datetime.fromisoformat(self._last_candle_time.replace("Z", "+00:00"))
                dt_brt = dt.astimezone(_tz_brt())
                elapsed = int((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds())
                m, s = divmod(elapsed, 60)
                t.append("Ultimo candle M5  ", style="cyan dim")
                t.append(f"{dt_brt.strftime('%H:%M:%S')} (ha {m}m{s:02d}s)\n", style="white")
            except Exception:
                t.append(f"Ultimo candle M5  {self._last_candle_time}\n", style="white")

        if self._next_entry_time:
            try:
                dt = datetime.fromisoformat(self._next_entry_time.replace("Z", "+00:00"))
                dt_brt = dt.astimezone(_tz_brt())
                remaining = int((dt.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds())
                if remaining > 0:
                    m, s = divmod(remaining, 60)
                    t.append("Proxima entrada   ", style="cyan dim")
                    t.append(f"{dt_brt.strftime('%H:%M:%S')} (em {m}m{s:02d}s)", style="green")
                else:
                    t.append("Proxima entrada   ", style="cyan dim")
                    t.append(dt_brt.strftime("%H:%M:%S"), style="yellow")
            except Exception:
                t.append(f"Proxima entrada   {self._next_entry_time}", style="white")

        self.query_one("#timing-section", Static).update(t)

    def on_mount(self) -> None:
        self.set_interval(1, self._render_timing)
