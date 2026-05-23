# Dashboard TUI para Bot Deriv

## Instalação

Instale a dependência do Textual:

```bash
pip install textual
```

Ou se estiver usando ambiente virtual:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uso

### 1. Rodar o bot (backend)

O bot agora inclui um servidor de eventos via Unix socket:

```bash
python main.py
```

O bot criará um socket em `~/.deriv-bot/events.sock` e começará a publicar eventos.

### 2. Conectar o dashboard (TUI)

Em outro terminal, conecte a interface TUI:

```bash
python -m dashboard
```

Ou:

```bash
python dashboard/__main__.py
```

### 3. Usar a interface

- **Tab Mercado**: Indicadores técnicos em tempo real (M5/M15) + pré-análise
- **Tab Sinais Ativos**: Sinais pendentes com countdown
- **Tab Histórico**: Últimos sinais com resultados
- **Tab Stats**: Win rate geral e por regime/estratégia
- **Tab Logs**: Logs do bot em tempo real

**Atalhos**:
- `q` - Sair do dashboard
- `r` - Atualizar estatísticas

### 4. Desconectar/reconectar

Você pode desconectar o dashboard (Ctrl+C) e reconectar depois — o bot continua rodando.

O dashboard reconecta automaticamente se perder a conexão com o bot.

## Arquitetura

```
Bot (main.py)                  Dashboard (python -m dashboard)
     |                                    |
     v                                    ^
EventServer                         EventClient
(Unix socket)                     (recebe eventos)
     |                                    |
     +----> publishes events ---->       |
           (status, market,            |
            signal_emitted,         DashboardApp
            signal_resolved)             |
                                          v
                                    Widgets TUI
                                    (Status, Market,
                                     Active, History,
                                     Stats, Logs)
```

## Eventos Publicados

| Tipo | Dados | Descrição |
|------|-------|-----------|
| `status` | `{status, detail}` | Status do bot (connected, waiting, analyzing, etc.) |
| `market` | `{m5_indicators, m15_indicators, pre_analysis}` | Dados de mercado atualizados |
| `signal_emitted` | `{id, direction, confidence, symbol, regime, time_window, strategy, entry_candle_time}` | Novo sinal emitido |
| `signal_resolved` | `{id, outcome, quote_entry, quote_exit}` | Sinal resolvido (WIN/LOSS) |
| `llm_response` | `{direction, confidence, raw_response}` | Resposta do LLM |
| `error` | `{message, detail}` | Erro ocorrido |

## Solução de Problemas

### Dashboard não conecta

- Verifique se o bot está rodando (`python main.py`)
- Verifique se o socket existe (`ls -la ~/.deriv-bot/events.sock`)

### Widgets vazios

- O bot precisa ter executado pelo menos um ciclo para gerar dados
- Verifique se há sinais no banco de dados (`data/signals.db`)

### Erro de importação

- Instale as dependências: `pip install -r requirements.txt`
- Certifique-se de estar no diretório raiz do projeto
