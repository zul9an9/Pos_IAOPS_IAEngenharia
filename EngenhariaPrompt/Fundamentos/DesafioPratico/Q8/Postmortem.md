# Postmortem técnico — chronos-api (incidente em andamento)

**Serviço:** chronos-api (API de transações, produção)
**Severidade:** P1
**Janela analisada:** 2026-04-23 18:42 UTC (deploy) → 2026-04-24 14:20 UTC
**Decisão a sustentar:** (A) rollback v2.48.0 vs. (B) scaling emergencial
**Autor:** Incident Commander (SRE)

---

## 1. TL;DR
Saturação do pool de conexões ao Ledger sob pico de tráfego, com gargalo **connection-bound, não compute-bound** (CPU 62%, mem 71%, mas pool 20/20 e RDS 240/250). Causa raiz mais provável: regressão de comportamento de conexão introduzida no **v2.48.0** (refactor do pool + timeout 2s + endpoint batch), detonada pelo pico de hoje. **Recomendação: rollback (opção A). Confiança: média-alta.**

## 2. Timeline (UTC)
- **23/04 18:42:11** — Deploy v2.47.0 → v2.48.0 via Argo CD (Artefato 1). Sem incidente nas ~19h seguintes.
- **24/04 13:30** — Baseline saudável: p99 420ms, 1200 req/s, 0,2% erro (Artefato 2).
- **13:45–14:00** — Tráfego sobe (1450→1780 req/s); p99 dobra (510→780ms); erro chega a 0,8%.
- **14:10** — Joelho da curva: p99 2400ms, 4,5% erro (Artefato 2).
- **14:19:48–52** — Pool esgotado (max=20, active=20, waiting=147), timeouts de 2s, `connection reset by peer`, circuit breaker OPEN em 87%, falha de publish no Reactor (Artefato 3).
- **14:20** — p99 8100ms, 2650 req/s, 11,7% erro. Backlog do Reactor em 50.127 msgs, lag 18min (Artefatos 2 e 4).

## 3. Análise dos artefatos
- **Artefato 1 (deploy):** mostra *o que* mudou; não mostra *quando* o sintoma surgiu. Quatro mudanças relevantes ao caminho de conexão: pool refatorado, psycopg 3.1→3.2, timeout 5s→2s, endpoint batch novo.
- **Artefato 2 (métricas):** degradação é progressiva e correlacionada ao tráfego, não um degrau súbito no horário do deploy. Não permite afirmar sozinha que o deploy é a causa.
- **Artefato 3 (log):** evidência mais forte. `pool exhausted` + `waiting=147` = saturação clássica de pool. `connection reset by peer` logo após o timeout de 2s indica **churn de conexão** (conexões mortas e reabertas). Não permite afirmar qual mudança específica do v2.48.0 originou isso.
- **Artefato 4 (Reactor):** consequência a jusante, não causa. 50k msgs é dano acumulado, não sinal de root cause.
- **Artefato 5 (cluster):** decisivo. CPU 62% / mem 71% descartam saturação de compute. HPA em 12/12 e RDS em **240/250 = 12 pods × 20 conexões/pool** mostram que o teto é de *conexões*, não de réplicas.

## 4. Root cause (5-whys)
1. Requests falham → `context deadline exceeded` / pool esgotado.
2. Pool esgotado → 147 esperando por 20 slots; conexões presas ou em churn.
3. Conexões insuficientes → timeout de 2s mata queries sob carga, conexões resetam e precisam reabrir contra um RDS já em 240/250 (sem headroom).
4. Por que agora? → pico cruzou o limiar em que 20 conexões/pod deixam de bastar.
5. Por que 20 não basta agora e (presumidamente) bastava antes? → **[HIPÓTESE]** o refactor do pool e/ou o timeout de 2s alteraram o ciclo de vida da conexão; o endpoint batch adicionou workload conexão-intensivo.

**Causa raiz:** regressão de configuração/comportamento de conexão no v2.48.0 (pool lib + timeout 2s, amplificada pelo batch).
**Fator contribuinte:** teto do RDS em 250.
**Gatilho:** pico de tráfego de hoje.

**Hipótese alternativa (saturação pura, deploy coincidência):** plausível — tráfego cresceu ~2,2× (1200→2650). Mas enfraquecida por CPU/mem moderados: saturação genuína de capacidade tenderia a pressionar compute também. O gargalo é *especificamente* de conexão, exatamente o que o v2.48.0 mexeu. **DADO AUSENTE:** comportamento do v2.47.0 em pico equivalente — sem isso, não dá para descartar a alternativa em 100%.

## 5. Comparativo das opções

| Critério | A) Rollback v2.48.0 | B) Scaling emergencial |
|---|---|---|
| Tempo até mitigar | Minutos (Argo CD sync) | Minutos a dezenas de min; param de RDS pode exigir cuidado/reboot |
| Risco de regressão | Baixo; reverte 4 mudanças de uma vez | **Alto:** ↑ pool × 12 pods estoura o RDS; ↑ max_connections é memory-bound e arriscado ao vivo |
| O que NÃO resolve | Não drena o backlog de 50k msgs | Não remove a regressão; trata sintoma |
| Fallback se falhar | Re-deploy v2.48.0; perda mínima | Reverter param de RDS; risco de instabilidade adicional |
| Pré-condições | v2.47.0 íntegro no registry | Headroom de memória no RDS — incerto |

## 6. Recomendação
**Rollback para v2.47.0 (opção A), confiança média-alta.** O gargalo é connection-bound e o v2.48.0 alterou justamente esse caminho; rollback é atômico e reversível. A opção B é inferior porque o cluster já está no teto do HPA e o RDS em 240/250 — aumentar pool multiplica conexões contra um teto que, para subir, é arriscado sob carga.

**Evidências PRÓ:** gargalo de conexão; CPU/mem não saturados; ação rápida e reversível; churn de conexão coincide com timeout de 2s do v2.48.0.
**Evidências CONTRA:** deploy foi há 19h sem incidente (aponta tráfego como gatilho proximal); rollback não drena o backlog; se for crescimento puro de tráfego, não resolve.

## 7. Riscos residuais e follow-ups
- **Backlog não some com o rollback:** após estabilizar a API, monitorar o consumer do `chronos-transactions` drenar as ~50k msgs; avaliar bump temporário de consumers.
- **[HIPÓTESE] a confirmar no postmortem formal:** comparar default de pool size da lib antiga vs. nova; isolar o impacto do timeout 2s no churn; medir custo de conexão por request do endpoint batch.
- **Capacidade real:** validar se v2.47.0 sustenta 2650 req/s — se não, há trabalho de capacity planning independente do deploy.
- **DADO AUSENTE crítico:** logs/métricas do pico de ontem à noite em v2.48.0 e o pool size efetivo configurado na nova lib.
