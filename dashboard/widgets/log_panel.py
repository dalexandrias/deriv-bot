"""Painel de logs em tempo real com filtros por nível, pause e contador X/Y."""
from collections import deque
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static, RichLog
from rich.text import Text


_LEVEL_STYLES = {
    "DEBUG":   "dim",
    "INFO":    "white",
    "WARNING": "yellow",
    "ERROR":   "red",
}

_ALL_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class LogPanel(Vertical):
    """Painel de logs com filtros, pause e contador total/buffer."""

    BINDINGS = [
        Binding("i", "toggle_info",    "INFO"),
        Binding("w", "toggle_warning", "WARN"),
        Binding("e", "toggle_error",   "ERROR"),
        Binding("d", "toggle_debug",   "DEBUG"),
        Binding("p", "toggle_pause",   "Pause"),
        Binding("c", "clear_log",      "Clear"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._buf: deque[dict] = deque(maxlen=2000)
        self._total_seen: int = 0
        self._active_levels: set[str] = set(_ALL_LEVELS)
        self._paused: bool = False

    def compose(self) -> ComposeResult:
        yield Static("", id="log-header")
        yield RichLog(id="log-body", highlight=False, markup=False, auto_scroll=True)

    def on_mount(self) -> None:
        self._render_header()

    # ── Public API ────────────────────────────────────────────────────────

    def add_log(self, message: str, level: str = "INFO",
                time_str: str = "", name: str = "") -> None:
        """Adiciona um log entry ao buffer e à view se não pausado."""
        self._total_seen += 1
        entry = {"level": level, "time": time_str, "name": name, "message": message}
        self._buf.append(entry)
        self._render_header()
        if not self._paused and level in self._active_levels:
            self._write_entry(entry)

    # ── Rendering ─────────────────────────────────────────────────────────

    def _write_entry(self, entry: dict) -> None:
        body = self.query_one("#log-body", RichLog)
        t = Text()
        t.append(f"{entry['time']:8} " if entry["time"] else "", style="dim")
        level = entry["level"]
        t.append(f"{level:7}", style=_LEVEL_STYLES.get(level, "white"))
        if entry["name"]:
            t.append(f"{entry['name']:20} ", style="cyan dim")
        t.append(entry["message"])
        body.write(t)

    def _render_header(self) -> None:
        levels_text = Text()
        for lvl in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            abbr = {"DEBUG": "d", "INFO": "i", "WARNING": "w", "ERROR": "e"}[lvl]
            if lvl in self._active_levels:
                levels_text.append(f"[{abbr}]{lvl} ", style=_LEVEL_STYLES.get(lvl, "white"))
            else:
                levels_text.append(f"[{abbr}]{lvl} ", style="dim")

        pause_s = "yellow" if self._paused else "dim"
        levels_text.append("[p]⏸ pause  ", style=pause_s)
        levels_text.append("[c]clear  ", style="dim")

        buf_count = sum(1 for e in self._buf if e["level"] in self._active_levels)
        levels_text.append(f"  {buf_count}/{self._total_seen} logs", style="dim")

        self.query_one("#log-header", Static).update(levels_text)

    def _replay_buf(self) -> None:
        body = self.query_one("#log-body", RichLog)
        body.clear()
        for entry in self._buf:
            if entry["level"] in self._active_levels:
                self._write_entry(entry)

    # ── Actions ───────────────────────────────────────────────────────────

    def action_toggle_info(self) -> None:
        self._toggle_level("INFO")

    def action_toggle_warning(self) -> None:
        self._toggle_level("WARNING")

    def action_toggle_error(self) -> None:
        self._toggle_level("ERROR")

    def action_toggle_debug(self) -> None:
        self._toggle_level("DEBUG")

    def _toggle_level(self, level: str) -> None:
        if level in self._active_levels:
            self._active_levels.discard(level)
        else:
            self._active_levels.add(level)
        self._render_header()
        self._replay_buf()

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        self._render_header()
        if not self._paused:
            self._replay_buf()

    def action_clear_log(self) -> None:
        self.query_one("#log-body", RichLog).clear()
        self._render_header()
