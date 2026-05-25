import asyncio
import os
import time
import json
from datetime import datetime, timezone, timedelta

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.collector.deriv_client import DerivClient, TIMEFRAME_TO_GRANULARITY
from app.signals.repository import SignalRepository
from app.signals.models import SignalCreate
from app.indicators.service import IndicatorService
from app.indicators.technical import analyze
from app.agent.pre_analysis import run_pre_analysis
from app.agent.prompts import build_system_prompt, build_user_context
from app.agent.tools import TOOLS, ToolDispatcher
from app.agent.learning import build_context_block
from app.events.protocol import EventType
from app.events.publisher import publish
from app.config import settings
from app.db.models import BotConfig, IndicatorConfig

BRT = timezone(timedelta(hours=-3))
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_TOOL_TURNS = 5
MAX_RETRIES = 3

_BB_TO_FLOAT = {"acima": 1.0, "dentro": 0.0, "abaixo": -1.0}
_EMA_TO_FLOAT = {"acima": 1.0, "abaixo": -1.0}


class AgentService:
    def __init__(self, client: DerivClient, session_factory: async_sessionmaker):
        self.client = client
        self.session_factory = session_factory
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_cycle: datetime | None = None
        self._start_time: datetime | None = None
        self._cycle_count: int = 0
        self._active_verifiers: dict[int, asyncio.Task] = {}

    async def start(self) -> None:
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            repo = SignalRepository(session)
            config = await self._load_config(repo)
            await self._recover_pending_signals(repo, session, config)
        self._task = asyncio.create_task(self._loop())
        logger.info("Agent iniciado")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent parado")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> dict:
        return {
            "running": self._running,
            "last_cycle": self._last_cycle.isoformat() if self._last_cycle else None,
            "uptime": (datetime.now(timezone.utc) - self._start_time).total_seconds() if self._start_time else 0,
        }

    async def _load_config(self, repo: SignalRepository) -> dict:
        stmt = select(BotConfig)
        result = await repo.session.execute(stmt)
        configs = result.scalars().all()
        config = {}
        for cfg in configs:
            try:
                config[cfg.key] = json.loads(cfg.value)
            except (json.JSONDecodeError, TypeError):
                config[cfg.key] = cfg.value
        return config

    async def _load_indicator_configs(self, repo: SignalRepository) -> list:
        stmt = select(IndicatorConfig)
        result = await repo.session.execute(stmt)
        return result.scalars().all()

    async def _recover_pending_signals(self, repo: SignalRepository, session, config: dict) -> None:
        from app.signals.verifier import resolve

        expired = await repo.get_pending_expired()
        for sig in expired:
            await repo.mark_error(sig.id)
            publish(EventType.SIGNAL_RESOLVED, {"id": sig.id, "status": "error"})
            logger.warning(f"Sinal #{sig.id} expirado sem resolução → marcado como erro")
        if expired:
            await session.commit()

        alive = await repo.get_pending_alive()
        settle_delay = int(config.get("candle_settle_delay", 2))
        for sig in alive:
            if sig.id not in self._active_verifiers:
                task = asyncio.create_task(resolve(
                    self.client, self.session_factory, sig.id, sig.direction,
                    sig.symbol, sig.timeframe, sig.entry_candle_time,
                    settle_delay=settle_delay,
                ))
                self._active_verifiers[sig.id] = task
                task.add_done_callback(lambda _, sid=sig.id: self._active_verifiers.pop(sid, None))
                logger.info(f"Sinal #{sig.id} recuperado → verifier re-iniciado")

    async def _loop(self) -> None:
        while self._running:
            try:
                self._cycle_count += 1
                cycle_id = self._cycle_count
                cycle_start = datetime.now(BRT)

                async with self.session_factory() as session:
                    repo = SignalRepository(session)

                    config = await self._load_config(repo)
                    indicator_configs = await self._load_indicator_configs(repo)
                    symbol = config.get("symbol", "R_25")
                    decision_tf = config.get("decision_timeframe", "5m")
                    context_tf = config.get("context_timeframe", "15m")
                    min_confidence = float(config.get("min_confidence", 0.50))

                    await self._recover_pending_signals(repo, session, config)

                    logger.info(
                        f"┌─ CICLO #{cycle_id:04d} ─────────────────────────────────────────"
                    )
                    logger.info(
                        f"│  Iniciado em {cycle_start.strftime('%H:%M:%S')} BRT | "
                        f"{symbol} | {decision_tf}/{context_tf} | min_conf={min_confidence:.0%}"
                    )

                    await self.client.ensure_connected()
                    publish(EventType.STATUS, {"status": "waiting", "detail": "Aguardando candle"})
                    await self._wait_for_next_candle_close(config)
                    settle = int(config.get("candle_settle_delay", 2))
                    if settle > 0:
                        await asyncio.sleep(settle)

                    publish(EventType.STATUS, {"status": "analyzing", "detail": "Analisando mercado"})
                    market_data = await self._fetch_and_analyze(config, indicator_configs)
                    m5 = market_data["m5_indicators"]
                    m15 = market_data["m15_indicators"]
                    pre = market_data["pre_analysis"]

                    _m5_macd = m5.get('macd_histogram')
                    _m15_macd = m15.get('macd_histogram')
                    _m5_macd_s = f"{_m5_macd:.4f}" if _m5_macd is not None else "-"
                    _m15_macd_s = f"{_m15_macd:.4f}" if _m15_macd is not None else "-"
                    logger.info(
                        f"│  [M5]  RSI={m5.get('rsi', 0):.1f}  MACD_h={_m5_macd_s}  "
                        f"BB_pos={m5.get('bb_position', '-')}  ADX={m5.get('adx', 0):.1f}  ATR%={m5.get('atr_pct', 0):.3f}"
                    )
                    logger.info(
                        f"│  [M15] RSI={m15.get('rsi', 0):.1f}  MACD_h={_m15_macd_s}  "
                        f"BB_pos={m15.get('bb_position', '-')}  ADX={m15.get('adx', 0):.1f}  EMA50={m15.get('price_vs_ema50', '-')}"
                    )
                    logger.info(
                        f"│  [PRE] regime={pre.get('regime', '-')}  "
                        f"m15_bias={pre.get('m15_bias', {}).get('bias', '-')}  "
                        f"confluência=CALL:{pre.get('confluence', {}).get('call_signals', 0)} "
                        f"PUT:{pre.get('confluence', {}).get('put_signals', 0)}  "
                        f"estratégia={pre.get('suggested_strategy', '-')}"
                    )

                    publish(EventType.MARKET, {
                        "m5_indicators": m5,
                        "m15_indicators": m15,
                        "pre_analysis": pre,
                        "last_candle_time": market_data.get("last_candle_time", ""),
                        "next_entry_time": market_data.get("next_entry_time", ""),
                    })

                    await repo.upsert_candles(market_data["m5_candles"], symbol, decision_tf)
                    await repo.upsert_candles(market_data["m15_candles"], symbol, context_tf)

                    result = await self._run_agent(config, market_data, repo, session)
                    confidence = result["confidence"]
                    direction = result["direction"]

                    publish(EventType.LLM_RESPONSE, {
                        "direction": direction,
                        "confidence": confidence,
                    })

                    signal_id = None
                    signal_status = ""
                    if confidence >= min_confidence and direction != "NONE":
                        signal_data = SignalCreate(
                            symbol=symbol, timeframe=decision_tf,
                            direction=direction, confidence=confidence,
                            duration=int(config.get("duration", 300)),
                            rsi=m5.get("rsi"),
                            bb_position=_BB_TO_FLOAT.get(m5.get("bb_position"), None),
                            adx=m5.get("adx"),
                            atr_pct=m5.get("atr_pct"),
                            price_vs_ema50=_EMA_TO_FLOAT.get(m5.get("price_vs_ema50"), None),
                            macd_line=m5.get("macd_line"),
                            macd_signal=m5.get("macd_signal"),
                            macd_histogram=m5.get("macd_histogram"),
                            regime=pre.get("regime"),
                            time_window=pre.get("time_window", {}).get("window"),
                            m15_bias=pre.get("m15_bias", {}).get("bias"),
                            confluence_score=max(
                                pre.get("confluence", {}).get("call_signals", 0),
                                pre.get("confluence", {}).get("put_signals", 0),
                            ),
                            strategy=pre.get("suggested_strategy"),
                            entry_candle_time=market_data.get("next_entry_time"),
                        )
                        signal_id = await repo.insert_signal(signal_data)
                        await session.commit()
                        signal_status = f"EMITIDO #{signal_id}"
                        publish(EventType.SIGNAL_EMITTED, {
                            "id": signal_id, "direction": direction,
                            "confidence": confidence, "symbol": symbol,
                            "entry_candle_time": market_data.get("next_entry_time"),
                            "duration": int(config.get("duration", 300)),
                        })
                        from app.signals.verifier import resolve
                        _v_task = asyncio.create_task(resolve(
                            self.client, self.session_factory, signal_id, direction,
                            symbol, decision_tf,
                            market_data.get("next_entry_time"),
                            settle_delay=int(config.get("candle_settle_delay", 2)),
                        ))
                        self._active_verifiers[signal_id] = _v_task
                        _v_task.add_done_callback(
                            lambda _, sid=signal_id: self._active_verifiers.pop(sid, None)
                        )
                    else:
                        signal_status = f"NÃO EMITIDO (conf={confidence:.0%} < mín={min_confidence:.0%})"
                        publish(EventType.STATUS, {"status": "idle", "detail": f"Confiança insuficiente: {confidence:.0%}"})

                cycle_elapsed = (datetime.now(BRT) - cycle_start).total_seconds()
                self._last_cycle = datetime.now(timezone.utc)

                logger.success(
                    f"│  [DECISÃO] {direction}  confiança={confidence:.0%}  sinal={signal_status}"
                )
                logger.success(
                    f"└─ CICLO #{cycle_id:04d} CONCLUÍDO em {cycle_elapsed:.1f}s ──────────────────────"
                )
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.exception(f"Erro durante ciclo #{self._cycle_count} do agente: {e}")
                publish(EventType.ERROR, {"message": str(e)})
                await asyncio.sleep(10)

    async def _wait_for_next_candle_close(self, config: dict) -> None:
        tf = config.get("decision_timeframe", "5m")
        granularity = TIMEFRAME_TO_GRANULARITY.get(tf, 300)
        now = time.time()
        next_close = (int(now / granularity) + 1) * granularity
        wait_secs = next_close - now
        logger.info(f"Aguardando {wait_secs:.1f}s até fechamento do próximo candle ({tf})...")
        remaining = wait_secs
        heartbeat_interval = 20.0
        while remaining > 0:
            chunk = min(heartbeat_interval, remaining)
            await asyncio.sleep(chunk)
            remaining -= chunk
            if remaining > 0:
                publish(EventType.STATUS, {
                    "status": "waiting",
                    "detail": f"Próximo candle em {int(remaining)}s",
                })

    async def _fetch_and_analyze(self, config: dict, indicator_configs: list) -> dict:
        decision_tf = config.get("decision_timeframe", "5m")
        context_tf = config.get("context_timeframe", "15m")
        symbol = config.get("symbol", "R_25")
        count = max(int(config.get("candles_count", 60)), 60)

        m5_candles = await self.client.get_candles(symbol, decision_tf, count)
        m15_candles = await self.client.get_candles(symbol, context_tf, count)
        m5_indicators = IndicatorService.analyze_with_config(m5_candles, indicator_configs)
        m15_indicators = IndicatorService.analyze_with_config(m15_candles, indicator_configs)
        m5_indicators["symbol"] = symbol
        m5_indicators["timeframe"] = decision_tf
        m15_indicators["symbol"] = symbol
        m15_indicators["timeframe"] = context_tf
        pre_analysis = run_pre_analysis(m5_indicators, m15_indicators, m5_candles, m15_candles)

        last_candle_epoch = m5_candles[-1]["time"]
        now = datetime.now(timezone.utc).timestamp()
        granularity = TIMEFRAME_TO_GRANULARITY.get(decision_tf, 300)
        next_entry_epoch = int(now / granularity) * granularity
        if next_entry_epoch <= now:
            next_entry_epoch += granularity
        last_candle_dt = datetime.fromtimestamp(last_candle_epoch, tz=BRT)
        next_entry_dt = datetime.fromtimestamp(next_entry_epoch, tz=BRT)

        return {
            "m5_candles": m5_candles, "m15_candles": m15_candles,
            "m5_indicators": m5_indicators, "m15_indicators": m15_indicators,
            "pre_analysis": pre_analysis,
            "last_candle_epoch": last_candle_epoch, "next_entry_epoch": next_entry_epoch,
            "last_candle_time": last_candle_dt.isoformat(),
            "next_entry_time": next_entry_dt.isoformat(),
        }

    async def _run_agent(self, config: dict, market_data: dict, repo: SignalRepository, session=None) -> dict:
        decision_tf = config.get("decision_timeframe", "5m")
        context_tf = config.get("context_timeframe", "15m")
        system_prompt = await build_system_prompt(config, session)
        user_msg = build_user_context(config, market_data["m5_indicators"],
            market_data["m15_indicators"], market_data["pre_analysis"],
            market_data.get("last_candle_time", ""), market_data.get("next_entry_time", ""))
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}]
        dispatcher = ToolDispatcher(repo, config["symbol"], decision_tf, context_tf)
        content = ""
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        async with httpx.AsyncClient() as http:
            for turn in range(MAX_TOOL_TURNS + 1):
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {"model": config["model"], "messages": messages, "tools": TOOLS}
                last_exc = None
                resp = None
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        r = await http.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60.0)
                        r.raise_for_status()
                        resp = r.json()
                        break
                    except Exception as e:
                        last_exc = e
                        logger.warning(f"OpenRouter falhou ({attempt}/{MAX_RETRIES}): {e}")
                        await asyncio.sleep(2 ** attempt)
                if resp is None:
                    raise RuntimeError(f"OpenRouter indisponível: {last_exc}")
                choice = resp["choices"][0]
                message = choice["message"]
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    content = (message.get("content") or "").strip()
                    break
                messages.append({"role": "assistant", "tool_calls": tool_calls, "content": message.get("content") or ""})
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    result = await dispatcher.dispatch(tool_name, args)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, ensure_ascii=False)})
                if turn == MAX_TOOL_TURNS:
                    payload2 = {"model": config["model"], "messages": messages}
                    r2 = await http.post(OPENROUTER_URL, headers=headers, json=payload2, timeout=60.0)
                    r2.raise_for_status()
                    content = (r2.json()["choices"][0]["message"].get("content") or "").strip()
        return self._parse_response(content, market_data.get("pre_analysis"))

    @staticmethod
    def _parse_response(content: str, pre_analysis: dict | None = None) -> dict:
        try:
            lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
            if len(lines) < 3:
                raise ValueError(f"Expected 3 lines, got {len(lines)}")
            direction_raw = lines[-2].upper()
            confidence_line = lines[-1]
            direction_map = {"COMPRA": "CALL", "VENDA": "PUT"}
            direction = direction_map.get(direction_raw)
            if direction is None:
                fallback = "CALL"
                if pre_analysis and pre_analysis.get("suggested_direction") in ("CALL", "PUT"):
                    fallback = pre_analysis["suggested_direction"]
                direction = fallback
            confidence_pct = int(confidence_line.replace("%", ""))
            confidence = confidence_pct / 100.0
            return {"confidence": confidence, "direction": direction, "raw_response": content}
        except (ValueError, IndexError):
            fallback = "CALL"
            if pre_analysis and pre_analysis.get("suggested_direction") in ("CALL", "PUT"):
                fallback = pre_analysis["suggested_direction"]
            return {"confidence": 0.0, "direction": fallback, "raw_response": content}
