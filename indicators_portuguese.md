# Indicadores Técnicos para Trading em 1 Minuto no Volatility 100 Index (R_100) da Deriv: O Que Funciona, O Que Não Funciona e Por Quê

## TL;DR (Resumo Executivo)
- **Os indicadores mais usados pela comunidade Deriv/índices sintéticos para trading Rise/Fall (CALL/PUT) de 1 minuto no R_100 são: pares de EMA (tipicamente 9/21 ou 10/20), RSI (14, com 7 também popular para scalping), Bandas de Bollinger (20, 2), MACD (12/26/9), Estocástico (14,3,3), ADX (14) e ATR (14)** — quase sempre em camadas formando um stack "tendência + momentum + volatilidade" (ex: EMA + RSI + Bollinger Bands, ou Stoch+RSI+MACD+BB em setups de scalping V75). Nas próprias plataformas Deriv (Deriv Trader, MT5, cTrader) todos estão disponíveis nativamente, e Bollinger Bands aparece no tutorial oficial de Bot da Deriv como exemplo de overlay para contrato Rise.

- **A evidência estatística é brutal para esse caso de uso específico.** A própria Deriv afirma na página de produto de índices sintéticos: "Os índices sintéticos, com exceção do Range Break Index, podem não ser bem adequados para indicadores técnicos… qualquer padrão histórico notável é puramente coincidência." O Volatility 100 é gerado por um gerador de números pseudoaleatórios criptograficamente seguro (CSPRNG) calibrado para ~100% de volatilidade anualizada com zero drift — matematicamente uma martingale onde, por definição, nenhuma função de preços passados prediz o sinal do próximo retorno. Combinado com payouts da Deriv para Rise/Fall de ~94–95% (uma vantagem da casa de ~2,5–3% por trade nos exemplos Volatility-10 que a própria Deriv publica; provavelmente pior em Vol 100 com durações curtas), uma estratégia de moeda aleatória é uma perda garantida no longo prazo, e você precisa de uma taxa de ganho sustentada acima de ~51,3–52,6% apenas para empatar. A principal decisão da Junta de Supervisores ESMA de 23 de março de 2018 (esma.europa.eu) descobriu que "74-89% das contas de varejo tipicamente perdem dinheiro em seus investimentos, com perdas médias por cliente variando de €1.600 a €29.000" tradando CFDs, e 80–90% perdem em opções binárias especificamente.

- **A recomendação honesta: manter o stack de indicadores enxuto e não-redundante (um filtro de tendência + um oscilador de momentum + um envelope de volatilidade, ex: EMA-50 + RSI-14 + Bollinger Bands 20/2 + ATR-14 para dimensionamento), aceitar que em uma verdadeira martingale nenhum indicador pode entregar uma vantagem estrutural, e tratar qualquer bot Rise/Fall dirigido por LLM como um projeto de pesquisa e não como uma estratégia com EV positivo esperado.** Se você está determinado a fazer deploy, foque o LLM em (a) detecção de regime (ADX < 20 = range, ADX > 25 = tendência) para que seus sinais pelo menos correspondam à estrutura estatística local, (b) evitar indicadores fortemente correlacionados (RSI + Stoch + MACD medem momentum e adicionam ruído, não sinal), e (c) backtesting rigoroso out-of-sample em dados de tick do R_100 puxados da API WebSocket da Deriv, com suposições realistas de payout.

---

## Achados-Chave

