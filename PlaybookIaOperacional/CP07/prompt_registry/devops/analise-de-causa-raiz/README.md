---
nome: Análise de Causa-Raiz
descricao: Cruza config, métricas e logs de uma janela para separar causa-raiz de sintomas e propor ação proporcional.
versao: 1.0.0
tags: [causa-raiz, observabilidade, elasticsearch, incidentes, sre]
inputs:
  - nome: config_cluster
    descricao: Arquivo de configuração do cluster Elasticsearch (shards, réplicas, heap, job de reindex, cache).
  - nome: metricas
    descricao: Série temporal de métricas do período (latência de busca, throughput de indexação, uso de heap, cache hit).
  - nome: logs
    descricao: Trecho de log nativo do Elasticsearch cobrindo a mesma janela de tempo.
---

# Análise de Causa-Raiz

## Objetivo

Conduzir análise de causa-raiz cruzando três artefatos da mesma janela (config, métricas e logs) até a causa real — separando explicitamente causa de sintoma, apoiando cada elo da cadeia causal em um dado concreto e declarando os limites do que os dados permitem concluir.

## Quando usar

- Diante de uma degradação onde o dashboard mostra sintomas (latência subindo, cache hit caindo) mas não a causa.
- Quando há três fontes correlacionáveis na mesma janela e o risco é apontar o último evento visível como causa.
- Para embasar uma decisão técnica proporcional, evitando tanto o exagero (refazer o cluster) quanto o vago ("monitorar mais").

## Exemplo de uso

**Entrada:** `cerebro.yaml` + série de métricas + log nativo de uma janela em que a busca começou a estourar timeout.

**Saída (trecho):** a causa-raiz é o job de reindex (task 88123) não ter concluído no tempo esperado (previsto ~90min, ainda em 41% após 7h); a cadeia liga isso a pressão sustentada de heap → GCs longos → circuit breaker → timeout de busca e queda do cache hit — tratando a queda de cache como consequência, não causa. Ação: pausar a task 88123 para aliviar o heap. Limites: os dados não explicam por que o reindex atrasou.

## Limitações conhecidas

- Exige as três fontes cobrindo a MESMA janela de tempo; lacunas em qualquer uma enfraquecem o cruzamento.
- Antes de enviar a um modelo externo, sanitizar identificadores internos (ex.: hostname `cerebro-node-3` → `node-A`) — os valores numéricos são mantidos por sustentarem o raciocínio.
- O prompt é orientado a Elasticsearch/JVM; outros stacks exigem adaptar o papel e o vocabulário de sintomas.
