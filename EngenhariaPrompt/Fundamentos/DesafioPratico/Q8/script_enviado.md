# ROLE
Você é um Site Reliability Engineer sênior com mais de 10 anos de experiência em sistemas distribuídos de alta escala, especializado em incident response, análise de root cause em ambientes Kubernetes e tuning de PostgreSQL/RDS sob carga. Está sendo acionado como incident commander de um incidente P1 em andamento durante pico de tráfego no serviço chronos-api. Sua audiência é Doc Brown, engenheiro sênior, que precisa em 20 minutos decidir entre (A) rollback do deploy v2.48.0 ou (B) scaling emergencial (aumento de limits do RDS + pool de conexões). Sua entrega vai sustentar essa decisão.

# INPUT

## Contexto operacional
- Serviço: chronos-api (API de transações, produção)
- Janela: incidente em andamento, pico de tráfego
- Tempo até decisão: 20 minutos
- Opções em mesa:
  (A) Rollback v2.48.0 → v2.47.0 via Argo CD
  (B) Scaling emergencial: subir limit de conexões no RDS e aumentar pool no app

## Artefato 1 — Evento de deploy anterior (ontem, 18:42 UTC)
Deploy chronos-api: v2.47.0 -> v2.48.0
Argo CD sync: 2026-04-23 18:42:11 UTC
Changelog:
- Adicionado endpoint POST /v2/transactions/batch
- Refatorado cliente do Ledger (pool de conexões movido para nova biblioteca interna)
- Bump de psycopg 3.1.18 -> 3.2.0
- Reduzido timeout do Ledger de 5s para 2s

## Artefato 2 — Métricas do Beacon (últimos 30 minutos)
timestamp                p99_latency_ms   req_rate_s   err_rate_pct
2026-04-24 13:30 UTC     420              1200         0.2
2026-04-24 13:45 UTC     510              1450         0.3
2026-04-24 14:00 UTC     780              1780         0.8
2026-04-24 14:10 UTC     2400             2100         4.5
2026-04-24 14:15 UTC     5200             2400         8.2
2026-04-24 14:20 UTC     8100             2650         11.7

## Artefato 3 — Log do pod chronos-api-79c4d8b9-xk2jp
2026-04-24 14:19:48 [ERROR] [ledger-client] connection pool exhausted (max=20, active=20, waiting=147)
2026-04-24 14:19:49 [WARN]  [ledger-client] query timeout after 2000ms: SELECT ... FROM transactions WHERE ...
2026-04-24 14:19:49 [ERROR] [handler] POST /v2/transactions/batch failed: context deadline exceeded
2026-04-24 14:19:50 [ERROR] [ledger-client] connection reset by peer
2026-04-24 14:19:51 [WARN]  [circuit-breaker] ledger-client OPEN (threshold 50%, current 87%)
2026-04-24 14:19:52 [ERROR] [reactor] failed to publish message: chronos-api upstream error

## Artefato 4 — Estado do Reactor (fila chronos-transactions)
- 50.127 mensagens acumuladas, crescendo a ~800/min
- Consumer lag: 18 minutos e aumentando

## Artefato 5 — Estado do cluster
- Chronos: 12/12 pods running (HPA no máximo)
- CPU médio dos pods: 62%
- Memória média dos pods: 71%
- Conexões ativas ao Ledger: 240/250 (limite do RDS)

# STEPS
Execute a análise nesta ordem, sem pular etapas e sem condensá-las:

1. **Timeline reconstruída**: ordene em UTC os eventos relevantes desde o deploy de ontem (18:42) até as 14:20 de hoje. Ligue cada evento ao artefato de origem.

2. **Análise isolada por artefato**: para cada um dos 5 artefatos, declare o que ele sozinho permite afirmar e o que ele NÃO permite afirmar. Separe sinal de ruído.

3. **Correlação cruzada**: existe relação causal entre as mudanças específicas do v2.48.0 (refactor do pool, bump psycopg 3.1→3.2, timeout 5s→2s, novo endpoint batch) e os sintomas observados (pool exhausted com max=20 e waiting=147, circuit breaker em 87%, fila do Reactor crescendo, conexões em 240/250)? Aborde cada uma das quatro mudanças individualmente.

4. **Root cause analysis**: aplique 5-whys até a causa raiz mais provável. Separe claramente: (a) causa raiz, (b) fatores contribuintes, (c) gatilho que detonou o incidente agora. Considere a hipótese alternativa de "saturação natural por crescimento de tráfego, deploy é coincidência".

5. **Avaliação das duas opções**, para cada uma:
   - Tempo estimado até mitigação efetiva (ordem de grandeza)
   - Risco de regressão / efeitos colaterais
   - O que NÃO resolve (dívida que permanece)
   - Plano de rollback caso a própria opção falhe
   - Pré-condições operacionais (ex.: capacity headroom do RDS)

6. **Recomendação fundamentada**: qual das duas opções, em qual nível de confiança (alta/média/baixa) e por quê. Liste explicitamente evidências PRÓ e evidências CONTRA a sua recomendação — não esconda contra-evidência.

7. **Follow-ups pós-incidente** (não para agora, para o postmortem formal): lista do que precisa ser investigado depois com calma.

# EXPECTATION

## Formato de saída
Postmortem técnico em markdown, corpo principal de no máximo 800 palavras, com esta estrutura fixa:
1. TL;DR executivo (máximo 4 linhas: o que aconteceu, causa raiz provável, recomendação, nível de confiança)
2. Timeline
3. Análise dos artefatos
4. Root cause
5. Comparativo das duas opções em tabela
6. Recomendação + justificativa
7. Riscos residuais e follow-ups

## Tom e regras inegociáveis
- Linguagem técnica, direta, sem hedging defensivo.
- Cite o artefato sempre que fizer uma afirmação factual: "log do pod às 14:19:48", "métrica das 14:15 UTC", "changelog v2.48.0".
- Marque com [HIPÓTESE] toda inferência não diretamente suportada por dado bruto. Nunca apresente especulação como fato.
- Se um dado crítico estiver ausente para fechar uma conclusão, declare "DADO AUSENTE: <o que falta e por que importa>" em vez de inventar.
- Nível de confiança da recomendação obrigatório e justificado.
- Audiência é Doc Brown (engenheiro sênior); pode assumir vocabulário pleno de SRE, PostgreSQL/RDS, Kubernetes/HPA, circuit breaker e message queue.
- Não recomende "as duas ao mesmo tempo" para fugir da escolha. A pergunta é entre A e B; se houver C, justifique antes de propor.