1. **R_100 é projetado como um processo aleatório sem drift.** A Deriv descreve o índice como seguindo "um modelo matemático que produz mudanças contínuas de preço em um nível de volatilidade predefinido… Enquanto mudanças de preço individuais são aleatórias, o comportamento geral permanece estatisticamente consistente ao longo do tempo" (Deriv Academy). O Head of Quants da Deriv, Prashant Sinha (experts.deriv.com, Jan 2026), confirma um gerador CSPRNG calibrado para "variância matemática estrita (volatilidade)." A página de símbolo do TradingView lista R_100 como "Volatilidade Constante de 100% com um tick a cada 2 segundos." Sob a interpretação padrão de movimento browniano geométrico que se adequa à descrição da Deriv, o desvio padrão por tick para o R_100 de 2 segundos é aproximadamente σ ≈ 1,0 × √(2 / 31.557.600) ≈ 2,5 × 10⁻⁴ (≈0,025%) por tick — valor derivado, não oficialmente publicado pela Deriv. O time de quants da Deriv afirma explicitamente que o algoritmo é "rigorosamente auditado por terceiros independentes", mas os parâmetros da SDE não são divulgados publicamente além de "volatilidade constante de N%."

2. **A própria Deriv avisa que indicadores não se aplicam bem.** Na página de produto de índices sintéticos deriv.com: *"Os índices sintéticos, com exceção do Range Break Index, podem não ser bem adequados para indicadores técnicos. Como não há order book, significando que o preço não é determinado pelo equilíbrio do maior bid e menor ask, qualquer padrão histórico notável é puramente coincidência."* Isso é incomumente candente para uma página de broker.

3. **Os stacks de indicadores favoritos da comunidade são notavelmente consistentes entre fontes.** O guia "V75 Scalping" do Synthetics.info (um blog comunitário Deriv muito acessado) prescreve Bollinger Bands + RSI + Estocástico + MACD em M15→M5. O thread VIX-75 do EarnForex recomenda Bollinger Bands (período 25) + Williams Fractals + Alligator (13,5,3). O e-book "How to Trade Synthetic Indices" de Vince Stanzione publicado por Deriv ilustra especificamente um **crossover de média móvel 21/6 no Volatility 75 (1s) usando um gráfico de 1 minuto**, mais Canais de Donchian (estilo Tartaruga). A estratégia "MKOREAN" rise/fall amplamente compartilhada no Scribd usa Momentum + CCI + Stochastic RSI + MACD. O padrão dominante é **tendência (MA/EMA) + momentum (RSI/Stoch/MACD) + volatilidade (BB/ATR)**.

4. **A maioria desses indicadores de "confirmação" são altamente correlacionados e adicionam pouca informação independente.** O estudo de correlação de Spearman-rank de Grzegorz Link descobriu que "quase todos (RSI, ROC, CCI, %b, Estocástico e a linha MACD) são uma forma de velocidade de preço" e estão fortemente correlacionados. Tradeciety e LuxAlgo ambos avisam que empilhar RSI + MACD + Estocástico cria a *ilusão* de confluência enquanto apenas repetindo um sinal. Esse é o maior defeito de design em a maioria das estratégias comunitárias Deriv acima.

5. **Payouts e vantagem da casa tornam a matemática hostil.** O e-book 2025 da Deriv documenta payouts Rise/Fall no Volatility 10 (1s), duração de 5 ticks, em ~94,2–95,3% (especificamente um exemplo Vol 10 (1s) com "um retorno potencial de 94,20%" e outro onde "$10 de investimento agora ganhou $9,53 para um lucro de 95,3%"). Tratando R_100 como zero-drift (então P(Rise)=P(Fall)=0,5), a vantagem da casa por trade com payout de 95% é (1 − 0,95)/2 = **2,5%** da stake; com payout de 90% sobe para 5%; com 80% é 10%. A taxa de ganho de equilíbrio com payout de 95% é 1/(1+0,95) = **51,28%**; com payout de 80% é **55,6%** (Quadcode; Wikipedia "Binary option" — o cálculo de Pape: "você deve ganhar 54,5% das vezes apenas para empatar"). Para lucro líquido de 10% ao mês depois de 200 trades em payout de 95%, você precisaria de ~54% de acurácia sustentada — e a posição oficial da Deriv é que não há padrões históricos exploráveis para entregar isso.

