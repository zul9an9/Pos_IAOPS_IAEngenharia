---
nome: Decisão de Backpressure
descricao: Compara estratégias de backpressure contra cada restrição de negócio e engenharia antes de recomendar, expondo o trade-off aceito.
versao: 1.0.0
tags: [backpressure, arquitetura, capacidade, decisao, confiabilidade]
inputs:
  - nome: estado_relay
    descricao: "Estado do sistema sob pressão: throughput atual, pico observado, retenção e consumidores."
  - nome: restricoes
    descricao: Regras de negócio e engenharia que qualquer solução precisa respeitar (SLAs por consumidor, orçamento, tolerância a perda).
---

# Decisão de Backpressure

## Objetivo

Forçar a IA a comparar múltiplas estratégias de backpressure avaliando CADA estratégia contra CADA restrição individualmente, antes de recomendar — em vez de entregar uma resposta única disfarçada de análise. A recomendação sempre declara o trade-off aceito e a informação que mudaria a decisão.

## Quando usar

- Diante de uma decisão de capacidade cara, com restrições concorrentes de naturezas diferentes (SLAs técnicos, orçamento, requisito de negócio).
- Quando o valor está no raciocínio comparativo explícito, não numa recomendação rápida.
- Para expor o que está sendo sacrificado, evitando a ilusão de uma solução sem custo.

## Exemplo de uso

**Entrada:** estado do Relay (pico de 320k msgs/s vindo de um único tenant) + restrições (SLA Sentinel 60s, SLA Forge 15min, orçamento +8%, perda de mensagem inegociável).

**Saída (trecho):** avalia priorização, DLQ, sharding por tenant e autoscaling contra cada restrição; recomenda uma **combinação** (priorizar Sentinel + DLQ só no excedente do Forge + autoscaling escopado ao Forge), deixa sharding como melhoria de médio prazo, e declara os trade-offs aceitos (atraso de até 15min no Forge, custo extra do autoscaling).

## Limitações conhecidas

- A saída é deliberadamente aberta (frequentemente uma combinação de estratégias) — exige julgamento humano para fechar, não é um veredito determinístico.
- A qualidade da comparação depende de as restrições virem bem descritas e completas em `{{restricoes}}`; restrição omitida não é avaliada.
- Esse tipo de saída aberta pedirá avaliação por julgamento (LLM-as-judge) em vez de assert determinístico quando for testada.
