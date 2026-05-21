import json
import os
import asyncio
import httpx

from deriv.client import DerivClient
from signals.repository import SignalRepository
from agent.tools import TOOLS
from agent.handlers import ToolHandlers
from agent.learning import build_context_block
from agent.prompts import build_system_prompt, build_user_context
from utils.logger import logger

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ITERATIONS = 10
MAX_RETRIES = 3


async def _call_openrouter(http: httpx.AsyncClient, model: str, messages: list[dict]) -> dict:
    api_key = os.environ["OPENROUTER_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
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


async def run_agent(client: DerivClient, config: dict, repo: SignalRepository) -> None:
    handlers = ToolHandlers(client, config, repo)
    learning_block = build_context_block(repo, config)
    system_prompt = build_system_prompt(config)
    # Passar o epoch do último candle para o contexto do LLM
    last_candle_epoch = getattr(handlers, '_last_candle_epoch', None)
    user_msg = build_user_context(config, learning_block, last_candle_epoch)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    # Reset analysis cache at start of each cycle
    handlers._last_analysis = None

    logger.info("=== Novo ciclo do agente iniciado ===")

    async with httpx.AsyncClient() as http:
        for iteration in range(1, MAX_ITERATIONS + 1):
            logger.info(f"Iteração {iteration}/{MAX_ITERATIONS} — chamando modelo {config['model']}")
            data = await _call_openrouter(http, config["model"], messages)

            choice = data["choices"][0]
            msg = choice["message"]
            tool_calls = msg.get("tool_calls") or []

            assistant_msg = {
                "role": "assistant",
                "content": msg.get("content") or "",
            }
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            if not tool_calls:
                final = msg.get("content", "").strip()
                logger.info(f"Decisão final do agente:\n{final}")
                return

            for tc in tool_calls:
                fn = tc["function"]
                name = fn["name"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                logger.info(f"Tool chamada: {name}({args})")
                result = await handlers.dispatch(name, args)
                logger.info(f"Tool resultado [{name}]: {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": name,
                    "content": json.dumps(result, default=str),
                })

        logger.warning(f"Ciclo terminou sem decisão final após {MAX_ITERATIONS} iterações")