6. **Estatísticas de perda de varejo são inequívocas.** O comunicado de imprensa ESMA de 23 de março de 2018 (esma.europa.eu) afirmou diretamente: "As análises de NCAs em trading de CFD em diferentes jurisdições da UE mostram que 74-89% das contas de varejo tipicamente perdem dinheiro em seus investimentos, com perdas médias por cliente variando de €1.600 a €29.000." Em opções binárias especificamente, múltiplas fontes (Strike.money, Dukascopy, Global Gurus) citam **80–90% dos traders de varejo perdem**, que é por que ESMA baniu opções binárias de varejo em toda a UE e a FCA permanentemente baniu-as para consumidores varejistas UK a partir de 2 de abril de 2019 (Policy Statement PS19/11), com o Diretor Executivo da FCA Christopher Woolard afirmando bluntamente: "Opções binárias são produtos de jogo disfarçados de instrumentos financeiros." Os contratos binários da Deriv são acessíveis globalmente primariamente através de suas entidades BVI e Vanuatu precisamente por causa desses bans da UE/UK.

7. **A coisa mais próxima de uma "vantagem válida" em sintéticos é execução ciente de regime, não previsão de padrão.** Como volatilidade é *constante* por construção (ao contrário de mercados reais), dimensionamento de posição baseado em ATR e gating de regime baseado em ADX removem a maior fonte de sinais ruins de indicador — falsas tendências em range e falsas reversões em tendência. O próprio índice Range Break da Deriv é o único sintético para qual eles admitem indicadores terem aplicação significativa, porque tem uma estrutura *explicitamente* de mean-reversion.

---

## Detalhes

### 1. O Que a Comunidade Deriv / Índices Sintéticos Realmente Usa (com parâmetros)

Abaixo estão os indicadores que aparecem repetidamente em blogs comunitários Deriv (synthetics.info, volatility75index.com), os PDFs de estratégia Scribd que circulam em Telegram e TikTok, o e-book Vince Stanzione da própria Deriv, o thread VIX-75 do EarnForex, e guias de scalping Headway/FXOpen. Os parâmetros listados são as configurações de 1 minuto mais citadas.

**Tendência / direção**
- **Par EMA 9 & 21** (par de scalping mais comum); também **EMA 10/20** e o **crossover MA 21/6 em V75 1s, 1-minuto** de Stanzione (exemplo publicado da própria Deriv). Razão: EMA reage mais rápido que SMA — relevante quando cada vela é construída de apenas ~30 ticks (R_100 de 2 segundos) ou ~60 ticks (R_100 (1s) de 1 segundo).
- **EMA 50 e/ou EMA 200** como filtro de viés de timeframe maior (15-minuto ou 5-minuto), depois trade apenas na direção da tendência de TF maior.
- **ADX (14)**, threshold 20–25 para distinguir range vs tendência (filtro de regime, não gatilho de entrada).
- **Velas Heikin-Ashi** aparecem em várias estratégias Deriv (ex: o "11 Binary_deriv Strategies" PDF Scribd) para suavizar ruído — ao custo de acurácia de price-action e lag em reversões.

**Momentum**
- **RSI (14)** com thresholds 70/30 é o padrão; scalpers frequentemente descem para **RSI (7)** com thresholds 80/20 (guia 1-minuto binary de Cris Brag; Mondfx).
- **Estocástico (14,3,3)** ou fast (5,3,3) com thresholds 80/20.
- **MACD (12,26,9)** padrão; a estratégia 1-minuto binary do Tradingpedia usa uma configuração mais rápida **(9,20,3)** para acompanhar ruído M1.
- **CCI (20)** e **Williams %R (14)** aparecem em alguns PDFs específicos Deriv mas são essencialmente transformações monotônicas do mesmo sinal de momentum.

