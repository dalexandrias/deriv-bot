import asyncio
import json
import os
from datetime import datetime, timezone, timedelta

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import BotConfig
from app.agent.memory_repository import (
    get_recent_cycles,
    get_last_reflection,
    count_cycles_since,
    insert_cycle as _unused,
    insert_reflection,
    upsert_lessons,
)
from app.signals.repository import SignalRepository
from app.agent.prompts import build_reflection_prompt
from app.events.protocol import EventType
from app.events.publisher import publish

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class ReflectionService:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("ReflectionService iniciado")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ReflectionService parado")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(300)
                if not self._running:
                    return
                config = await self._load_config()
                if not config.get("reflection_enabled", False):
                    continue
                if await self._should_reflect(config):
                    await self._reflect(config)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"Erro no reflection loop: {e}")
                await asyncio.sleep(60)

    async def _load_config(self) -> dict:
        async with self.session_factory() as session:
            result = await session.execute(select(BotConfig))
            configs = result.scalars().all()
            config = {}
            for cfg in configs:
                try:
                    config[cfg.key] = json.loads(cfg.value)
                except (json.JSONDecodeError, TypeError):
                    config[cfg.key] = cfg.value
            return config

    async def _should_reflect(self, config: dict) -> bool:
        try:
            n_cycles = int(config.get("reflection_n_cycles", 50))
            max_hours = int(config.get("reflection_max_hours", 24))
        except (ValueError, TypeError):
            n_cycles, max_hours = 50, 24

        async with self.session_factory() as session:
            last = await get_last_reflection(session)

            cycles_count = await count_cycles_since(session, last.id if last else None)
            if cycles_count >= n_cycles:
                return True

            if last and last.created_at:
                deadline = last.created_at + timedelta(hours=max_hours)
                if datetime.now(timezone.utc) >= deadline:
                    return True

            if last is None:
                return cycles_count >= max(10, n_cycles // 5)

            return False

    async def _reflect(self, config: dict) -> None:
        logger.info("Iniciando reflexão de memória de longo prazo...")

        model = config.get("reflection_model", config.get("model", "deepseek/deepseek-v4-flash"))
        lessons_max = int(config.get("reflection_lessons_max", 10))
        trigger = "scheduled"

        async with self.session_factory() as session:
            repo = SignalRepository(session)
            cycles = await get_recent_cycles(session, limit=100)
            signals = await repo.get_signals_filtered(limit=50, outcome="any")

            if not cycles and not signals:
                logger.info("Reflexão ignorada: sem dados suficientes")
                return

            prompt = build_reflection_prompt(cycles, signals)
            raw_response = await self._call_llm(model, prompt)

            if not raw_response:
                logger.warning("Reflexão falhou: sem resposta do LLM")
                return

            lessons = self._parse_lessons(raw_response, lessons_max)
            if not lessons:
                logger.info("Reflexão concluída: nenhuma lição extraída")
                return

            reflection_id = await insert_reflection(
                session,
                cycles_analyzed=len(cycles),
                model_used=model,
                trigger=trigger,
                raw_response=raw_response,
            )
            await upsert_lessons(session, reflection_id, lessons)
            await session.commit()

            logger.success(f"Reflexão concluída: {len(lessons)} lições (reflection_id={reflection_id})")
            publish(EventType.LESSON_LEARNED, {
                "count": len(lessons),
                "reflection_id": reflection_id,
                "trigger": trigger,
            })

    async def _call_llm(self, model: str, prompt: str) -> str | None:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            logger.warning("Reflexão abortada: OPENROUTER_API_KEY não configurada")
            return None

        try:
            async with httpx.AsyncClient() as http:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                }
                r = await http.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120.0)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"] or ""
        except Exception as e:
            logger.error(f"Erro ao chamar LLM reflexor: {e}")
            return None

    @staticmethod
    def _parse_lessons(raw: str, max_lessons: int) -> list[dict]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = 1 if lines[0].startswith("```") else 0
            end = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            text = "\n".join(lines[start:end])

        try:
            lessons = json.loads(text)
            if not isinstance(lessons, list):
                return []
            parsed = []
            for l in lessons[:max_lessons]:
                if not isinstance(l, dict):
                    continue
                content = l.get("content", "").strip()
                topic = l.get("topic", "").strip()
                if not content or not topic:
                    continue
                try:
                    sample_size = int(l.get("sample_size", 0))
                except (ValueError, TypeError):
                    sample_size = 0
                try:
                    confidence = max(0.0, min(1.0, float(l.get("confidence", 0.5))))
                except (ValueError, TypeError):
                    confidence = 0.5
                parsed.append({
                    "content": content,
                    "topic": topic,
                    "sample_size": sample_size,
                    "confidence": confidence,
                })
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Não foi possível parsear lições do LLM: {e}")
            return []
