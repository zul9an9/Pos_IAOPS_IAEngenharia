---
nome: decisao-de-contrapressao-relay
descricao: Compara estratégias de contrapressão para o Relay, pondera trade-offs e recomenda uma combinação compatível com SLA, custo e não perda de telemetry.
versao: 1.0.0
tags:
  - mensageria
  - filas
  - sre
  - arquitetura
inputs:
  - nome: cenario
    descricao: Estado atual do Relay, carga observada, consumidores e restrições operacionais e financeiras.
  - nome: opcoes
    descricao: Estratégias candidatas que devem ser comparadas antes da recomendação.
---

# Decisão de contrapressão do Relay

## Objetivo

Evitar que um cliente barulhento transforme pico de ingestão em atraso do Sentinel, comparando caminhos defensáveis antes de escolher a estratégia.

## Casos de uso

- Picos acima do throughput sustentado do barramento.
- Decisões que precisam preservar um SLA de tempo real enquanto outro consumidor tolera atraso.
- Mudanças em arquitetura de filas com restrição de custo e rejeição a perda de telemetry.

## Exemplo

Cenário do Checkpoint 04: throughput sustentado de 180k msgs/s, pico de 320k msgs/s por 25min, Sentinel tolera no máximo 60s de atraso, Forge até 15min, orçamento 8% acima do previsto e perda de telemetry inaceitável.

## Execução de referência

Modelo: GPT-5.6 Luna.

Recomendação resumida:

```text
RECOMENDAÇÃO:
priorizar Sentinel no consumo do Relay e combinar com isolamento de clientes barulhentos; usar expansão automática de consumidores como mecanismo elástico, com retenção suficiente para absorver o pico e sem descartar telemetry.

JUSTIFICATIVA:
A prioridade protege o SLA mais estrito; o isolamento reduz a chance de um tenant dominar a fila; autoscaling absorve picos sem exigir capacidade máxima permanente. DLQ não deve ser tratada como destino normal para telemetry que não pode ser perdida, mas pode ser usada apenas para mensagens efetivamente rejeitadas por um fluxo bem definido e reprocessável.
```

## Limitações

- A escolha final depende de capacidades reais de particionamento, prioridade, retenção e autoscaling do Relay.
- O prompt não calcula dimensionamento exato sem dados de backlog, consumo por tenant e latências.
- Uma DLQ não substitui retenção durável nem estratégia de replay quando perda é proibida.
