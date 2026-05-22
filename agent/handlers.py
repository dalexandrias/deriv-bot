import asyncio
from datetime import datetime, UTC
from deriv.client import DerivClient
from deriv import market, trading
from indicators.technical import analyze
from signals.repository import SignalRepository
from signals import verifier
from signals.models import Signal
from utils.logger import logger


class ToolHandlers:
    """
    Tool handlers are no longer used in the new architecture.
    The bot directly calls emit_signal in main.py instead of using LLM tool calls.
    This class is kept for backward compatibility but is not used.
    """
    def __init__(self, client: DerivClient, config: dict, repo: SignalRepository):
        self.client = client
        self.config = config
        self.repo = repo

    async def dispatch(self, name: str, args: dict) -> dict:
        return {"error": "Tools are no longer supported in the new architecture"}
