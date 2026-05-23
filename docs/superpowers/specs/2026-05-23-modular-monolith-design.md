# Modular Monolith Design - Deriv Trading Bot

**Date:** 2026-05-23
**Status:** Approved
**Decision:** Monolito modular com PostgreSQL + FastAPI, deploy único via Coolify

## Context

O bot atual é um monolito Python que conecta na Deriv via WebSocket, usa SQLite local, agente LLM via OpenRouter, e dashboard TUI via Unix socket. Os objetivos da refatoração:

- Escalar operações (múltiplos bots no futuro)
- Resiliência (reiniciar bot sem perder dados)
- Plugar frontend externo
- Observabilidade para produção

## Arquitetura

### Estrutura de Diretórios

```
AutomationAnalyseDeriv/
├── app/
│   ├── main.py              # FastAPI entrypoint + lifespan
│   ├── config.py            # pydantic-settings (env + DB)
│   ├── api/
│   │   ├── router.py        # Router principal
│   │   ├── bot.py           # on/off, status
│   │   ├── collector.py     # symbols, timeframes, status coleta
│   │   ├── signals.py       # histórico, stats
│   │   └── indicators.py    # CRUD configs de indicadores
│   ├── collector/
│   │   ├── service.py       # Loop: WebSocket Deriv → DB
│   │   └── deriv_client.py  # Conexão WebSocket
│   ├── agent/
│   │   ├── service.py       # Loop agente LLM
│   │   ├── pre_analysis.py  # Análise programática
│   │   ├── prompts.py       # Prompts
│   │   ├── tools.py         # Ferramentas LLM
│   │   └── learning.py      # Aprendizado
│   ├── indicators/
│   │   ├── service.py       # Cálculo de indicadores (configs do DB)
│   │   └── technical.py     # TA wrapper
│   ├── signals/
│   │   ├── models.py        # Dataclasses
│   │   ├── repository.py    # Operações PostgreSQL
│   │   └── verifier.py      # Verificação WIN/LOSS
│   ├── db/
│   │   ├── connection.py    # SQLAlchemy async engine + sessions
│   │   ├── models.py        # ORM models
│   │   └── migrations/      # Alembic
│   ├── events/
│   │   ├── protocol.py      # Tipos de eventos
│   │   └── publisher.py     # SSE para frontends externos
│   └── dashboard/           # TUI mantida para uso local
├── alembic.ini
├── Dockerfile
├── pyproject.toml
└── config.yaml              # Defaults iniciais
```

### Container Único

- FastAPI + Uvicorn na porta 8000
- Collector como background task (asyncio)
- Agent como background task (asyncio)
- PostgreSQL externo (Coolify managed DB)
- SQLite removido desde o início

## Modelo de Dados

### bot_config

| Coluna    | Tipo         | Descrição                    |
|-----------|-------------|------------------------------|
| id        | SERIAL PK   |                              |
| key       | VARCHAR UNIQUE | Chave da configuração     |
| value     | JSONB        | Valor (string, number, etc) |
| updated_at| TIMESTAMPTZ  |                              |

**Chaves padrão:** symbol, decision_timeframe, context_timeframe, loop_interval, duration, min_confidence, model, candle_settle_delay, candles_count

### indicator_config

| Coluna         | Tipo          | Descrição                         |
|----------------|---------------|-----------------------------------|
| id             | SERIAL PK     |                                   |
| name           | VARCHAR UNIQUE | Nome do indicador (ex: RSI_14)   |
| indicator_type | VARCHAR       | RSI, MACD, BB, EMA, ADX, ATR     |
| parameters     | JSONB         | Parâmetros específicos            |
| enabled        | BOOLEAN       | Indicador ativo/inativo           |
| created_at     | TIMESTAMPTZ   |                                   |
| updated_at     | TIMESTAMPTZ   |                                   |

**Exemplos de parameters:**
- RSI: `{"period": 14}`
- MACD: `{"fast": 12, "slow": 26, "signal": 9}`
- BB: `{"period": 20, "std_dev": 2}`
- EMA: `{"period": 50}`
- ADX: `{"period": 14}`
- ATR: `{"period": 14}`

### candle

| Coluna     | Tipo          | Descrição               |
|------------|---------------|-------------------------|
| id         | SERIAL PK     |                         |
| symbol     | VARCHAR       | Ex: R_25               |
| timeframe  | VARCHAR       | Ex: 5m, 15m            |
| epoch      | TIMESTAMPTZ   | Abertura da vela       |
| open       | DECIMAL       |                         |
| high       | DECIMAL       |                         |
| low        | DECIMAL       |                         |
| close      | DECIMAL       |                         |
| volume     | INTEGER       |                         |
| created_at | TIMESTAMPTZ   |                         |

**UNIQUE(symbol, timeframe, epoch)**

### signal

| Coluna      | Tipo          | Descrição                        |
|-------------|---------------|----------------------------------|
| id          | SERIAL PK     |                                  |
| symbol      | VARCHAR       |                                  |
| timeframe   | VARCHAR       |                                  |
| direction   | VARCHAR       | CALL / PUT                      |
| confidence  | DECIMAL       | 0.0 a 1.0                       |
| entry_price | DECIMAL       |                                  |
| exit_price  | DECIMAL       | NULL até resolução              |
| outcome     | VARCHAR       | WIN / LOSS / PENDING / ABORTED  |
| status      | VARCHAR       | pending / resolved / aborted    |
| duration    | INTEGER       | Segundos                        |
| reasoning   | TEXT          | Justificativa do LLM            |
| created_at  | TIMESTAMPTZ   |                                  |
| resolved_at | TIMESTAMPTZ   | NULL até resolução              |

