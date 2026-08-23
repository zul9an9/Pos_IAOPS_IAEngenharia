---
nome: nota-de-triagem
descricao: Converte um alerta operacional cru em uma nota de triagem padronizada para continuidade do plantão.
versao: 1.0.0
tags:
  - sre
  - incidentes
  - triagem
  - observabilidade
inputs:
  - nome: alerta_cru
    descricao: Texto bruto do alerta contendo timestamps, sistema, sintomas, impacto aparente e contexto disponível.
---

# Nota de triagem

## Objetivo

Padronizar anotações de plantão a partir de alertas crus, mantendo a sequência operacional consolidada pelo time: alerta, impacto, hipótese inicial, ação imediata e critério de escala.

## Casos de uso

- Registro rápido durante incidentes.
- Passagem de turno sem depender de estilo individual.
- Consolidação de alertas de Relay, Forge, Sentinel e componentes relacionados.

## Exemplo

Entrada do Checkpoint 02:

```text
2026-05-13 03:11:00 UTC [Relay] ingest reject rate 6% for 8min, tenant wakanda-systems,
buffer saturated after deploy 02:55
```

Saída de referência:

```text
ALERTA: Relay - taxa de rejeição de ingestão em 6% por 8min
IMPACTO: ingestão do tenant wakanda-systems degradada; buffer saturado
HIPÓTESE INICIAL: mudança implantada às 02:55 elevou a rejeição e levou o buffer à saturação
AÇÃO IMEDIATA: investigar/mitigar o deploy de 02:55 e acompanhar a taxa de rejeição
ESCALAR PARA: time responsável pelo Relay se a rejeição não cair após a mitigação
```

## Limitações

- O prompt não deve inventar impacto ou times que não estejam no alerta.
- A hipótese é inicial e precisa ser atualizada conforme novas evidências aparecem.
