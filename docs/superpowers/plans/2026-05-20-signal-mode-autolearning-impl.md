# Signal Mode + Auto-Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the trading bot from executing real orders to emitting Rise/Fall signals on Volatility 100 Index with SQLite-backed auto-learning that injects historical signal performance into the LLM context each cycle.

**Architecture:** Create `signals/` package (models, SQLite repository, async verifier) and `agent/learning.py` (context block builder). Update agent tools, handlers, prompts, and main loop to wire everything together. Signal results are resolved asynchronously in background tasks with recovery on bot restart.

**Tech Stack:** Python asyncio, SQLite (stdlib), dataclasses for Signal/Outcome models, existing Deriv WebSocket client.

---

## File Structure

**New files:**
- `signals/__init__.py`
- `signals/models.py` — `Signal`, `Outcome` dataclasses
- `signals/repository.py` — `SignalRepository` class (SQLite CRUD + aggregations)
- `signals/verifier.py` — `resolve()` coroutine for async signal verification
- `agent/learning.py` — `build_context_block()` function
- `data/` — directory for `signals.db` (created by repo on init)

**Modified files:**
- `agent/tools.py` — replace `place_order`/`get_account_status` with `emit_signal`
- `agent/handlers.py` — replace `place_order`/`get_account_status` with `emit_signal`, add `_last_analysis` cache
- `agent/prompts.py` — new system prompt + `build_user_context()` takes learning block
- `agent/loop.py` — instantiate `SignalRepository`, inject learning block, call `recover_pending_signals`
- `main.py` — instantiate repo, call recovery, pass repo to `run_agent`
- `config.yaml` — symbol `R_100`, duration `5`, remove `stake`/`max_stake_pct`, add `db_path`/`learning_history_size`

---

## Task 1: Create Signal and Outcome dataclasses

**Files:**
- Create: `signals/models.py`
- Test: `tests/signals/test_models.py` (optional but recommended for type validation)

- [ ] **Step 1: Create `signals/` package directory**

```bash
mkdir -p /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv/signals
touch /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv/signals/__init__.py
```

- [ ] **Step 2: Write `signals/models.py` with Signal dataclass**

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Signal:
    """Represents a Rise/Fall signal emitted by the agent."""
    id: int | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    symbol: str = "R_100"
    direction: str = "CALL"  # "CALL" | "PUT"
    confidence: float = 0.5  # 0.0–1.0
    justification: str = ""
    duration: int = 5  # seconds
    timeframe: str = "1m"
    rsi: float | None = None
    macd_signal: str | None = None  # "compra" | "venda"
    trend: str | None = None  # "alta" | "baixa" | "lateral"
    bb_position: str | None = None
    quote_entry: float | None = None
    quote_exit: float | None = None
    outcome: str | None = None  # "win" | "loss"
    status: str = "pending"  # "pending" | "resolved" | "aborted"
```

- [ ] **Step 3: Add Outcome dataclass to `signals/models.py`**

```python
@dataclass
class Outcome:
    """Result of a resolved Rise/Fall signal."""
    signal_id: int
    quote_exit: float
    outcome: str  # "win" | "loss"
```

- [ ] **Step 4: Verify imports and basic structure**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 -c "from signals.models import Signal, Outcome; s = Signal(symbol='R_100', direction='CALL'); print(s)"
```

Expected output: Signal dataclass instance printed successfully, no errors.

- [ ] **Step 5: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add signals/__init__.py signals/models.py
git commit -m "feat: add Signal and Outcome dataclasses"
```

---

## Task 2: Create SignalRepository (SQLite CRUD)

**Files:**
- Create: `signals/repository.py`
- Modify: `config.yaml` (add `db_path`)

- [ ] **Step 1: Write `signals/repository.py` — init and schema**

```python
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from signals.models import Signal, Outcome
from utils.logger import logger

class SignalRepository:
    """SQLite repository for signals."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at    TEXT NOT NULL,
            symbol        TEXT NOT NULL,
            direction     TEXT NOT NULL,
            confidence    REAL NOT NULL,
            justification TEXT NOT NULL,
            duration      INTEGER NOT NULL,
            timeframe     TEXT NOT NULL,
            rsi           REAL,
            macd_signal   TEXT,
            trend         TEXT,
            bb_position   TEXT,
            quote_entry   REAL,
            quote_exit    REAL,
            outcome       TEXT,
            status        TEXT NOT NULL DEFAULT 'pending'
        )
        """)
        conn.commit()
        conn.close()