**Volatilidade / envelope**
- **Bollinger Bands (20, 2)** — usada por praticamente todo guia e explicitamente demonstrada no tutorial oficial de Bot da Deriv como o overlay exemplo para contratos Rise.
- **Keltner Channels** (midline EMA-20, multiplicador ATR baseado 1,5–2) — Headway recomenda essas sobre Bollinger Bands para VIX-75 porque larguras baseadas em ATR tratam expansão violenta melhor.
- **ATR (14)** — usado para dimensionamento de stop em trades de CFD e para normalizar regimes de volatilidade; em Rise/Fall binário é usado para filtrar períodos de baixa volatilidade.
- **Canais de Donchian (20)** — Turtle-style breakout, apresentado no e-book Deriv de Stanzione.
- **Parabolic SAR (0,02, 0,2)** — aparece em alguns setups V75 para lógica de trail-stop.

**Price-action / estrutural**
- Suporte/resistência, pontos pivô, padrões de velas (engulfing, doji, marubozu, hammer). A estratégia engulfing-candle 1-minuto binary do Tradingpedia e as estratégias "Even/Odd" Scribd são exemplos canônicos.
- **VWAP** é algumas vezes mencionado mas é **praticamente sem sentido em índices sintéticos** porque não há order book e portanto nenhum volume real; o "volume" que a Deriv reporta em gráficos sintéticos é uma contagem de ticks, não notional tradado.

**Stack típico da comunidade para Rise/Fall R_100 de 1 minuto** (sintetizado em fontes):
1. EMA 9 + EMA 21 → direção de tendência.
2. RSI 14 + 70/30 → confirmação de momentum.
3. Bollinger Bands 20/2 → zona de volatilidade/mean-reversion.
4. ADX 14 > 25 → apenas tome trades de tendência; ADX < 20 → tome trades de mean-reversion BB.
5. ATR 14 → sanity-check que o movimento é grande o suficiente para limpar o spread/buffer de payout.

### 2. Evidência Estatística — O Que Realmente Funciona em Séries Aleatórias / Quase-Aleatórias

**Literatura de random-walk e EMH.** O *A Random Walk Down Wall Street* de Burton Malkiel e os dois papers fundacionais de Eugene Fama — "The Behavior of Stock-Market Prices" (*Journal of Business*, Jan. 1965, pp. 34–105) e "Efficient Capital Markets: A Review of Empirical Work" (*Journal of Finance*, Maio 1970, pp. 383–417) — estabeleceram a baseline de que mudanças de preço são essencialmente imprevisíveis de preços passados em mercados líquidos. O *A Non-Random Walk Down Wall Street* de Andrew Lo & A. Craig MacKinlay (Princeton University Press, 1999; paperback 2002) descobriu desvios fracos mas estatisticamente significantes de random walk em mercados de ações reais — mas esses desvios vêm de microestrutura, order-flow, e difusão lenta de informação, **nenhum dos quais existem em um índice sintético dirigido por CSPRNG**. Em uma verdadeira martingale (drift = 0), toda expectativa condicional de retorno futuro dada qualquer função de preços passados é zero por definição. Toda a classe de indicadores de trend-following e mean-reversion é, em expectativa, zero-edge.

**Performance de indicador backtestada.** Os backtests EMA cross do QuantifiedStrategies em S&P 500 encontram que entradas de crossover de short-EMA em mercados reais são na maioria *piores* que buy-and-hold, e que qualquer lucratividade aparente de sistemas MA-crossover em dados reais vem do drift de mercado de ações (μ > 0), que **R_100 não tem**. A survey acadêmica mais abrangente, Park & Irwin's "What Do We Know About the Profitability of Technical Analysis?" (*Journal of Economic Surveys*, Vol. 21, No. 4, pp. 786–826, 2007), reviu exatamente 95 estudos modernos e encontrou: "56 estudos encontram resultados positivos… 20 estudos obtêm resultados negativos, e 19 estudos indicam resultados mistos" — e mesmo aqueles resultados positivos desaparecem uma vez que custos de transação e overfitting são propriamente contabilizados.

