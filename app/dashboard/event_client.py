"""Cliente que conecta ao Unix socket e recebe eventos do bot."""
import asyncio
import os
from typing import Callable, Awaitable
from app.events.protocol import Event


class EventClient:
    """Cliente para receber eventos do EventServer."""

    def __init__(
        self,
        socket_path: str | None = None,
        on_event: Callable[[Event], Awaitable[None]] | None = None,
    ):
        self.socket_path = socket_path or os.path.expanduser("~/.deriv-bot/events.sock")
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._on_event = on_event
        self._task: asyncio.Task | None = None

    async def connect(self) -> bool:
        """Conecta ao socket do servidor."""
        if not os.path.exists(self.socket_path):
            return False

        try:
            self._reader, self._writer = await asyncio.open_unix_connection(
                path=self.socket_path
            )
            self._connected = True
            return True
        except (FileNotFoundError, ConnectionRefusedError):
            return False

    async def disconnect(self) -> None:
        """Desconecta do servidor."""
        self._connected = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self._reader = None
        self._writer = None

    async def _receive_loop(self) -> None:
        """Loop de recebimento de eventos."""
        while self._connected and self._reader:
            try:
                line = await self._reader.readline()
                if not line:
                    break

                event = Event.from_json(line.decode("utf-8"))

                if self._on_event:
                    await self._on_event(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Ignorar erros de parsing
                pass

    async def start_listening(
        self, on_event: Callable[[Event], Awaitable[None]]
    ) -> None:
        """Inicia o loop de recebimento de eventos."""
        self._on_event = on_event
        self._task = asyncio.create_task(self._receive_loop())

    @property
    def connected(self) -> bool:
        """Retorna True se conectado."""
        return self._connected

    async def send_heartbeat(self) -> None:
        """Envia heartbeat para manter conexao ativa."""
        if self._writer and self._connected:
            try:
                self._writer.write(b"\n")
                await self._writer.drain()
            except Exception:
                self._connected = False


class AutoReconnectEventClient(EventClient):
    """Cliente com reconexao automatica."""

    def __init__(
        self,
        socket_path: str | None = None,
        on_event: Callable[[Event], Awaitable[None]] | None = None,
        reconnect_interval: float = 5.0,
    ):
        super().__init__(socket_path, on_event)
        self._reconnect_interval = reconnect_interval
        self._reconnect_task: asyncio.Task | None = None

    async def start_with_reconnect(
        self, on_event: Callable[[Event], Awaitable[None]]
    ) -> None:
        """Inicia com reconexao automatica."""
        self._on_event = on_event

        async def reconnect_loop():
            while True:
                if not self._connected:
                    connected = await self.connect()
                    if connected:
                        await self.start_listening(on_event)

                await asyncio.sleep(self._reconnect_interval)

        self._reconnect_task = asyncio.create_task(reconnect_loop())

    async def disconnect(self) -> None:
        """Para reconexao e desconecta."""
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        await super().disconnect()
