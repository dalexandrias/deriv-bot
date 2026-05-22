import asyncio
import os
import sys
import time
import yaml
from datetime import datetime, timezone
from dotenv import load_dotenv

from deriv.client import build_client_from_env
from deriv import market
from signals.repository import SignalRepository
from agent.loop import run_agent, fetch_and_analyze_market
from agent.learning import build_context_block
from utils.logger import logger
from deriv.market import TIMEFRAME_TO_GRANULARITY
from signals.models import Signal


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
        asyncio.create_task(
            verifier.resolve(
                client, repo, s.id,
                s.direction, s.symbol, s.timeframe,
                s.entry_candle_time,
                settle_delay=config.get("candle_settle_delay", 2),
            )
        )

    if pending_alive or pending_expired:
        logger.info(f"Recovery: {len(pending_alive)} signals re-scheduled, {len(pending_expired)} aborted")


async def emit_signal(client, repo, config, market_data, direction, confidence):
    """
    Emit a trading signal and schedule verification.

    Args:
        client: Deriv client
        repo: Signal repository
        config: Bot configuration
        market_data: Dict from fetch_and_analyze_market()
        direction: "CALL" or "PUT"
        confidence: 0.0-1.0

    Returns:
        signal_id (int)
    """
    from signals import verifier

    indicators = market_data["indicators"]
    next_entry_epoch = market_data["next_entry_epoch"]
    last_candle_epoch = market_data["last_candle_epoch"]

    entry_candle_time = datetime.fromtimestamp(next_entry_epoch, tz=timezone.utc).isoformat()

    signal = Signal(
        created_at=datetime.now(timezone.utc).isoformat(),
        symbol=config["symbol"],
        direction=direction,
        confidence=confidence,
        reason="",  # Not used in new architecture
        duration=int(config["duration"]),
        timeframe=config["timeframe"],
        rsi=indicators.get("rsi"),
        bb_position=indicators.get("bb_position"),
        adx=indicators.get("adx"),
        atr_pct=indicators.get("atr_pct"),
        price_vs_ema50=indicators.get("price_vs_ema50"),
        quote_entry=None,  # populated by verifier using candle open
        status="pending",
        last_candle_epoch=last_candle_epoch,
        entry_candle_time=entry_candle_time,
    )

    signal_id = repo.insert(signal)

    # Schedule verification: resolves using real candle open/close
    asyncio.create_task(
        verifier.resolve(
            client, repo, signal_id,
            direction, config["symbol"], config["timeframe"],
            entry_candle_time,
            settle_delay=config.get("candle_settle_delay", 2),
        )
    )

    logger.info(
        f"📝 SIGNAL #{signal_id} | {direction} | EMITTED | {config['symbol']} "
        f"| conf={confidence:.0%} | Entrada: {entry_candle_time}"
    )

    return signal_id


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
            settle = config.get("candle_settle_delay", 2)
            if settle > 0:
                await asyncio.sleep(settle)

            try:
                # Step 1: Fetch market data and calculate indicators
                market_data = await fetch_and_analyze_market(client, config)

                # Step 2: Run LLM analysis
                result = await run_agent(client, config, repo, market_data)

                # Step 3: Bot decides based on confidence threshold
                confidence = result["confidence"]
                direction = result["direction"]
                min_confidence = config.get("min_confidence", 0.60)

                if confidence >= min_confidence and direction != "NONE":
                    logger.info(
                        f"✅ Confiança {confidence:.0%} >= {min_confidence:.0%} → ENTRANDO em {direction}"
                    )
                    logger.info(
                        f"🎯 SINAL: {direction} | Confiança: {confidence:.0%} | "
                        f"Próximo candle: {market_data['next_entry_time']}"
                    )

                    # Emit signal
                    signal_id = await emit_signal(
                        client, repo, config, market_data, direction, confidence
                    )
                else:
                    logger.info(
                        f"⏸️ Confiança insuficiente: {confidence:.0%} < {min_confidence:.0%} "
                        f"ou direção={direction}"
                    )

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