**Redundância de indicador.** O estudo de Spearman-rank de Grzegorz Link e a análise de Tradeciety ambas demonstram que RSI, Estocástico, MACD, CCI, ROC e %b são medidas de momentum altamente correlacionadas. Empilhá-las cria a *aparência* de três confirmações independentes enquanto estatisticamente você tem ~1,5 sinais independentes no máximo — que é por que muitas estratégias comunitárias Deriv que "ganham em backtest" falham em forward-test.

**Matemática por-trade em Deriv Rise/Fall.** O e-book 2025 da Deriv documenta payouts Rise/Fall de 94,2–95,3% no Volatility 10 (1s), duração de 5 ticks. Assumindo a mesma faixa se aplica a durações curtas R_100 (payouts são cotados por trade pela API de pricing Deriv, então essa é uma aproximação), a **taxa de ganho de equilíbrio em payout de 95% é 51,3%**, e a **vantagem da casa por trade se você virar moedas é 2,5%**. Em payout de 90%, equilíbrio é 52,6% e edge é 5%. Caia para payout de 80% (comum em durações mais exóticas) e você precisa de 55,6% para empatar, com 10% de edge por-trade contra você.

**Taxas de perda de varejo.** O regime de divulgação primário ESMA 2018 confirmou 74–89% dos traders CFD de varejo perdem dinheiro, com perdas médias por cliente de €1.600–€29.000. Estudos específicos de opção-binária citados por Strike.money, Dukascopy, e Global Gurus colocam taxas de perdedor de opções-binárias em 80–90%. A combinação é consistente com a matemática acima: se taxas de ganho mediana aglomeram ao redor de 50% e o edge é 2,5–10% contra você, **a vasta maioria das contas de varejo tenderá para zero dado trade suficiente**.

### 3. Perspectiva Crítica — Há Alguma Vantagem Genuína?

O Volatility 100 Index é, por construção, exatamente o tipo de processo onde análise técnica tem a **menor** justificativa teórica:

- **Sem order book → sem vantagem baseada em microestrutura.** Todos os efeitos TA que sobrevivem scrutínio acadêmico em mercados reais (ex: momentum de curto horizonte, breakouts de range de abertura, fluxos de fim-de-dia) rastreiam de volta a desequilíbrios de order-flow e difusão lenta de informação. R_100 não tem nenhum desses.
- **Sem fundamentais → sem vantagem de chegada de informação.** A classe inteira "smart-money compra antes de earnings" de efeitos é mecanicamente impossível.
- **Volatilidade constante → sem vantagem de volatilidade-clustering.** Mercados reais têm clustering GARCH-like que você pode às vezes explorar; R_100 é calibrado para σ constante, então ATR é informativo para dimensionamento mas não para timing de entrada.
- **Zero drift → buy-and-hold tem retorno esperado zero** (ao contrário de índices de ações reais), então trend-following não tem nenhum "vento" subjacente empurrando em qualquer direção.

O que isso significa na prática: qualquer vantagem aparente que você encontrar em um backtest no R_100 é overwhelmingly provavelmente (a) ruído de uma amostra finita, (b) overfitting à história específica da seed RNG, ou (c) viés de sobrevivência em sua busca de parâmetro. O backtest Bitcoin MA-crossover de Mathematicsconsultants.com é instrutivo: até mesmo em um mercado real (drifting), MA crossovers com parâmetros aleatoriamente escolhidos underperformam buy-and-hold, e otimização de parâmetro apenas encaixa ruído.

