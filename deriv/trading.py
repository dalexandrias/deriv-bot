from deriv.client import DerivClient, DerivError
from utils.logger import logger


async def get_proposal(client: DerivClient, symbol: str, direction: str, stake: float, duration: int) -> dict:
    resp = await client._send({
        "proposal": 1,
        "amount": stake,
        "basis": "stake",
        "contract_type": direction,
        "currency": "USD",
        "duration": duration,
        "duration_unit": "s",
        "symbol": symbol,
    })
    return resp["proposal"]


async def get_account_balance(client: DerivClient) -> dict:
    resp = await client._send({"balance": 1})
    bal = resp["balance"]
    return {"balance": float(bal["balance"]), "currency": bal["currency"]}


async def monitor_contract(client: DerivClient, contract_id: int) -> dict:
    resp = await client._send({"proposal_open_contract": 1, "contract_id": contract_id})
    return resp.get("proposal_open_contract", {})