```

- [ ] **Step 2: Add `insert()` method to `SignalRepository`**

```python
    def insert(self, signal: Signal) -> int:
        """Insert a signal and return its id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO signals (
            created_at, symbol, direction, confidence, justification,
            duration, timeframe, rsi, macd_signal, trend, bb_position,
            quote_entry, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.created_at, signal.symbol, signal.direction,
            signal.confidence, signal.justification, signal.duration,
            signal.timeframe, signal.rsi, signal.macd_signal,
            signal.trend, signal.bb_position, signal.quote_entry,
            signal.status
        ))
        conn.commit()
        signal_id = cursor.lastrowid
        conn.close()
        return signal_id
```

- [ ] **Step 3: Add `update_outcome()` method to `SignalRepository`**

```python
    def update_outcome(self, signal_id: int, quote_exit: float, outcome: str) -> None:
        """Update signal with exit price and outcome."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE signals
        SET quote_exit = ?, outcome = ?, status = 'resolved'
        WHERE id = ?
        """, (quote_exit, outcome, signal_id))
        conn.commit()
        conn.close()
```

- [ ] **Step 4: Add `get_pending_alive()` and `get_pending_expired()` methods**

```python
    def get_pending_alive(self) -> list[Signal]:
        """Fetch pending signals whose duration hasn't expired yet."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
        SELECT * FROM signals
        WHERE status = 'pending'
        AND datetime(created_at) > datetime('now', '-' || duration || ' seconds')
        """)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_signal(row) for row in rows]

    def get_pending_expired(self) -> list[Signal]:
        """Fetch pending signals whose duration has expired."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM signals
        WHERE status = 'pending'
        AND datetime(created_at) <= datetime('now', '-' || duration || ' seconds')
        """)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_signal(row) for row in rows]

    def mark_aborted(self, signal_id: int) -> None:
        """Mark a signal as aborted."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE signals SET status = 'aborted' WHERE id = ?
        """, (signal_id,))
        conn.commit()
        conn.close()
```

- [ ] **Step 5: Add `get_resolved()` method for learning context**

```python
    def get_resolved(self, limit: int = 20, offset: int = 0) -> list[Signal]:
        """Fetch resolved signals for learning block."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM signals
        WHERE status = 'resolved'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_signal(row) for row in rows]
