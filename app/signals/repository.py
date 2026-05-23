from datetime import datetime, timezone

from sqlalchemy import Integer, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Signal as SignalORM, Candle as CandleORM
from app.signals.models import SignalCreate


class SignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ CRUD

    async def insert_signal(self, data: SignalCreate) -> int:
        sig = SignalORM(
            symbol=data.symbol,
            timeframe=data.timeframe,
            direction=data.direction,
            confidence=data.confidence,
            duration=data.duration,
            status=data.status,
            rsi=data.rsi,
            bb_position=data.bb_position,
            adx=data.adx,
            atr_pct=data.atr_pct,
            price_vs_ema50=data.price_vs_ema50,
            macd_line=data.macd_line,
            macd_signal=data.macd_signal,
            macd_histogram=data.macd_histogram,
            regime=data.regime,
            time_window=data.time_window,
            m15_bias=data.m15_bias,
            confluence_score=data.confluence_score,
            strategy=data.strategy,
            entry_candle_time=data.entry_candle_time,
            reasoning=data.reasoning,
        )
        self.session.add(sig)
        await self.session.flush()
        return sig.id

    async def get_signal_by_id(self, signal_id: int) -> SignalORM | None:
        result = await self.session.execute(
            select(SignalORM).where(SignalORM.id == signal_id)
        )
        return result.scalar_one_or_none()

    async def update_outcome(
        self,
        signal_id: int,
        entry_price: float,
        exit_price: float,
        outcome: str,
    ) -> None:
        result = await self.session.execute(
            select(SignalORM).where(SignalORM.id == signal_id)
        )
        sig = result.scalar_one_or_none()
        if sig is None:
            return
        sig.entry_price = entry_price
        sig.exit_price = exit_price
        sig.outcome = outcome
        sig.status = "resolved"
        sig.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_aborted(self, signal_id: int) -> None:
        result = await self.session.execute(
            select(SignalORM).where(SignalORM.id == signal_id)
        )
        sig = result.scalar_one_or_none()
        if sig is None:
            return
        sig.status = "aborted"
        sig.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()

    # ---------------------------------------------------------------- queries

    async def get_pending_alive(self) -> list[SignalORM]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(SignalORM).where(
                and_(
                    SignalORM.status == "pending",
                    (now - SignalORM.created_at) < SignalORM.duration,
                )
            )
        )
        return list(result.scalars().all())

    async def get_pending_expired(self) -> list[SignalORM]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(SignalORM).where(
                and_(
                    SignalORM.status == "pending",
                    (now - SignalORM.created_at) >= SignalORM.duration,
                )
            )
        )
        return list(result.scalars().all())

    async def get_signals_filtered(
        self,
        limit: int = 20,
        outcome: str | None = None,
        direction: str | None = None,
    ) -> list[dict]:
        query = select(SignalORM).order_by(SignalORM.id.desc()).limit(limit)
        if outcome is not None:
            query = query.where(SignalORM.outcome == outcome)
        if direction is not None:
            query = query.where(SignalORM.direction == direction)
        result = await self.session.execute(query)
        return [_orm_to_dict(s) for s in result.scalars().all()]

    async def get_overall_stats(self) -> dict:
        result = await self.session.execute(
            select(
                func.count(SignalORM.id).label("total"),
                func.coalesce(
                    func.sum(func.cast(SignalORM.outcome == "win", Integer)), 0
                ).label("wins"),
                func.coalesce(
                    func.sum(func.cast(SignalORM.outcome == "loss", Integer)), 0
                ).label("losses"),
                func.coalesce(func.avg(SignalORM.confidence), 0).label("avg_confidence"),
            ).where(SignalORM.status == "resolved")
        )
        row = result.one()
        total = row.total or 0
        wins = row.wins or 0
        losses = row.losses or 0
        win_rate = round(wins / total, 2) if total > 0 else 0.0
        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_confidence": round(row.avg_confidence or 0, 2),
        }

    async def get_recent_signals(self, limit: int = 20) -> list[dict]:
        result = await self.session.execute(
            select(SignalORM).order_by(SignalORM.id.desc()).limit(limit)
        )
        return [_orm_to_dict(s) for s in result.scalars().all()]

    # -------------------------------------------------------------- candles

    async def get_candles_range(
        self,
        symbol: str,
        timeframe: str,
        count: int = 60,
        before_epoch: datetime | None = None,
    ) -> list[dict]:
        query = (
            select(CandleORM)
            .where(
                CandleORM.symbol == symbol,
                CandleORM.timeframe == timeframe,
            )
            .order_by(CandleORM.epoch.desc())
            .limit(count)
        )
        if before_epoch is not None:
            query = query.where(CandleORM.epoch < before_epoch)
        result = await self.session.execute(query)
        candles = list(result.scalars().all())
        candles.reverse()  # oldest first
        return [_candle_to_dict(c) for c in candles]

    async def upsert_candles(
        self,
        candles: list[dict],
        symbol: str,
        timeframe: str,
    ) -> None:
        for c in candles:
            epoch = c["time"]
            result = await self.session.execute(
                select(CandleORM).where(
                    CandleORM.symbol == symbol,
                    CandleORM.timeframe == timeframe,
                    CandleORM.epoch == epoch,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.open = c["open"]
                existing.high = c["high"]
                existing.low = c["low"]
                existing.close = c["close"]
            else:
                self.session.add(
                    CandleORM(
                        symbol=symbol,
                        timeframe=timeframe,
                        epoch=epoch,
                        open=c["open"],
                        high=c["high"],
                        low=c["low"],
                        close=c["close"],
                    )
                )
        await self.session.flush()


# ------------------------------------------------------------------ helpers


def _orm_to_dict(sig: SignalORM) -> dict:
    return {
        "id": sig.id,
        "symbol": sig.symbol,
        "timeframe": sig.timeframe,
        "direction": sig.direction,
        "confidence": sig.confidence,
        "duration": sig.duration,
        "status": sig.status,
        "entry_price": sig.entry_price,
        "exit_price": sig.exit_price,
        "outcome": sig.outcome,
        "reasoning": sig.reasoning,
        "rsi": sig.rsi,
        "bb_position": sig.bb_position,
        "adx": sig.adx,
        "atr_pct": sig.atr_pct,
        "price_vs_ema50": sig.price_vs_ema50,
        "macd_line": sig.macd_line,
        "macd_signal": sig.macd_signal,
        "macd_histogram": sig.macd_histogram,
        "regime": sig.regime,
        "time_window": sig.time_window,
        "m15_bias": sig.m15_bias,
        "confluence_score": sig.confluence_score,
        "strategy": sig.strategy,
        "entry_candle_time": sig.entry_candle_time,
        "created_at": sig.created_at.isoformat() if sig.created_at else None,
        "resolved_at": sig.resolved_at.isoformat() if sig.resolved_at else None,
    }


def _candle_to_dict(c: CandleORM) -> dict:
    return {
        "time": int(c.epoch.timestamp()) if c.epoch else None,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
    }
