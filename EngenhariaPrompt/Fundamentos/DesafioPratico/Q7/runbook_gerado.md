# Runbook — High memory usage on Chronos API pods

**Alerta:** [CRITICAL] High memory usage on Chronos API pods (>85% for 10min)
**Severidade:** P2
**Dono:** Squad Chronos · Escalação: @chronos-core
**Tempo-alvo de resolução:** 20 min
**Última revisão:** 2026-06-02

---

## 1. Triagem (≤ 2 min)

Confirmar que o alerta ainda está ativo no Beacon (não auto-resolvido):

```bash
# Listar pods do Deployment com consumo atual
kubectl -n production top pods -l app=chronos-api --sort-by=memory
```

```bash
# Status do Deployment e HPA
kubectl -n production get deploy chronos-api
kubectl -n production get hpa chronos-api
```

**Verificação esperada:**
- Se nenhum pod aparece > 85% do limit → alerta auto-resolveu. Pular para a Seção 8.
- Se ≥ 1 pod aparece > 85% do limit → seguir para Seção 2.
- Anotar nome dos pods afetados.

---

## 2. Diagnóstico de memória

Para cada pod afetado `<POD>`:

```bash
kubectl -n production describe pod <POD> | grep -E "Limits|Requests|Restart|OOM"
kubectl -n production logs <POD> --tail=200 --previous 2>/dev/null | tail -50
```

Checar se a métrica subiu de forma sustentada ou em pico, no Grafana:
dashboard **Chronos / API – Memory** → painel `container_memory_working_set_bytes`.

**Verificação esperada — classificar em UM dos 3 casos:**

| Sinal observado | Classificação | Próximo passo |
|---|---|---|
| Pico isolado < 5 min, sem `OOMKilled` | (a) Pico transitório | Seção 6a |
| Crescimento sustentado > 30 min, sem deploy recente | (b) Possível leak | Seção 4 e depois 6b |
| Múltiplos pods saturados simultaneamente, sem deploy | (c) Subdimensionamento | Seção 6b |
| `OOMKilled` recente (< 1h) | leak ou regressão | Seção 5 |

---

## 3. Dependências

### 3.1 Ledger (PostgreSQL)

```bash
# Latência p95 da conexão com Ledger via /metrics
kubectl -n production exec -it <POD> -- \
  curl -s localhost:<METRICS_PORT>/metrics | grep -E "ledger_(query|conn)_"
```

**Verificação esperada:**
- `ledger_query_duration_seconds{quantile="0.95"}` > 1.0 → backpressure em Ledger; escalar (Seção 7).
- Caso contrário, prosseguir.

### 3.2 Reactor (SQS)

```bash
aws sqs get-queue-attributes \
  --queue-url <REACTOR_QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages ApproximateAgeOfOldestMessage
```

**Verificação esperada:**
- `ApproximateNumberOfMessages` > 10.000 **ou**
- `ApproximateAgeOfOldestMessage` > 600 s
→ Backlog em SQS está inflando memória dos pods. Aplicar Seção 6b e escalar.

---

## 4. Deploy recente

```bash
argocd app get chronos-api -o wide | grep -E "Sync|Revision|Updated"
argocd app history chronos-api | head -5
```

**Verificação esperada:**
- Último sync < 2 h → alta probabilidade de regressão. Ir para Seção 6c (rollback).
- Último sync > 24 h → causa não está em deploy. Ir para Seção 6a ou 6b.

---

## 5. Mitigação

Executar **apenas uma** com base nos passos 2–4.

### 6a. Restart controlado (pico transitório)

```bash
kubectl -n production delete pod <POD>
```

Aguardar 90 s e re-rodar `kubectl top pods`. Memória do novo pod deve ficar < 60% do limit.

### 6b. Scale manual temporário

```bash
kubectl -n production patch hpa chronos-api \
  -p '{"spec":{"minReplicas":8}}'
```

Aguardar 3 min. Memória média do Deployment deve cair abaixo de 70%.
**Lembrar:** voltar `minReplicas=4` no pós-incidente.

### 6c. Rollback via Argo CD

```bash
argocd app history chronos-api
argocd app rollback chronos-api <REVISION_ANTERIOR>
```

Aguardar 5 min e validar memória < 70% e ausência de `OOMKilled`.

---

## 7. Escalação para @chronos-core

Escalar **se qualquer** condição abaixo for verdadeira:

- Memória > 85% por mais de 15 min após Seção 6 aplicada.
- `OOMKilled` em ≥ 2 pods dentro de 10 min.
- Ledger com p95 > 1.0 s sustentado (Seção 3.1).
- Backlog em SQS > 10.000 ou idade > 600 s (Seção 3.2).
- Rollback não disponível (sem revisão anterior estável).

**Template da mensagem em #oncall-chronos:**
