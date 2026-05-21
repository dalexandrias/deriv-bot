import asyncio
import os
import sys
import time
import yaml
from datetime import datetime, timezone
from dotenv import load_dotenv

from deriv.client import build_client_from_env
from signals.repository import SignalRepository
from agent.loop import run_agent
from utils.logger import logger
from deriv.market import TIMEFRAME_TO_GRANULARITY


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def recover_pending_signals(client, repo, config):
    """Re-schedule pending signals and mark expired ones as aborted."""
    pending_alive = repo.get_pending_alive()
    pending_expired = repo.get_pending_expired()

    for s in pending_expired:
        repo.mark_aborted(s.id)

    for s in pending_alive:
        from signals import verifier
        created = datetime.fromisoformat(s.created_at)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        remaining = max(s.duration - int(elapsed), 0)

        asyncio.create_task(
            verifier.resolve(client, repo, s.id, s.quote_entry,
                             s.direction, s.symbol, remaining)
        )

    if pending_alive or pending_expired:
        logger.info(f"Recovery: {len(pending_alive)} signals re-scheduled, {len(pending_expired)} aborted")


async def wait_for_next_candle_close(timeframe: str) -> None:
    """Aguarda até que o candle atual feche, dormindo o tempo exato necessário."""
    granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe)
    if not granularity:
        raise ValueError(f"Timeframe inválido: {timeframe}")

    now = time.time()
    next_close = (int(now / granularity) + 1) * granularity
    wait_secs = next_close - now
    logger.info(f"Aguardando {wait_secs:.1f}s até fechamento do próximo candle...")
    await asyncio.sleep(wait_secs)


async def main() -> None:
    load_dotenv()
    for var in ("OPENROUTER_API_KEY", "DERIV_API_TOKEN"):
        if not os.environ.get(var):
            logger.error(f"Variável de ambiente obrigatória ausente: {var}")
            sys.exit(1)

    config = load_config()
    logger.info(f"Config carregada: modelo={config['model']} símbolo={config['symbol']}")

    client = build_client_from_env()
    repo = SignalRepository(config.get("db_path", "data/signals.db"))
    await client.connect()
    await recover_pending_signals(client, repo, config)

    try:
        while True:
            await client.ensure_connected()
            await wait_for_next_candle_close(config["timeframe"])
            try:
                await run_agent(client, config, repo)
            except Exception as e:
                logger.exception(f"Erro durante ciclo do agente: {e}")
    finally:
        await client.close()
        logger.info("Cliente Deriv encerrado. Encerrando bot.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupção pelo usuário. Saindo.")
