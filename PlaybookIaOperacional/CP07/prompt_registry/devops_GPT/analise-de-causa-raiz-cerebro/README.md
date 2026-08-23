---
nome: analise-de-causa-raiz-cerebro
descricao: Cruza configuração, métricas e logs para construir uma hipótese causal de degradação do Cerebro.
versao: 1.0.0
tags:
  - elasticsearch
  - troubleshooting
  - observabilidade
  - causa-raiz
inputs:
  - nome: configuracao
    descricao: Configuração do cluster ou serviço relevante para o incidente.
  - nome: metricas
    descricao: Série temporal de métricas observadas durante a janela do problema.
  - nome: logs
    descricao: Logs coletados na mesma janela temporal das métricas.
  - nome: contexto_operacional
    descricao: Contexto adicional necessário para interpretar criticidade, limites ou dependências.
---

# Análise de causa-raiz do Cerebro

## Objetivo

Fazer a IA cruzar configuração, métricas e logs na mesma linha do tempo para construir uma hipótese causal em vez de repetir sintomas.

## Casos de uso

- Degradação de busca e indexação em Elasticsearch.
- Incidentes em que o sinal aparece primeiro nas métricas, depois em filas/GC e finalmente em erros do serviço.
- Preparação de uma hipótese antes de escalar para especialistas.

## Exemplo

A entrada do Checkpoint 03 mostra reindexação iniciada às 02:00 ainda em 41% às 09:58, aumento de `heap_used_pct` de 61% para 94%, queda de cache hit de 74% para 29%, fila de escrita chegando a 200/200, circuit breaker disparando e buscas parciais.

## Execução de referência

Modelo: GPT-5.6 Luna.

Resultado principal:

```text
RESUMO EXECUTIVO:
A reindexação programada continuou muito além da janela esperada e permaneceu consumindo capacidade de escrita enquanto a pressão de heap crescia. A combinação de carga de indexação, fila de escrita saturada, GC intenso e circuit breaker reduz a capacidade de servir buscas, levando a timeouts, rejeições e resultados parciais.

CADEIA CAUSAL:
reindexação prolongada -> pressão de indexação/memória -> filas + GC + cache evictions -> circuit breaker -> buscas lentas/parciais e rejeições

CAUSA-RAIZ PROVÁVEL:
reindexação excessivamente prolongada/sobreposta à operação normal, com recursos insuficientes para manter indexação e busca concorrentes dentro do limite de heap.
```

## Limitações

- A análise estabelece hipótese causal, não causalidade experimental.
- A configuração fornecida é parcial; parâmetros não presentes não devem ser inventados.
- Logs podem conter dados internos que precisam ser redigidos antes de uso em serviços externos.
