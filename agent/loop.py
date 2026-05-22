import json
import os
import asyncio
import httpx
from datetime import datetime, UTC, timezone

from deriv.client import DerivClient
from deriv import market
from indicators.technical import analyze
from signals.repository import SignalRepository
from agent.learning import build_context_block
from agent.prompts import build_system_prompt, build_user_context
from utils.logger import logger

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ITERATIONS = 10
MAX_RETRIES = 3


async def fetch_and_analyze_market(client: DerivClient, config: dict) -> dict:
    """
    Fetch candles from Deriv, calculate technical indicators, and compute entry times.

    Returns:
        dict with:
        - candles: list of candle data
        - indicators: technical analysis (RSI, BB, ADX, ATR, EMA)
        - last_candle_epoch: epoch time of last candle (seconds)
        - next_entry_epoch: epoch time of next entry candle (seconds)
        - last_candle_time: formatted datetime string of last candle
        - next_entry_time: formatted datetime string of next entry
    """
    symbol = config["symbol"]
    timeframe = config["timeframe"]
    count = config.get("candles_count", 60)

    # Ensure minimum candles for indicator stability
    count = max(count, 60)

    logger.info(f"📊 Buscando {count} candles de {symbol} ({timeframe})...")
    candles = await market.get_candles(client, symbol, timeframe, count)

    if not candles:
        raise RuntimeError(f"Sem candles retornados para {symbol}")

    logger.info(f"📊 {len(candles)} candles recebidos")

    # Calculate technical indicators
    indicators = analyze(candles)
    indicators["symbol"] = symbol
    indicators["timeframe"] = timeframe

    # Get last candle epoch and calculate next entry time
    last_candle_epoch = candles[-1]["time"]  # seconds (Deriv API)
    now = datetime.now(timezone.utc).timestamp()

    from deriv.market import TIMEFRAME_TO_GRANULARITY
    granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe, 60)

    # Detect API lag: last candle should be at most 1 period behind the current boundary
    expected_last_closed = int(now / granularity) * granularity - granularity
    lag_periods = (expected_last_closed - last_candle_epoch) / granularity
    if lag_periods > 1:
        logger.warning(
            f"⚠️  API lag detectado: último candle da API é {int(lag_periods)} período(s) atrás do esperado "
            f"(API={last_candle_epoch}, esperado≥{expected_last_closed})"
        )

    # Entry candle = the one that just opened (current period boundary, wall-clock-based)
    # This is reliable even when the API returns stale data
    next_entry_epoch = int(now / granularity) * granularity

    # Format times for display
    last_candle_dt = datetime.fromtimestamp(last_candle_epoch, tz=timezone.utc)
    next_entry_dt = datetime.fromtimestamp(next_entry_epoch, tz=timezone.utc)

    logger.info(
        f"📈 Indicadores: RSI={indicators.get('rsi', 0):.1f}, "
        f"BB={indicators.get('bb_position', 'N/A')}, "
        f"ADX={indicators.get('adx', 0):.1f}, "
        f"ATR={indicators.get('atr_pct', 0):.1f}%"
    )
    logger.info(f"🕐 Último candle: {last_candle_dt.strftime('%d/%m/%Y - %H:%M:%S')} UTC")
    logger.info(f"🕐 Próxima entrada: {next_entry_dt.strftime('%d/%m/%Y - %H:%M:%S')} UTC")

    return {
        "candles": candles,
        "indicators": indicators,
        "last_candle_epoch": last_candle_epoch,
        "next_entry_epoch": next_entry_epoch,
        "last_candle_time": last_candle_dt.isoformat(),
        "next_entry_time": next_entry_dt.isoformat(),
    }


async def _call_openrouter(http: httpx.AsyncClient, model: str, messages: list[dict]) -> dict:
    api_key = os.environ["OPENROUTER_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
    }

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await http.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_exc = e
            logger.warning(f"OpenRouter falhou (tentativa {attempt}/{MAX_RETRIES}): {e}")
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"OpenRouter indisponível após {MAX_RETRIES} tentativas: {last_exc}")


async def run_agent(client: DerivClient, config: dict, repo: SignalRepository,
                    market_data: dict) -> dict:
    """
    Run the LLM agent with pre-calculated indicators.

    Args:
        client: Deriv client
        config: Bot configuration
        repo: Signal repository
        market_data: Dict from fetch_and_analyze_market() with:
            - indicators: technical analysis
            - last_candle_time: ISO formatted datetime
            - next_entry_time: ISO formatted datetime

    Returns:
        dict with:
        - confidence: float (0.0-1.0)
        - direction: "CALL" | "PUT" | "NONE"
        - raw_response: raw text from model (for debugging)
    """
    learning_block = build_context_block(repo, config)
    system_prompt = build_system_prompt(config)
    user_msg = build_user_context(
        config,
        market_data["indicators"],
        learning_block,
        market_data.get("last_candle_time", ""),
        market_data.get("next_entry_time", "")
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    logger.info("=== Novo ciclo do agente iniciado ===")
    logger.info(f"🤖 Chamando modelo {config['model']}...")

    # Log do prompt completo para debug
    logger.debug("=== PROMPT ENVIADO PARA O LLM ===")
    for msg in messages:
        logger.debug(f"[{msg['role'].upper()}]:\n{msg['content']}")
    logger.debug("=== FIM DO PROMPT ===")

    async with httpx.AsyncClient() as http:
        data = await _call_openrouter(http, config["model"], messages)

    choice = data["choices"][0]
    content = choice["message"].get("content", "").strip()

    logger.info(f"📥 Resposta do modelo: {content}")

    # Parse JSON response
    try:
        # Extract JSON from response (handle cases where model adds text around it)
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")

        json_str = content[json_start:json_end]
        result = json.loads(json_str)

        confidence = float(result.get("confidence", 0.5))
        direction = str(result.get("direction", "NONE")).upper()

        # Validate confidence range
        if not (0.0 <= confidence <= 1.0):
            logger.warning(f"⚠️ Confiança fora do range: {confidence}, usando 0.5")
            confidence = 0.5

        # Validate direction
        if direction not in ("CALL", "PUT", "NONE"):
            logger.warning(f"⚠️ Direção inválida: {direction}, usando NONE")
            direction = "NONE"

        logger.info(f"✅ Parseado: confidence={confidence:.2f}, direction={direction}")

        return {
            "confidence": confidence,
            "direction": direction,
            "raw_response": content,
        }

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"❌ Erro ao parsear resposta JSON: {e}")
        logger.error(f"Resposta bruta: {content}")
        # Return safe defaults on parse error
        return {
            "confidence": 0.0,
            "direction": "NONE",
            "raw_response": content,
        }