**Poderia um LLM sofisticado extrair um sinal mesmo assim?** Quase certamente não, por duas razões:
1. Um CSPRNG é projetado para ser computacionalmente indistinguível de verdadeira aleatoriedade; se qualquer rede neural pudesse prever sua saída do histórico de preço, a primitiva criptográfica (tipicamente um stream cipher ou HMAC-DRBG) seria considerada quebrada.
2. A API de pricing da Deriv cita payouts Rise/Fall que se ajustam dinamicamente; se qualquer padrão sistematicamente aparecesse, a Deriv presumivelmente reprepararia para neutralizá-lo (esse é comportamento padrão de broker de opções binárias).

O enquadramento honesto para o usuário: **um bot LLM Rise/Fall no R_100 é fundamentalmente um projeto de previsão de martingale contra uma vantagem da casa de 2,5–5%.** O melhor cenário é um valor esperado levemente negativo com variância controlada; o cenário mais provável é decadência de conta aproximadamente à taxa da vantagem da casa vezes frequência de trade.

### 4. Recomendações Práticas

Se você prosseguir (reconhecendo o acima), aqui está o stack de indicador mais defensável e configuração. Cada indicador mede uma *dimensão distinta* para evitar o problema de redundância:

**Stack de 4 indicadores recomendado para o LLM consumir (1-minuto R_100):**

| Indicador | Propósito | Configuração | Por que isso não algo mais |
|---|---|---|---|
| **EMA-50** (close) | Tendência / viés | 50-período em M1 | Um sinal de direção é suficiente; emparelhamento com EMA-200 (M5) dá viés de TF maior |
| **RSI-14** | Momentum / overextensão | 14 período, níveis 70/30 | Oscilador de momentum mais estudado; **não** adicione Stoch ou MACD — eles são correlacionados |
| **Bollinger Bands** | Envelope de volatilidade / zona de mean-reversion | SMA 20-período, 2σ | Encaixe natural para índices sintéticos porque σ é constante-projetado; bandas esticam em ruído, contraem em compressão |
| **ATR-14** | Regime de volatilidade / dimensionamento | 14 período | Use para filtrar trades quando ATR < sua mediana de 50-período (regimes de baixo-vol tem mais whipsaws em M1) |
| **ADX-14** (opcional 5º) | Gate de regime | 14 período, threshold 20/25 | Trade continuação de tendência apenas quando ADX > 25; trade BB mean-reversion apenas quando ADX < 20 |

**O que alimentar o LLM cada minuto:**
- Últimos 50 closes (OHLC bruto).
- Valor EMA-50 e sinal de slope.
- Valor RSI-14.
- Bollinger superior/meio/inferior e %B (onde preço fica na banda).
- Valor ATR-14 e percentil ATR-14 sobre últimos 200 bars.
- ADX-14, +DI, −DI.
- Opcional: distância do último close para o EMA-50 de 5-minutos (contexto multi-TF).

**O que NÃO fazer:**
- Não dê ao LLM RSI + Estocástico + MACD + Williams %R + CCI juntos. Eles são ~85% correlacionados; você desperdiça tokens e cria confluência falsa.
- Não use VWAP em índices sintéticos — não há volume real.
- Não otimize parâmetros maximizando taxa de ganho in-sample no histórico de tick R_100. O otimizador encaixará histórico RNG, não sinal real. Use teste walk-forward com holdout out-of-sample estrito.
- Não dimensione stakes Rise/Fall por Kelly sem primeiro provar uma taxa de ganho com EV positivo nos payouts realmente cotados. A matemática é implacável.

**Manipulação de regime:**
- **Regime de tendência (ADX-14 > 25, preço acima EMA-50, RSI entre 50–70):** tome Rise em pullbacks para EMA-50 ou banda de Bollinger do meio, expiry 3–5 minutos.
- **Regime de range (ADX-14 < 20, preço oscilando ao redor EMA-50):** tome Rise na banda de Bollinger inferior quando RSI < 30, Fall na banda de Bollinger superior quando RSI > 70, expiry 1–3 minutos.
- **Transição (20 < ADX < 25 ou compressão em largura de BB):** fique de fora. Aqui é onde trades binários vão morrer.

