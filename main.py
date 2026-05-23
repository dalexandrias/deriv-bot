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
from events import EventServer, EventType, set_event_server, publish
from utils.log_sink import attach_event_sink


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

    # Support both old and new config format
    if "decision_timeframe" in config:
        decision_tf = config["decision_timeframe"]
    else:
        decision_tf = config.get("timeframe", "5m")

    m5_indicators = market_data["m5_indicators"]
    pre_analysis = market_data["pre_analysis"]
    next_entry_epoch = market_data["next_entry_epoch"]
    last_candle_epoch = market_data["last_candle_epoch"]

    entry_candle_time = datetime.fromtimestamp(next_entry_epoch, tz=timezone.utc).isoformat()

    # Extract pre-analysis data
    regime = pre_analysis.get("regime")
    time_window = pre_analysis.get("time_window", {}).get("window")
    m15_bias = pre_analysis.get("m15_bias", {}).get("bias")
    confluence = pre_analysis.get("confluence", {})
    confluence_score = max(confluence.get("call_signals", 0), confluence.get("put_signals", 0))
    strategy = pre_analysis.get("suggested_strategy")

    signal = Signal(
        created_at=datetime.now(timezone.utc).isoformat(),
        symbol=config["symbol"],
        direction=direction,
        confidence=confidence,
        reason="",  # Not used in new architecture
        duration=int(config["duration"]),
        timeframe=decision_tf,
        rsi=m5_indicators.get("rsi"),
        bb_position=m5_indicators.get("bb_position"),
        adx=m5_indicators.get("adx"),
        atr_pct=m5_indicators.get("atr_pct"),
        price_vs_ema50=m5_indicators.get("price_vs_ema50"),
        macd_line=m5_indicators.get("macd_line"),
        macd_signal=m5_indicators.get("macd_signal"),
        macd_histogram=m5_indicators.get("macd_histogram"),
        quote_entry=None,  # populated by verifier using candle open
        status="pending",
        last_candle_epoch=last_candle_epoch,
        entry_candle_time=entry_candle_time,
        regime=regime,
        time_window=time_window,
        m15_bias=m15_bias,
        confluence_score=confluence_score,
        strategy=strategy,
    )

    signal_id = repo.insert(signal)

    # Schedule verification: resolves using real candle open/close
    asyncio.create_task(
        verifier.resolve(
            client, repo, signal_id,
            direction, config["symbol"], decision_tf,
            entry_candle_time,
            settle_delay=config.get("candle_settle_delay", 2),
        )
    )

    logger.info(
        f"📝 SIGNAL #{signal_id} | {direction} | EMITIDO | {config['symbol']} "
        f"| conf={confidence:.0%} | {regime} | {time_window} | {strategy} | Entrada: {entry_candle_time}"
    )

    return signal_id


async def wait_for_next_candle_close(config: dict) -> None:
    """Aguarda até que o candle atual feche, dormindo o tempo exato necessário."""
    # Support both old and new config format
    if "decision_timeframe" in config:
        timeframe = config["decision_timeframe"]
    else:
        timeframe = config.get("timeframe", "5m")

    granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe)
    if not granularity:
        raise ValueError(f"Timeframe inválido: {timeframe}")

    now = time.time()
    next_close = (int(now / granularity) + 1) * granularity
    wait_secs = next_close - now
    logger.info(f"Aguardando {wait_secs:.1f}s até fechamento do próximo candle ({timeframe})...")
    await asyncio.sleep(wait_secs)


async def main() -> None:
    load_dotenv()
    for var in ("OPENROUTER_API_KEY", "DERIV_API_TOKEN"):
        if not os.environ.get(var):
            logger.error(f"Variável de ambiente obrigatória ausente: {var}")
            sys.exit(1)

    config = load_config()
    logger.info(f"Config carregada: modelo={config['model']} símbolo={config['symbol']}")

    # Support both old and new config format
    if "decision_timeframe" in config:
        decision_tf = config["decision_timeframe"]
        context_tf = config.get("context_timeframe", "15m")
        logger.info(f"Timeframes: decisão={decision_tf}, contexto={context_tf}")
    else:
        decision_tf = config.get("timeframe", "5m")
        context_tf = "15m"
        logger.info(f"Timeframe (legado): {decision_tf}")

    client = build_client_from_env()
    repo = SignalRepository(config.get("db_path", "data/signals.db"))
    await client.connect()
    publish(EventType.STATUS, {"status": "connected"})

    # Iniciar EventServer para comunicação com UI
    event_server = EventServer()
    set_event_server(event_server)
    await event_server.start()
    attach_event_sink()
    publish(EventType.STATUS, {"status": "ready", "detail": "Bot iniciado"})

    await recover_pending_signals(client, repo, config)

    try:
        while True:
            await client.ensure_connected()
            publish(EventType.STATUS, {"status": "waiting", "detail": "Aguardando candle"})
            await wait_for_next_candle_close(config)
            settle = config.get("candle_settle_delay", 2)
            if settle > 0:
                await asyncio.sleep(settle)

            try:
                publish(EventType.STATUS, {"status": "analyzing", "detail": "Analisando mercado"})

                # Step 1: Fetch market data and calculate indicators (dual timeframe)
                market_data = await fetch_and_analyze_market(client, config)

                # Publish market data update
                publish(EventType.MARKET, {
                    "m5_indicators": market_data["m5_indicators"],
                    "m15_indicators": market_data["m15_indicators"],
                    "pre_analysis": market_data["pre_analysis"],
                    "last_candle_time": market_data["last_candle_time"],
                    "next_entry_time": market_data["next_entry_time"],
                })

                # Step 1b: Persist both M5 and M15 candles in local DB for tool use
                repo.insert_candles_batch(
                    market_data["m5_candles"], config["symbol"], decision_tf
                )
                repo.insert_candles_batch(
                    market_data["m15_candles"], config["symbol"], context_tf
                )

                # Step 2: Run LLM analysis with pre-analysis context
                result = await run_agent(client, config, repo, market_data)

                # Publish LLM response
                publish(EventType.LLM_RESPONSE, {
                    "direction": result["direction"],
                    "confidence": result["confidence"],
                    "raw_response": result.get("raw_response", ""),
                })

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

                    # Publish signal emitted event
                    pre = market_data["pre_analysis"]
                    publish(EventType.SIGNAL_EMITTED, {
                        "id": signal_id,
                        "direction": direction,
                        "confidence": confidence,
                        "symbol": config["symbol"],
                        "regime": pre.get("regime", ""),
                        "time_window": pre.get("time_window", {}).get("window", ""),
                        "strategy": pre.get("suggested_strategy", ""),
                        "entry_candle_time": market_data["next_entry_time"],
                    })
                else:
                    logger.info(
                        f"⏸️ Confiança insuficiente: {confidence:.0%} < {min_confidence:.0%} "
                        f"ou direção={direction}"
                    )
                    publish(EventType.STATUS, {
                        "status": "idle",
                        "detail": f"Confiança insuficiente: {confidence:.0%}"
                    })

            except Exception as e:
                logger.exception(f"Erro durante ciclo do agente: {e}")
                publish(EventType.ERROR, {"message": str(e)})
    finally:
        await event_server.stop()
        await client.close()
        logger.info("Cliente Deriv encerrado. Encerrando bot.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupção pelo usuário. Saindo.")
