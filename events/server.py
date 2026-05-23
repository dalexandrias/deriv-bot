"""Unix socket server que publica eventos para clientes conectados."""
import asyncio
import os
from pathlib import Path
from typing import Set
import socket

from events.protocol import Event
from utils.logger import logger


class EventServer:
    """Servidor de eventos via Unix socket."""

    def __init__(self, socket_path: str | None = None):
        self.socket_path = socket_path or os.path.expanduser("~/.deriv-bot/events.sock")
        self._server: asyncio.Server | None = None
        self._writers: Set[asyncio.StreamWriter] = set()
        self._running = False

    async def start(self) -> None:
        """Inicia o servidor Unix socket."""
        # Criar diretório do socket se não existir
        Path(self.socket_path).parent.mkdir(parents=True, exist_ok=True)

        # Remover socket anterior se existir
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self._running = True

        # Criar servidor Unix socket
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=self.socket_path,
        )

        logger.info(f"EventServer iniciado em {self.socket_path}")

        # Manter rodando em background
        asyncio.create_task(self._serve_forever())

    async def _serve_forever(self) -> None:
        """Mantém o servidor rodando."""
        if self._server:
            async with self._server:
                await self._server.serve_forever()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle uma conexão de cliente."""
        addr = writer.get_extra_info("peername")
        logger.info(f"Cliente conectado: {addr}")

        # Adicionar writer à lista
        self._writers.add(writer)

        try:
            # Manter conexão aberta (cliente pode enviar heartbeat)
            while self._running:
                data = await reader.read(1024)
                if not data:
                    break
                # Cliente pode enviar comandos futuramente
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Erro no cliente {addr}: {e}")
        finally:
            self._writers.discard(writer)
            writer.close()
            await writer.wait_closed()
            logger.info(f"Cliente desconectado: {addr}")

    async def broadcast(self, event: Event) -> None:
        """Envia evento para todos clientes conectados."""
        if not self._writers:
            return

        message = event.to_json() + "\n"
        data = message.encode("utf-8")

        # Enviar para todos clientes conectados
        disconnected = set()
        for writer in self._writers:
            try:
                writer.write(data)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                disconnected.add(writer)
            except Exception as e:
                logger.warning(f"Erro ao enviar para cliente: {e}")
                disconnected.add(writer)

        # Remover clientes desconectados
        for writer in disconnected:
            self._writers.discard(writer)
            writer.close()
            await writer.wait_closed()

    async def stop(self) -> None:
        """Para o servidor e limpa recursos."""
        self._running = False

        # Fechar todas as conexões de clientes
        for writer in list(self._writers):
            writer.close()
            await writer.wait_closed()
        self._writers.clear()

        # Fechar o servidor
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Remover arquivo do socket
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        logger.info("EventServer parado")