**Regras de confluência para filtrar sinais falsos:**
- Requer pelo menos 2 de 3 dimensões (tendência, momentum, localização de volatilidade) concordem.
- Pule trades dentro de 10 ticks de um breakout de squeeze de Bollinger Band — resultado direcional é genuinamente 50/50 lá.
- Coloque cap em frequência de trade. O guia scalping 1-minuto XS.com nota "scalpers experientes podem executar 40-50 trades mas apenas quando condições ótimas existem." Em R_100 um cap defensável é 10–20 trades/hora.

**Notas de implementação específicas da Deriv:**
- Use a **API WebSocket Deriv** (developers.deriv.com) para dados de tick. R_100 ticks chegam a cada ~2 segundos; R_100 (1s) a cada ~1 segundo. Construa velas de 1-minuto client-side de ticks.
- Expiry Rise/Fall pode ser definido em ticks (1–10) ou minutos; para análise de vela M1, uma **expiry de 2–5 minutos** combina melhor o horizonte de informação natural de indicadores M1 que uma expiry sub-tick.
- Payouts são cotados live pela API por contrato — log-e com cada trade. Se seu payout médio deriva abaixo de ~90% e sua taxa de ganho é abaixo de 55%, você está sangrando dinheiro mesmo se equity está atualmente up por variância.
- Em Deriv Trader/MT5/cTrader você tem todos os indicadores acima disponíveis nativamente; em Deriv Bot, os cinco blocos de indicador são MACD, RSI, Bollinger Bands, SMA e EMA, que limita alguns do acima.

---

## Recomendações (Em Etapas)

**Etapa 0 — Reality-check antes de ir live.** Puxe 30+ dias de dados de vela R_100 de 1-minuto via API WebSocket Deriv. Backtest um coin-flip (Rise/Fall aleatório) no payout atualmente cotado. Confirme que EV por trade é negativo e que drawdown parece "assustador o suficiente que a matemática é real." Se você não pode perder deliberadamente em demo, você não ainda tem uma baseline.

**Etapa 1 — Construa o stack de indicador enxuto** acima (EMA-50, RSI-14, BB 20/2, ATR-14, ADX-14). Alimente-o para seu LLM com um prompt estrito que requeira que ele (a) declare o regime primeiro, (b) cite quais 2 de 3 dimensões concordam, e (c) recuse-se a sinalizar em regimes de transição. Execute em demo por pelo menos 1.000 trades.

**Etapa 2 — Threshold de decisão estatística.** Compute a taxa de ganho real do LLM em demo com intervalo de confiança de 95% (binomial). Você precisa do **limite inferior de CI 95%** para exceder a taxa de equilíbrio (51,3% em payout de 95%) — não a estimativa pontual. Se sua estimativa pontual é 53% em 200 trades, seu CI 95% é aproximadamente 46–60% e você não tem evidência estatística de vantagem.

**Etapa 3 — Validação out-of-sample.** Retenha os 20% mais recentes de dados; se performance degrada por mais de ~20% da taxa de ganho in-sample, você overfitou. Itere.

**Etapa 4 — Live com limites duros.** Cap risco por trade em 0,5–1% de bankroll. Defina um limite de perda diária (ex: 5% de bankroll) e um cap de trade diário. Auto-shutdown do bot quando qualquer um é atingido.

**Benchmarks que devem mudar suas decisões:**
- Se taxa de ganho observada depois de 500 trades demo < 52%: mate o projeto.
- Se taxa de ganho observada é 53–55% em 500 trades mas degrada out-of-sample: mate o projeto.
- Se payout médio cai abaixo de 90% em seus setups típicos: reavalie; edge é agora ≥5%.
- Se distribuição de sinal do LLM é materialmente desbalanceada (ex: >65% chamadas Rise): sanity check — o modelo provavelmente está ancorando em algo stale.

