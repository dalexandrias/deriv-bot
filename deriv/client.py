import asyncio
import json
import itertools
import os
import websockets
from utils.logger import logger


class DerivError(Exception):
    pass


class DerivClient:
    WS_URL_TMPL = "wss://ws.derivws.com/websockets/v3?app_id={app_id}"

    def __init__(self, api_token: str, app_id: str | int = 1089):
        self.api_token = api_token
        self.app_id = str(app_id)
        self._ws = None
        self._listener_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._req_id_counter = itertools.count(1)
        self._lock = asyncio.Lock()
        self._stop = False

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        url = self.WS_URL_TMPL.format(app_id=self.app_id)
        backoff = 1
        while not self._stop:
            try:
                logger.info(f"Conectando à Deriv WS ({url}) ...")
                self._ws = await websockets.connect(url, ping_interval=20, ping_timeout=20)
                self._listener_task = asyncio.create_task(self._listener())
                auth = await self._send({"authorize": self.api_token})
                logger.info(f"Autorizado. Loginid={auth.get('authorize', {}).get('loginid')}")
                return
            except Exception as e:
                logger.error(f"Falha ao conectar: {e}. Retentando em {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8)

    async def ensure_connected(self) -> None:
        """Reconnect if the WebSocket is no longer open."""
        if not self.is_connected:
            logger.info("WS desconectado — reconectando antes do próximo ciclo.")
            self._stop = False
            await self.connect()

    async def close(self) -> None:
        self._stop = True
        if self._listener_task:
            self._listener_task.cancel()
        if self._ws:
            await self._ws.close()

    async def _listener(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    logger.warning(f"Mensagem não-JSON recebida: {raw[:200]}")
                    continue
                logger.debug(f"WS<<< {msg}")
                req_id = msg.get("req_id")
                fut = self._pending.pop(req_id, None) if req_id is not None else None
                if fut and not fut.done():
                    fut.set_result(msg)
        except asyncio.CancelledError:
            return
        except websockets.ConnectionClosed as e:
            logger.warning(f"Conexão WS fechada: {e}. Tentando reconectar.")
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(DerivError("WS closed"))
            self._pending.clear()
            if not self._stop:
                await self.connect()

    async def _send(self, payload: dict, timeout: float = 30.0) -> dict:
        if not self.is_connected:
            await self.ensure_connected()
        req_id = next(self._req_id_counter)
        payload = {**payload, "req_id": req_id}
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[req_id] = fut
        try:
            async with self._lock:
                logger.debug(f"WS>>> {payload}")
                await self._ws.send(json.dumps(payload))
        except (websockets.ConnectionClosed, DerivError) as e:
            self._pending.pop(req_id, None)
            logger.warning(f"WS caiu durante send ({e}) — reconectando e retentando.")
            await self.ensure_connected()
            return await self._send(payload, timeout=timeout)
        try:
            resp = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise DerivError(f"Timeout aguardando resposta para req_id={req_id}")
        if "error" in resp:
            err = resp["error"]
            raise DerivError(f"{err.get('code')}: {err.get('message')}")
        return resp


def build_client_from_env() -> DerivClient:
    token = os.environ["DERIV_API_TOKEN"]
    app_id = os.environ.get("DERIV_APP_ID", "1089")
    return DerivClient(token, app_id)