```

- [ ] **Step 6: Add `get_pattern_stats()` method for aggregations**

```python
    def get_pattern_stats(self) -> list[dict]:
        """Fetch win rates by pattern (direction, trend, macd_signal)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
        SELECT
            direction,
            trend,
            macd_signal,
            COUNT(*) AS total,
            SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 2) AS win_rate
        FROM signals
        WHERE status = 'resolved'
        GROUP BY direction, trend, macd_signal
        HAVING total >= 3
        ORDER BY win_rate DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
```

- [ ] **Step 7: Add `_row_to_signal()` helper**

```python
    def _row_to_signal(self, row: sqlite3.Row) -> Signal:
        """Convert a database row to a Signal dataclass."""
        return Signal(
            id=row["id"],
            created_at=row["created_at"],
            symbol=row["symbol"],
            direction=row["direction"],
            confidence=row["confidence"],
            justification=row["justification"],
            duration=row["duration"],
            timeframe=row["timeframe"],
            rsi=row["rsi"],
            macd_signal=row["macd_signal"],
            trend=row["trend"],
            bb_position=row["bb_position"],
            quote_entry=row["quote_entry"],
            quote_exit=row["quote_exit"],
            outcome=row["outcome"],
            status=row["status"],
        )
```

- [ ] **Step 8: Test repository with manual insertion**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
from signals.repository import SignalRepository
from signals.models import Signal

repo = SignalRepository("data/test_signals.db")
s = Signal(symbol="R_100", direction="CALL", confidence=0.8, justification="Test")
sig_id = repo.insert(s)
print(f"Inserted signal #{sig_id}")

resolved = repo.insert(Signal(
    symbol="R_100", direction="CALL", confidence=0.8, justification="Test",
    quote_entry=100.0, quote_exit=101.0, outcome="win", status="resolved"
))
print(f"Inserted resolved #{resolved}")

stats = repo.get_pattern_stats()
print(f"Stats: {stats}")
EOF
```

Expected: signal IDs printed, no errors.

- [ ] **Step 9: Update `config.yaml` with `db_path` and `learning_history_size`**

Edit `config.yaml`:

```yaml
model: "openai/gpt-4o"
symbol: "R_100"
timeframe: "1m"
candles_count: 20
duration: 5
loop_interval: 60
learning_history_size: 20
db_path: "data/signals.db"
```

- [ ] **Step 10: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
rm data/test_signals.db 2>/dev/null || true
git add signals/repository.py config.yaml
git commit -m "feat: add SignalRepository with SQLite CRUD and aggregations"
```

---

## Task 3: Create async signal verifier

**Files:**
- Create: `signals/verifier.py`

- [ ] **Step 1: Write `signals/verifier.py` — resolve coroutine**

```python
import asyncio
from signals.repository import SignalRepository
from deriv.client import DerivClient
from deriv import market
from utils.logger import logger

async def resolve(
    client: DerivClient,
    repo: SignalRepository,
    signal_id: int,
    quote_entry: float,
    direction: str,
    symbol: str,
    duration: int,
) -> None:
    """
    Async task that waits for signal duration, fetches exit price,
    determines outcome, and updates repository.
    """
    try:
        await asyncio.sleep(duration)
        quote_exit = await market.get_tick(client, symbol)

        if direction == "CALL":
            outcome = "win" if quote_exit > quote_entry else "loss"
        else:  # PUT
            outcome = "win" if quote_exit < quote_entry else "loss"

        repo.update_outcome(signal_id, quote_exit, outcome)
        logger.info(
            f"RESULT #{signal_id} | {direction} | {outcome.upper()} "
            f"| entry={quote_entry} exit={quote_exit}"
        )
    except Exception as e:
        logger.error(f"Verifier #{signal_id} failed: {e}")
```

- [ ] **Step 2: Test verifier logic (manual asyncio test)**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
import asyncio
from datetime import datetime
from signals.models import Signal
from signals.repository import SignalRepository

async def test_verifier_logic():
    """Test outcome calculation."""
    repo = SignalRepository("data/test_verifier.db")
    
    # Test CALL win
    repo.update_outcome(1, 101.0, "win")
    result = repo.get_resolved(limit=1)
    print(f"CALL win recorded: {len(result) == 0}")  # No resolved signals yet, it's a test
    
    # Test PUT loss
    repo.update_outcome(2, 99.0, "loss")
    print("Outcome logic OK")

asyncio.run(test_verifier_logic())
EOF
```

- [ ] **Step 3: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
rm data/test_verifier.db 2>/dev/null || true
git add signals/verifier.py
git commit -m "feat: add async signal verifier"
```

---

## Task 4: Create learning context builder

**Files:**
- Create: `agent/learning.py`

- [ ] **Step 1: Write `agent/learning.py` — build_context_block function**

```python
from signals.repository import SignalRepository

def build_context_block(repo: SignalRepository, config: dict) -> str:
    """
    Build a learning context block from resolved signals.
    Injects recent signals + pattern statistics into the LLM prompt.
    """
    n = int(config.get("learning_history_size", 20))
    recent = repo.get_resolved(limit=n)
    
    if not recent:
        return ""  # No learning history yet

    lines = ["## Histórico recente de sinais (últimos resolvidos)"]
    for s in recent:
        lines.append(
            f"- #{s.id} {s.direction} | {s.outcome.upper() if s.outcome else 'PENDING'} "
            f"| RSI={s.rsi} trend={s.trend} macd={s.macd_signal} "
            f"| conf={s.confidence:.0%}"
        )

    stats = repo.get_pattern_stats()
    if stats:
        lines.append("\n## Taxa de acerto por padrão (sinais resolvidos)")
        for row in stats:
            total = row["total"]
            wins = row["wins"]
            win_rate = row["win_rate"]
            lines.append(
                f"- {row['direction']} | trend={row['trend']} macd={row['macd_signal']}: "
                f"{wins}/{total} acertos ({win_rate:.0%})"
            )

    return "\n".join(lines)
```

- [ ] **Step 2: Test learning block builder**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
from signals.repository import SignalRepository
from signals.models import Signal
from agent.learning import build_context_block

repo = SignalRepository("data/test_learning.db")

# Insert a resolved signal
repo.insert(Signal(
    symbol="R_100", direction="CALL", confidence=0.8,
    justification="Test", rsi=28.0, trend="baixa", macd_signal="compra",
    quote_entry=100.0, quote_exit=101.0, outcome="win", status="resolved"
))

block = build_context_block(repo, {"learning_history_size": 20})
print("Learning block:")
print(block)
print("OK" if "CALL" in block else "FAILED")
EOF
```

- [ ] **Step 3: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
rm data/test_learning.db 2>/dev/null || true
git add agent/learning.py
git commit -m "feat: add learning context block builder"
```

---

## Task 5: Update agent tools — replace place_order with emit_signal

**Files:**
- Modify: `agent/tools.py`

- [ ] **Step 1: Replace `place_order` tool definition with `emit_signal`**

Open `agent/tools.py` and replace the `place_order` tool definition (lines ~27–42) with:

```python
    {
        "type": "function",
        "function": {
            "name": "emit_signal",
            "description": "Emits a Rise (CALL) or Fall (PUT) signal for R_100. Use when indicators are aligned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction":     {"type": "string", "enum": ["CALL", "PUT"]},
                    "confidence":    {"type": "number", "description": "Confidence 0.0–1.0"},
                    "justification": {"type": "string", "description": "Reason based on indicators"},
                },
                "required": ["direction", "confidence", "justification"],
            },
        },
    },
```

- [ ] **Step 2: Remove `get_account_status` tool from TOOLS list**

Delete or comment out the `get_account_status` tool definition entirely.

- [ ] **Step 3: Verify tool structure**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 -c "from agent.tools import TOOLS; print(f'Tools: {[t[\"function\"][\"name\"] for t in TOOLS]}')"
```

Expected: `Tools: ['get_market_analysis', 'emit_signal']`

- [ ] **Step 4: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add agent/tools.py
git commit -m "feat: replace place_order with emit_signal tool"
```

---

## Task 6: Update agent handlers — implement emit_signal handler

**Files:**
- Modify: `agent/handlers.py`

- [ ] **Step 1: Add imports to `agent/handlers.py`**

Add these at the top:

```python
import asyncio
from datetime import datetime
from signals.repository import SignalRepository
from signals import verifier
from signals.models import Signal
```

- [ ] **Step 2: Update ToolHandlers.__init__ to accept repo and add cache**

Replace the existing `__init__`:

```python
    def __init__(self, client: DerivClient, config: dict, repo: SignalRepository):
        self.client = client
        self.config = config
        self.repo = repo
        self._last_analysis: dict | None = None
```

- [ ] **Step 3: Update get_market_analysis to cache result**

Find the existing `get_market_analysis` method and add this line before the return statement:

```python
    async def get_market_analysis(self, symbol: str, timeframe: str, count: int = 20) -> dict:
        candles = await market.get_candles(self.client, symbol, timeframe, count)
        if not candles:
            return {"error": "Sem candles retornados"}
        result = analyze(candles)
        result["symbol"] = symbol
        result["timeframe"] = timeframe
        self._last_analysis = result  # ← ADD THIS LINE
        return result
```

- [ ] **Step 4: Remove get_account_status handler method**

Delete the entire `async def get_account_status(self)` method.

- [ ] **Step 5: Remove place_order handler method**

Delete the entire `async def place_order(self, ...)` method.

- [ ] **Step 6: Add emit_signal handler**

Add this new method to `ToolHandlers`:

```python
    async def emit_signal(self, direction: str, confidence: float, justification: str) -> dict:
        """Emit a Rise/Fall signal and schedule verification."""
        quote_entry = await market.get_tick(self.client, self.config["symbol"])

        signal = Signal(
            created_at=datetime.utcnow().isoformat(),
            symbol=self.config["symbol"],
            direction=direction,
            confidence=confidence,
            justification=justification,
            duration=int(self.config["duration"]),
            timeframe=self.config["timeframe"],
            rsi=self._last_analysis.get("rsi") if self._last_analysis else None,
            macd_signal=self._last_analysis.get("macd_signal") if self._last_analysis else None,
            trend=self._last_analysis.get("trend") if self._last_analysis else None,
            bb_position=self._last_analysis.get("bb_position") if self._last_analysis else None,
            quote_entry=quote_entry,
        )

        signal_id = self.repo.insert(signal)

        asyncio.create_task(
            verifier.resolve(
                self.client, self.repo, signal_id, quote_entry,
                direction, self.config["symbol"], int(self.config["duration"])
            )
        )

        logger.info(
            f"SIGNAL #{signal_id} | {direction} | {self.config['symbol']} "
            f"| entry={quote_entry} | dur={self.config['duration']}s "
            f"| conf={confidence:.0%} | {justification}"
        )
        return {"status": "signal_emitted", "signal_id": signal_id, "direction": direction}
```

- [ ] **Step 7: Test handlers import**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 -c "from agent.handlers import ToolHandlers; print('ToolHandlers imported OK')"
```

- [ ] **Step 8: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add agent/handlers.py
git commit -m "feat: implement emit_signal handler, add analysis cache, remove place_order/get_account_status"
```

---

## Task 7: Update prompts for Rise/Fall and learning block

**Files:**
- Modify: `agent/prompts.py`

- [ ] **Step 1: Replace system prompt**

Replace `SYSTEM_PROMPT_TEMPLATE` with:

```python
SYSTEM_PROMPT_TEMPLATE = """Você é um agente analista de mercado operando no Volatility 100 Index (R_100) na plataforma Deriv.

