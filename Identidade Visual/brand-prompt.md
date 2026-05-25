# Lumen — Brand Prompt

Use este documento como contexto ao construir qualquer tela do **Lumen** com o Claude Code.

## O que é

Lumen é um dashboard SaaS para monitorar e configurar bots de trading na **Deriv**. Um bot lê velas (candlesticks) em tempo real; outro executa análises e gera sinais. O painel expõe: configuração dos bots, resultado dos sinais e métricas de performance.

O nome vem de *lumen* (unidade de luz) — a ideia é **clareza**: ler o mercado com nitidez, sem ruído. A leitura de longas sessões tem que ser confortável e os dados, instantaneamente legíveis.

## Personalidade

Limpo, profissional, confiável. Pensado como produto (pode ir além do uso pessoal), então nada de gambiarra visual. Calmo no cromatismo — a interface é neutra para que **a cor signifique dado**: verde é alta/compra, vermelho é baixa/venda, e o índigo da marca é só ação/navegação. Se tudo for colorido, nada comunica.

## Cor

- **Primária (marca/neutra):** índigo `#3B5BDB`. Usar em botões primários, links, estado ativo, foco. NUNCA usar verde/vermelho como cor de marca.
- **Superfícies:** fundo `#F8FAFC`, cards brancos `#FFFFFF`, headers de tabela `#F1F5F9`, bordas `#E2E8F0`.
- **Texto:** títulos `#0F172A`, corpo `#334155`, labels `#64748B`.
- **Semântica de mercado (reservada para dados):** alta `#16A34A`, baixa `#DC2626`, neutro `#64748B`. Versões soft para fundos de badge.
- **Status do bot:** rodando `#16A34A`, pausado `#D97706`, erro `#DC2626`.

Regra de ouro: verde e vermelho aparecem **só** em números, sinais, velas e variações. Nunca decorando botões ou bordas.

## Tipografia

- **Display/títulos:** Sohne (fallback Inter). Pesos 600.
- **Corpo/UI:** Inter. Pesos 400–500.
- **Números/preços/tickers:** JetBrains Mono (tabular). Todo dado financeiro vai em mono com `font-variant-numeric: tabular-nums` para alinhar colunas.

## Layout

- Sidebar de navegação à esquerda, conteúdo em grid de cards.
- Densidade controlada: respiro generoso, mas tabelas compactas e escaneáveis.
- Cantos arredondados 10px (cards) / 6px (inputs, badges).
- Sombras suaves, nunca pesadas. Profundidade vem de borda + sombra leve, não de gradiente.
- Sem gradientes decorativos. Atmosfera vem de hierarquia tipográfica e espaço em branco.

## Componentes-chave

- **Candlestick chart:** TradingView Lightweight Charts. Velas usam up/down semânticos.
- **Tabela de sinais:** colunas mono, badge de direção (up-soft/down-soft), timestamp muted.
- **Cards de métrica:** número grande em mono, label muted em cima, delta colorido (up/down) embaixo.
- **Painel de config:** inputs com label claro, toggles para ligar/pausar bot, validação inline.
- **Indicador de status do bot:** dot colorido (live/paused/error) + texto.

## Não fazer

- Não usar Inter como fonte de título de marca (é fallback de UI, não destaque).
- Não usar roxo em gradiente sobre branco (cliché de AI).
- Não pintar a UI de verde/vermelho fora de contexto de dado.
- Não usar sombras dramáticas ou neon — isso é um produto sério, não um terminal hacker.