## APIs REST

Prefixo: `/api/v1/`

### Bot

| Método | Endpoint             | Descrição                    |
|--------|----------------------|------------------------------|
| POST   | /bot/start           | Inicia o loop do agente      |
| POST   | /bot/stop            | Pausa o agente               |
| GET    | /bot/status          | Status + último ciclo + uptime|

### Bot Config

| Método | Endpoint               | Descrição                  |
|--------|------------------------|----------------------------|
| GET    | /bot/config            | Lista todas as configs     |
| PATCH  | /bot/config            | Atualiza configs (JSON body)|
| GET    | /bot/config/{key}      | Valor de uma config        |

### Indicators

| Método | Endpoint                      | Descrição                  |
|--------|-------------------------------|----------------------------|
| GET    | /indicators                   | Lista todos                |
| POST   | /indicators                   | Cria indicador customizado |
| PATCH  | /indicators/{id}              | Atualiza params ou enabled |
| DELETE | /indicators/{id}              | Remove indicador           |
| POST   | /indicators/reset-defaults    | Volta ao padrão            |

### Collector

| Método | Endpoint               | Descrição                       |
|--------|------------------------|---------------------------------|
| GET    | /collector/status      | Conexão + symbols coletando     |
| PATCH  | /collector/config      | Altera symbols/timeframes       |

### Signals

| Método | Endpoint               | Descrição                          |
|--------|------------------------|------------------------------------|
| GET    | /signals               | Lista com filtros                  |
| GET    | /signals/{id}          | Detalhe                            |
| GET    | /signals/stats         | Win rate, total, streak, por tf    |

### Observabilidade

| Método | Endpoint          | Descrição                    |
|--------|-------------------|------------------------------|
| GET    | /health           | Health check (DB + Deriv WS) |
| GET    | /metrics          | Métricas Prometheus          |

### Eventos

| Método | Endpoint            | Descrição                        |
|--------|---------------------|----------------------------------|
| GET    | /events/stream      | SSE: sinais, status, erros       |

**Resposta padrão:**
```json
{"data": {...}, "error": null}
```

**Autenticação:** Nenhuma por agora (rede interna). Preparado para middleware futuro.

## Fluxo de Dados

### Collector

1. Conecta WebSocket na Deriv
2. Inscreve nos symbols/timeframes do DB (`bot_config`)
3. Vela fechada → UPSERT na tabela `candle`
4. Se config mudar via API → recarrega subscription sem reconectar
5. Auto-reconnect com backoff exponencial

### Agent

1. Lê configs do DB (symbol, timeframe, indicadores habilitados + parâmetros)
2. Busca candles do PostgreSQL (não vai na Deriv para dados históricos)
3. Calcula indicadores usando `indicator_config` do DB
4. Roda pre-analysis → LLM → gera sinal
5. Salva sinal como `pending` no DB
6. Espera vela fechar → busca candle de verificação no DB
7. Marca sinal WIN/LOSS
8. Publica evento via SSE

### Startup (FastAPI lifespan)

1. Conecta ao PostgreSQL
2. Roda migrations Alembic automaticamente
3. Popula configs/indicadores defaults se DB vazio
4. Inicia collector (background task)
5. Inicia agent se `bot_status=running` no DB
6. FastAPI pronto na porta 8000

## Deploy no Coolify

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install .
COPY . .
CMD ["uvicorn", "app.main:api", "--host", "0.0.0.0", "--port", "8000"]
```

### Variáveis de Ambiente

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/deriv
DERIV_APP_ID=1089
DERIV_TOKEN=xxx
OPENROUTER_API_KEY=xxx
```

### Health Check no Coolify

`GET /api/v1/health` → verifica conexão DB + status WebSocket Deriv

### Observabilidade

- Logs estruturados JSON em stdout → Coolify captura
- Métricas Prometheus em `/api/v1/metrics`
- SSE para frontends em tempo real

## Decisões Tomadas

1. **Monolito modular** ao invés de MS separados — 1 instância de cada, VM única, sem overhead de comunicação entre serviços
2. **PostgreSQL** como única fonte de dados — sem SQLite
3. **FastAPI** para APIs REST + SSE — async nativo, documentação automática
4. **SQLAlchemy async** + **Alembic** para ORM e migrations
5. **pydantic-settings** para configuração (env vars + DB)
6. **Config no DB** como fonte de verdade — config.yaml só para defaults iniciais
7. **Indicadores configuráveis** via DB — parâmetros e enabled por indicador
8. **Dashboard TUI mantida** — uso local/debug, não afeta APIs

## Limites para Futuro Split em MS

Os pacotes já têm interfaces claras. Se no futuro precisar separar:

- `collector/` vira um MS independente (basta adicionar HTTP server)
- `agent/` vira um MS independente (basta adicionar HTTP server)
- `db/models.py` vai para um pacote shared ou lib interna
- As APIs REST já são o contrato entre os serviços