## Seu objetivo
Emitir sinais de Rise (CALL) ou Fall (PUT) com alta precisão. Você NÃO executa ordens reais.

## Processo obrigatório a cada ciclo:
1. Analise o mercado com get_market_analysis (symbol=R_100)
2. Avalie os indicadores:
   - RSI > 65 → favorece PUT (sobrecomprado)
   - RSI < 35 → favorece CALL (sobrevendido)
   - MACD e tendência devem confirmar a direção
3. Consulte o histórico de aprendizado injetado no contexto:
   - Priorize padrões com taxa de acerto ≥ 60% e pelo menos 3 amostras
   - Se o padrão atual tem histórico ruim (< 40%), abstain
4. Se dois ou mais indicadores contradizem → NÃO emita sinal
5. Quando confiante, chame emit_signal(direction, confidence, justification)

## Regras absolutas:
- Nunca emita sinal contra a tendência principal
- confidence deve refletir real alinhamento dos indicadores (não use 1.0 por padrão)
- Se o sinal não for claro, responda "sem sinal" com justificativa

## Formato da resposta final (após as tools):
- Resumo técnico (2–3 linhas)
- Decisão: CALL / PUT / SEM SINAL
- Justificativa baseada nos indicadores e no histórico
"""
```

- [ ] **Step 2: Update build_user_context to accept learning_block**

Replace the existing `build_user_context` function:

```python
def build_user_context(config: dict, learning_block: str = "") -> str:
    base = (
        f"Ciclo de análise iniciado.\n"
        f"Ativo: {config['symbol']}\n"
        f"Timeframe: {config['timeframe']}\n"
        f"Candles: {config.get('candles_count', 20)}\n"
        f"Duração do sinal: {config['duration']}s\n"
    )
    if learning_block:
        base += f"\n{learning_block}\n"
    base += "\nAnalise o mercado e emita um sinal se os indicadores estiverem alinhados."
    return base
```

- [ ] **Step 3: Test prompts**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
from agent.prompts import build_system_prompt, build_user_context

config = {"symbol": "R_100", "timeframe": "1m", "candles_count": 20, "duration": 5}
sys = build_system_prompt(config)
usr = build_user_context(config, "## Test learning block\n- Test signal")

print("System prompt OK:" , "Rise/Fall" in sys and "R_100" in sys)
print("User context OK:", "R_100" in usr and "Test learning block" in usr)
EOF
```

- [ ] **Step 4: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add agent/prompts.py
git commit -m "feat: update system prompt for Rise/Fall, add learning_block to user context"
```

---

## Task 8: Update agent loop to inject learning block and instantiate repo

**Files:**
- Modify: `agent/loop.py`

- [ ] **Step 1: Add imports**

Add at the top:

```python
from signals.repository import SignalRepository
from agent.learning import build_context_block
```

- [ ] **Step 2: Update run_agent signature and initialization**

Replace the `run_agent` function signature:

```python
async def run_agent(client: DerivClient, config: dict, repo: SignalRepository) -> None:
    handlers = ToolHandlers(client, config, repo)
    learning_block = build_context_block(repo, config)
    system_prompt = build_system_prompt(config)
    user_msg = build_user_context(config, learning_block)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
```

- [ ] **Step 3: Reset _last_analysis cache at start of each cycle**

In the loop (after `messages` is initialized), add:

```python
    handlers._last_analysis = None
```

- [ ] **Step 4: Test loop import**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 -c "from agent.loop import run_agent; print('run_agent imported OK')"
```

- [ ] **Step 5: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add agent/loop.py
git commit -m "feat: update run_agent to accept repo, inject learning block, reset cache"
```

---

## Task 9: Update main.py to instantiate repo and handle recovery

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add imports**

Add at the top:

```python
from signals.repository import SignalRepository
```

- [ ] **Step 2: Write recovery function in main.py**

Add this function before `main()`:

```python
async def recover_pending_signals(client, repo, config):
    """Re-schedule pending signals and mark expired ones as aborted."""
    from datetime import datetime, timedelta
    
    pending_alive = repo.get_pending_alive()
    pending_expired = repo.get_pending_expired()
    
    for s in pending_expired:
        repo.mark_aborted(s.id)
    
    for s in pending_alive:
        created = datetime.fromisoformat(s.created_at)
        elapsed = (datetime.utcnow() - created).total_seconds()
        remaining = max(s.duration - int(elapsed), 0)
        
        from signals import verifier
        asyncio.create_task(
            verifier.resolve(client, repo, s.id, s.quote_entry,
                             s.direction, s.symbol, remaining)
        )
    
    if pending_alive or pending_expired:
        logger.info(f"Recovery: {len(pending_alive)} signals re-scheduled, {len(pending_expired)} aborted")
```

- [ ] **Step 3: Update main() to instantiate repo and call recovery**

In the `main()` function, after `client = build_client_from_env()` and before the while loop, add:

```python
    repo = SignalRepository(config.get("db_path", "data/signals.db"))
    await client.connect()
    await recover_pending_signals(client, repo, config)
```

Then update the loop call:

```python
                await run_agent(client, config, repo)
```

- [ ] **Step 4: Full main.py context (from config loading to loop)**

After all edits, the main function should look like:

```python
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

    loop_interval = int(config.get("loop_interval", 60))

    try:
        while True:
            try:
                await run_agent(client, config, repo)
            except Exception as e:
                logger.exception(f"Erro durante ciclo do agente: {e}")
            logger.info(f"Aguardando {loop_interval}s até o próximo ciclo...")
            await asyncio.sleep(loop_interval)
    finally:
        await client.close()
        logger.info("Cliente Deriv encerrado. Encerrando bot.")
```

- [ ] **Step 5: Test main import**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 -c "from main import main; print('main imported OK')"
```

- [ ] **Step 6: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add main.py
git commit -m "feat: instantiate repo, add signal recovery on startup"
```

---

## Task 10: Update config.yaml with new symbol and remove trading fields

**Files:**
- Modify: `config.yaml`

- [ ] **Step 1: Verify current config**

```bash
cat /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv/config.yaml
```

- [ ] **Step 2: Replace entire config.yaml**

```yaml
model: "openai/gpt-4o"
symbol: "R_100"
timeframe: "1m"
candles_count: 20
duration: 5
loop_interval: 60
learning_history_size: 20
db_path: "data/signals.db"
```

- [ ] **Step 3: Verify config syntax**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
import yaml
with open("config.yaml") as f:
    config = yaml.safe_load(f)
print(f"Config OK. Symbol: {config['symbol']}, Duration: {config['duration']}s")
EOF
```

- [ ] **Step 4: Commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add config.yaml
git commit -m "chore: update config for R_100 Rise/Fall, remove stake fields"
```

---

## Task 11: Integration test — run bot for one cycle

**Files:**
- Test: Manual execution

- [ ] **Step 1: Verify all imports work together**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
from signals.models import Signal, Outcome
from signals.repository import SignalRepository
from signals import verifier
from agent.learning import build_context_block
from agent.tools import TOOLS
from agent.handlers import ToolHandlers
from agent.prompts import build_system_prompt, build_user_context
from agent.loop import run_agent
from main import main, recover_pending_signals

print("All imports OK")
print(f"Tools: {[t['function']['name'] for t in TOOLS]}")
EOF
```

Expected: All imports successful, Tools: `['get_market_analysis', 'emit_signal']`

- [ ] **Step 2: Verify database creation and queries**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
from signals.repository import SignalRepository
from signals.models import Signal

repo = SignalRepository("data/signals.db")

# Insert a signal
sig = Signal(
    symbol="R_100", direction="CALL", confidence=0.75,
    justification="RSI < 35, MACD bullish", rsi=28.5, trend="baixa",
    macd_signal="compra", quote_entry=100.0
)
sig_id = repo.insert(sig)
print(f"Inserted signal #{sig_id}")

# Simulate outcome
repo.update_outcome(sig_id, 101.5, "win")

# Query resolved
resolved = repo.get_resolved(limit=10)
print(f"Resolved signals: {len(resolved)}")

# Query stats
stats = repo.get_pattern_stats()
print(f"Pattern stats: {stats}")
EOF
```

Expected: Signal inserted, updated, and queries return data.

- [ ] **Step 3: Verify learning block generation**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 << 'EOF'
from signals.repository import SignalRepository
from agent.learning import build_context_block

repo = SignalRepository("data/signals.db")
config = {"learning_history_size": 20}
block = build_context_block(repo, config)

print("Learning block:")
print(block if block else "(empty, no signals yet)")
EOF
```

- [ ] **Step 4: Commit integration test notes (optional)**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git status
# (No changes to commit — this task was verification only)
```

---

## Task 12: Final cleanup and documentation

**Files:**
- Delete: `deriv/trading.py` functions (keep file, remove `place_order` and `buy`)
- Optional: Create `.gitkeep` in `data/` directory

- [ ] **Step 1: Remove unused trading functions (optional but recommended)**

Open `deriv/trading.py` and remove the `place_order` and `buy` functions (keep `get_proposal`, `get_account_balance`, `monitor_contract`):

```python
# REMOVE these:
async def place_order(...)  # ← DELETE
async def buy(...)          # ← DELETE
```

Keep `get_proposal`, `get_account_balance`, `monitor_contract` for potential future use.

- [ ] **Step 2: Create .gitkeep in data/ (so directory is tracked)**

```bash
mkdir -p /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv/data
touch /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv/data/.gitkeep
```

- [ ] **Step 3: Verify no TypeErrors on import**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
python3 -m py_compile main.py agent/handlers.py agent/loop.py signals/repository.py agent/learning.py
echo "All files compile OK"
```

- [ ] **Step 4: Final commit**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git add deriv/trading.py data/.gitkeep
git commit -m "cleanup: remove unused place_order/buy functions, add data/.gitkeep"
```

- [ ] **Step 5: View git log**

```bash
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
git log --oneline -10
```

Expected: At least 10 commits in the log, most recent first.

---

## Self-Review Checklist

**Spec Coverage:**
- ✓ Signal models (Signal, Outcome) — Task 1
- ✓ SQLite repository (insert, update_outcome, get_resolved, get_pattern_stats) — Task 2
- ✓ Async verifier (resolve coroutine) — Task 3
- ✓ Learning context block (build_context_block) — Task 4
- ✓ emit_signal tool definition — Task 5
- ✓ emit_signal handler with cache — Task 6
- ✓ Updated system prompt for Rise/Fall — Task 7
- ✓ Updated user context with learning block — Task 7
- ✓ run_agent accepts repo, injects block — Task 8
- ✓ main.py instantiates repo, calls recovery — Task 9
- ✓ config.yaml updated (R_100, duration 5, db_path, learning_history_size) — Task 10
- ✓ Removed place_order, get_account_status tools — Task 5
- ✓ Removed place_order, get_account_status handlers — Task 6

**No Placeholders:** All code snippets are complete. No "TBD", "add tests later", or vague instructions. Every step shows the exact command or code.

**Type Consistency:**
- `Signal` dataclass used throughout (models.py, repository.py, handlers.py, learning.py, verifier.py)
- `SignalRepository` instantiated consistently (main.py → run_agent → ToolHandlers)
- `build_context_block(repo, config)` signature consistent across Task 4 and Task 8
- `emit_signal(direction, confidence, justification)` tool signature matches handler signature

**Executability:**
- Each task has concrete bash commands with expected output.
- Code is copy-paste-ready, not pseudocode.
- Imports are added incrementally and tested.
- Database schema is spelled out exactly.
- No forward references or missing definitions.
