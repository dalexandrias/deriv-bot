# Design: Modo Sinal + Auto-Aprendizado — Volatility 100 Rise/Fall

**Data:** 2026-05-20  
**Status:** Aprovado

---

## Contexto

O bot atual executa ordens reais via `place_order` no par `frxEURUSD`. O objetivo é:

1. Substituir execução de ordens por **emissão de sinais** (log/console apenas).
2. Trocar o ativo para **Volatility 100 Index (`R_100`)** na modalidade **Rise/Fall**.
3. Adicionar um **modo de auto-aprendizado** que acompanha o resultado real de cada sinal e injeta evidências históricas no contexto do LLM a cada ciclo.

---

## Arquitetura

### Pacotes novos

```
signals/
  __init__.py
  models.py       # dataclasses Signal, Outcome
  repository.py   # SQLite CRUD + get_pattern_stats
  verifier.py     # asyncio task que resolve o sinal

agent/
  learning.py     # build_context_block()  ← novo módulo
```

### Arquivos modificados

```
agent/tools.py    # emit_signal substitui place_order; remove get_account_status
agent/handlers.py # emit_signal; remove place_order/get_account_status
agent/prompts.py  # novo system prompt + recebe learning_block
agent/loop.py     # recebe repo, injeta learning_block
main.py           # instancia repo, chama recover_pending_signals
config.yaml       # símbolo R_100, remove stake/max_stake_pct, adiciona db_path/learning_history_size
```

---

## Fluxo de um ciclo

```
loop_interval (padrão 60s)
│
├─ 1. learning.build_context_block(repo, config)
│       └─ lê SQLite: últimos N sinais resolvidos + estatísticas por padrão
│
├─ 2. LLM recebe:
│       - system prompt (Rise/Fall, R_100, sem ordens reais)
│       - user context + bloco de aprendizado
│
├─ 3. LLM → get_market_analysis(R_100, timeframe)
│
├─ 4. LLM → emit_signal(direction, confidence, justification)
│       handlers.emit_signal:
│         a) get_tick(R_100) → quote_entry
│         b) INSERT signal status='pending' no SQLite
│         c) asyncio.create_task(verifier.resolve(...))
│         d) loga "SIGNAL #id CALL R_100 ..."
│
└─ 5. LLM responde texto final (resumo da decisão)

Em paralelo (background):
  verifier.resolve(signal_id, ...)
    await sleep(duration)
    quote_exit = get_tick(symbol)
    outcome = win/loss pela regra Rise/Fall
    UPDATE signal status='resolved'
    loga "RESULT #id CALL WIN entry=X exit=Y"
```

---

## Schema SQLite

```sql
CREATE TABLE IF NOT EXISTS signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    direction     TEXT NOT NULL,     -- "CALL" | "PUT"
    confidence    REAL NOT NULL,     -- 0.0–1.0
    justification TEXT NOT NULL,
    duration      INTEGER NOT NULL,  -- segundos
    timeframe     TEXT NOT NULL,
    rsi           REAL,
    macd_signal   TEXT,              -- "compra" | "venda"
    trend         TEXT,              -- "alta" | "baixa" | "lateral"
    bb_position   TEXT,
    quote_entry   REAL,
    quote_exit    REAL,
    outcome       TEXT,              -- "win" | "loss" | NULL
    status        TEXT NOT NULL DEFAULT 'pending'  -- "pending" | "resolved" | "aborted"
);
```

**Regra Rise/Fall:**
- `CALL` → win se `quote_exit > quote_entry`
- `PUT`  → win se `quote_exit < quote_entry`
- Empate → loss (conservador, igual à Deriv real)

---

## Tool `emit_signal`

Substitui `place_order`. Parâmetros:

| Campo | Tipo | Descrição |
|---|---|---|
| `direction` | `"CALL"\|"PUT"` | Rise ou Fall |
| `confidence` | `float` 0–1 | Confiança declarada pelo LLM |
| `justification` | `string` | Razão baseada nos indicadores |

`get_account_status` também é removido (sem stake, saldo irrelevante).

