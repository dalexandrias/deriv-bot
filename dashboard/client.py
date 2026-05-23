"""Dashboard TUI para acompanhamento do bot Deriv."""
import asyncio
from datetime import datetime, timezone, timedelta

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane

from dashboard.event_client import AutoReconnectEventClient
from dashboard.db_reader import DBReader
from dashboard.widgets.status_panel import StatusPanel
from dashboard.widgets.overview_panel import OverviewPanel
from dashboard.widgets.market_panel import MarketPanel
from dashboard.widgets.active_panel import ActivePanel
from dashboard.widgets.history_panel import HistoryPanel
from dashboard.widgets.stats_panel import StatsPanel
from dashboard.widgets.log_panel import LogPanel

from events.protocol import Event, EventType

_BRT = timedelta(hours=-3)


class DashboardApp(App):
    """App TUI para dashboard do bot Deriv."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Sair"),
        ("r", "refresh_stats", "Atualizar stats"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_client = AutoReconnectEventClient()
        self.db_reader = DBReader()
        self.start_time = datetime.now(timezone.utc)
        self.last_signal = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusPanel()
        with TabbedContent():
            yield TabPane("Visão Geral", OverviewPanel(), id="tab-overview")
            yield TabPane("Mercado",     MarketPanel(),   id="tab-market")
            yield TabPane("Sinais",      ActivePanel(),   id="tab-active")
            yield TabPane("Histórico",   HistoryPanel(),  id="tab-history")
            yield TabPane("Stats",       StatsPanel(),    id="tab-stats")
            yield TabPane("Logs",        LogPanel(),      id="tab-logs")
        yield Footer()

    def on_mount(self) -> None:
        asyncio.create_task(self._start_event_client())
        self.set_interval(1,  self._update_uptime)
        self.set_interval(5,  self._refresh_active_signals)
        self.set_interval(30, self._refresh_stats)
        asyncio.create_task(self._load_initial_data())

    async def _start_event_client(self) -> None:
        await self.event_client.start_with_reconnect(self._on_event)

    async def _on_event(self, event: Event) -> None:
        if event.type == EventType.STATUS:
            data = event.data
            status = data.get("status", "")
            detail = data.get("detail", "")

            status_panel = self.query_one(StatusPanel)
            if status in ("connected", "ready"):
                status_panel.set_connected(True)
            else:
                status_panel.update_status(status, detail)

            overview = self.query_one(OverviewPanel)
            status_label_map = {
                "connected":      ("Conectado",        "green"),
                "ready":          ("Pronto",            "green"),
                "waiting":        ("Aguardando candle", "yellow"),
                "analyzing":      ("Analisando",        "cyan"),
                "signal_emitted": ("Sinal emitido",     "green"),
                "idle":           ("Ocioso",            "dim"),
                "error":          ("Erro",              "red"),
            }
            label, color = status_label_map.get(status, (status, "white"))
            overview.set_status(label, color)

        elif event.type == EventType.MARKET:
            data = event.data
            m5 = data["m5_indicators"]
            m15 = data["m15_indicators"]
            pre = data["pre_analysis"]
            last_ct = data.get("last_candle_time", "")
            next_et = data.get("next_entry_time", "")

            self.query_one(MarketPanel).update_market_data(m5, m15, pre, last_ct, next_et)
            self.query_one(OverviewPanel).update_market(m5, m15, pre)

        elif event.type == EventType.SIGNAL_EMITTED:
            data = event.data
            self.last_signal = data
            await self._refresh_active_signals()
            self._update_footer()

            log_panel = self.query_one(LogPanel)
            msg = f"SINAL #{data['id']} {data['direction']} conf={data['confidence']:.0%}"
            log_panel.add_log(msg, "INFO")

            overview = self.query_one(OverviewPanel)
            overview.add_log("INFO", _now_brt_str(), "", msg)

        elif event.type == EventType.SIGNAL_RESOLVED:
            data = event.data
            self.last_signal = data
            await self._refresh_active_signals()
            await self._refresh_history()
            await self._refresh_stats()
            self._update_footer()

            msg = (f"RESULT #{data['id']} {data['outcome'].upper()} "
                   f"entry={data['quote_entry']:.1f} exit={data['quote_exit']:.1f}")
            level = "INFO" if data["outcome"] == "win" else "ERROR"
            log_panel = self.query_one(LogPanel)
            log_panel.add_log(msg, level)

            overview = self.query_one(OverviewPanel)
            overview.add_log(level, _now_brt_str(), "", msg)

        elif event.type == EventType.LLM_RESPONSE:
            data = event.data
            msg = f"LLM: {data['direction']} conf={data['confidence']:.0%}"
            log_panel = self.query_one(LogPanel)
            log_panel.add_log(msg, "INFO")

            overview = self.query_one(OverviewPanel)
            overview.add_log("INFO", _now_brt_str(), "", msg)

        elif event.type == EventType.LOG:
            data = event.data
            level = data.get("level", "INFO")
            time_str = data.get("time", "")
            name = data.get("name", "")
            message = data.get("message", "")

            log_panel = self.query_one(LogPanel)
            log_panel.add_log(message, level, time_str, name)

            overview = self.query_one(OverviewPanel)
            overview.add_log(level, time_str, name, message)

        elif event.type == EventType.ERROR:
            data = event.data
            msg = f"ERRO: {data['message']}"
            log_panel = self.query_one(LogPanel)
            log_panel.add_log(msg, "ERROR")

            overview = self.query_one(OverviewPanel)
            overview.add_log("ERROR", _now_brt_str(), "", msg)

    async def _load_initial_data(self) -> None:
        await self._refresh_stats()
        await self._refresh_history()
        await self._refresh_active_signals()

    async def _refresh_stats(self) -> None:
        overall = self.db_reader.get_overall_stats()
        streak = self.db_reader.get_current_streak()
        by_regime = self.db_reader.get_stats_by_field("regime")
        by_direction = self.db_reader.get_stats_by_direction()
        by_strategy = self.db_reader.get_stats_by_field("strategy")
        by_conf = self.db_reader.get_stats_by_confidence_bucket()
        by_hour = self.db_reader.get_stats_by_hour_bucket()
        recent = self.db_reader.get_recent_outcomes(30)

        stats_panel = self.query_one(StatsPanel)
        stats_panel.update_all_stats(
            overall, streak,
            by_regime, by_direction, by_strategy,
            by_conf, by_hour, recent,
        )

        # Atualizar win rate na status bar e overview
        win_rate = overall.get("win_rate", 0.0)
        self.query_one(StatusPanel).update_win_rate(win_rate)
        self.query_one(OverviewPanel).update_win_rate(win_rate)

    async def _refresh_history(self) -> None:
        signals = self.db_reader.get_recent_signals(limit=50)
        recent = self.db_reader.get_recent_outcomes(30)
        history_panel = self.query_one(HistoryPanel)
        history_panel.update_history(signals, recent)

    async def _refresh_active_signals(self) -> None:
        signals = self.db_reader.get_active_signals()
        active_panel = self.query_one(ActivePanel)
        active_panel.update_active_signals(signals)

        # Atualizar sinal ativo na Overview
        overview = self.query_one(OverviewPanel)
        overview.update_active_signal(signals[0] if signals else None)

    def _update_uptime(self) -> None:
        now = datetime.now(timezone.utc)
        delta = now - self.start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        uptime_str = f"{h:02d}:{m:02d}:{s:02d}"

        self.query_one(StatusPanel).update_uptime(uptime_str)
        self.query_one(OverviewPanel).update_uptime(uptime_str)

    def _update_footer(self) -> None:
        if self.last_signal:
            outcome = self.last_signal.get("outcome", "").upper()
            sig_id = self.last_signal.get("id", "?")
            direction = self.last_signal.get("direction", "?")

            status_panel = self.query_one(StatusPanel)
            status_panel.update_last_signal(sig_id, direction, outcome)

            if outcome:
                style = "green" if outcome == "WIN" else "red"
                last_text = f"#{sig_id} [{style}]{outcome}[/]"
            else:
                last_text = f"#{sig_id} {direction}"

            stats = self.db_reader.get_overall_stats()
            wr = stats.get("win_rate", 0)
            wr_s = "green" if wr >= 0.6 else "yellow" if wr >= 0.5 else "red"
            self.title = f"Deriv Bot | {last_text} | WR [{wr_s}]{wr:.1%}[/]"

    def action_refresh_stats(self) -> None:
        asyncio.create_task(self._refresh_stats())


def _now_brt_str() -> str:
    return datetime.now(timezone.utc).astimezone(timezone(_BRT)).strftime("%H:%M:%S")