**Usos melhores do mesmo esforço de engenharia:**
- Construa o bot LLM em um instrumento CFD (R_100 em si via multiplicadores Deriv MT5, ou um índice real) onde você pode usar stop-losses, dimensionamento de posição, e risco-recompensa assimétrico — nenhum dos quais existem em Rise/Fall.
- Ou trade os **índices Range Break da Deriv**, que a própria Deriv afirma *são* adequados para indicadores técnicos por causa de sua mean-reversion estrutural explícita.

---

## Ressalvas

- **Deriv não publica os parâmetros exatos de equação-diferencial-estocástica ou desvio padrão por-tick para R_100.** A figura σ ≈ 2,5 × 10⁻⁴ por tick de 2 segundos acima é derivada da volatilidade anualizada de 100% afirmada sob uma GBM padrão annualization (365,25 × 86.400 segundos/ano); é consistente com todas as descrições públicas da Deriv mas é *não* um número oficial Deriv. O blog quant da Deriv explicitamente nota que o algoritmo é "rigorosamente auditado por terceiros independentes" mas a SDE/parâmetros não são publicamente divulgados além de "volatilidade constante de N%."

- **Payouts Rise/Fall são dinâmicos.** A figura 94–95% citada é do exemplo e-book da própria Deriv para Volatility 10 (1s) em duração de 5 ticks. Payouts R_100 em expiries de 1-minuto podem ser mais baixos (quanto maior a volatilidade e mais curta a duração, mais ampla a margem protetiva do broker tende a ser em minha leitura de posts comunitários Deriv). Sempre log valores de payout live da API para seu contrato específico; a matemática de vantagem da casa acima escala linearmente com payout.

- **A figura "80–90% dos traders de varejo perdem" em opções binárias** vem de afirmações amplas de indústria/regulador (a divulgação primária ESMA de 23 de março de 2018 de 74–89% de taxa de perda de varejo em CFDs, o ban permanente da FCA de 2 de abril de 2019 PS19/11 citando opções binárias como "produtos de jogo disfarçados de instrumentos financeiros," avisos CFTC, e citações secundárias em strike.money, Dukascopy, Global Gurus) em vez de divulgação específica Deriv. A Deriv não publica uma divulgação de taxa de perda de cliente nas jurisdições BVI/Vanuatu onde Rise/Fall é oferecido. A matemática de perda de varejo é robusta independentemente, dada a estrutura de payout.

- **Guias de estratégia da comunidade devem ser tratados com extremo ceticismo.** Muitas das alegações "70–98% taxa de ganho" em Synthetics.info, vídeos TikTok, e PDFs Scribd são não verificadas, frequentemente correspondem a períodos curtos cherry-picked, e são frequentemente anexadas a bot-selling ou funnels de marketing de afiliado. A própria página Volatility75index.com cautela que a taxa de ganho >70% de um trader Reddit "até aleatoriedade alcançar" é o padrão típico.

- **Uma nota acadêmica:** há um corpo de literatura (meta-survey Park & Irwin 2007 de 95 estudos; Lo/Mamaysky/Wang 2000) encontrando efeitos de análise técnica fraca em mercados reais. Esses achados *não transferem* para índices sintéticos porque os mecanismos os produzindo (order-flow, vieses comportamentais de traders reais, difusão de informação) estão ausentes por construção em um preço dirigido por CSPRNG.

- **Risco específico de LLM:** modelos de linguagem tendem a produzir saídas direcionais confiantes mesmo de entradas aleatórias (uma edição conhecida chamada calibration drift em raciocínio numérico). Sem um gate estatístico duro (Etapa 2 acima), um bot LLM Rise/Fall parecerá "funcionar" pelas primeiras cem trades, então revertará para a expectativa de vantagem da casa. Trate qualquer LLM Rise/Fall backtestado como culpado até provado inocente em dados out-of-sample.