**Cache de análise:** `ToolHandlers` mantém `self._last_analysis: dict | None = None`. O método `get_market_analysis` salva o resultado nesse atributo antes de retorná-lo ao LLM. Quando `emit_signal` é chamado no mesmo ciclo, lê `self._last_analysis` para gravar os indicadores no SQLite — sem segunda chamada à API Deriv. Se por algum motivo o cache estiver vazio, os campos de indicadores ficam `None` no banco (não é erro fatal).

---

## Verifier

`signals/verifier.py` — coroutine em background:

1. `await asyncio.sleep(duration)`
2. `quote_exit = await market.get_tick(client, symbol)`
3. Calcula `outcome` pela regra Rise/Fall
4. `repo.update_outcome(signal_id, quote_exit, outcome)`
5. Loga resultado

**Tratamento de falha:** exceção é capturada e logada; sinal permanece `pending` até o recovery na próxima inicialização.

---

## Recovery na inicialização

`main.py` chama `recover_pending_signals(client, repo, config)` antes do loop principal:

- Sinais `pending` cujo tempo ainda não expirou → re-agenda verifier com tempo restante.
- Sinais `pending` já expirados → marca como `aborted`.

---

## Auto-Aprendizado

### Bloco injetado no contexto a cada ciclo

```
## Histórico recente de sinais (últimos N resolvidos)
- #42 CALL | WIN  | RSI=28.3 trend=baixa macd=compra | conf=80%
- #41 PUT  | LOSS | RSI=55.1 trend=lateral macd=venda | conf=65%
...

## Taxa de acerto por padrão (sinais resolvidos)
- CALL | trend=baixa  macd=compra: 8/10 acertos (80%)
- PUT  | trend=alta   macd=venda:  5/8  acertos (63%)
- CALL | trend=lateral macd=compra: 2/6 acertos (33%)
```

### Query de agregação

```sql
SELECT direction, trend, macd_signal,
       COUNT(*) AS total,
       SUM(CASE WHEN outcome='win' THEN 1 END) AS wins,
       ROUND(AVG(CASE WHEN outcome='win' THEN 1.0 ELSE 0 END), 2) AS win_rate
FROM signals
WHERE status = 'resolved'
GROUP BY direction, trend, macd_signal
HAVING total >= 3
ORDER BY win_rate DESC
```

Padrões com menos de 3 amostras são omitidos para evitar viés de amostra pequena.

### Instrução no system prompt

- Priorizar padrões com win_rate ≥ 60% e ≥ 3 amostras.
- Abster-se se o padrão atual tem win_rate < 40%.

---

## System Prompt (resumo)

- Ativo: R_100, modalidade Rise/Fall
- Sem execução de ordens reais
- Processo: get_market_analysis → avaliar indicadores → consultar histórico → emit_signal ou "sem sinal"
- RSI > 65 → favorece PUT; RSI < 35 → favorece CALL
- Dois indicadores contraditórios → não emite

---

## Config final (`config.yaml`)

```yaml
model: "openai/gpt-4o"
symbol: "R_100"
timeframe: "1m"
candles_count: 20
duration: 5                  # segundos (Rise/Fall curto no Volatility 100)
loop_interval: 60
learning_history_size: 20    # N últimos sinais no prompt
db_path: "data/signals.db"
```

Campos removidos: `stake`, `max_stake_pct`.

---

## Remoções definitivas

| O que | Onde | Motivo |
|---|---|---|
| `place_order` tool | `agent/tools.py` | Substituído por `emit_signal` |
| `place_order` handler | `agent/handlers.py` | Idem |
| `get_account_status` tool | `agent/tools.py` | Saldo não é mais relevante |
| `get_account_status` handler | `agent/handlers.py` | Idem |
| `stake`, `max_stake_pct` | `config.yaml` | Sem ordens reais |

`deriv/trading.py` é mantido intacto (tem `monitor_contract` útil futuramente).

---

## Dependências

Nenhuma dependência nova. SQLite é stdlib Python. Todos os pacotes já estão em `requirements.txt`.

## Notas de implementação

- `SignalRepository.__init__` deve criar o diretório de `db_path` se não existir (`Path(db_path).parent.mkdir(parents=True, exist_ok=True)`).
- `ToolHandlers._last_analysis` deve ser resetado para `None` no início de cada ciclo (em `run_agent`, antes do loop de iterações), para não vazar análise de um ciclo para o próximo.
