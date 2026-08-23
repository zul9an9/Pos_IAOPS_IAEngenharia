---
nome: Migração Lote→Evento — Detalhamento do Passo (Elo 3)
descricao: "Terceiro elo da cadeia: detalha um passo do plano em ações concretas, métricas de sucesso/rollback e informações a solicitar ao time."
versao: 1.0.0
tags: [migracao, arquitetura-de-dados, event-driven, execucao, prompt-chaining]
inputs:
  - nome: plano
    descricao: "Saída do Elo 2: a sequência de passos numerados da migração."
  - nome: passo_alvo
    descricao: Qual passo do plano será detalhado (por padrão, o passo 1).
---

# Migração Lote→Evento — Detalhamento do Passo (Elo 3)

## Objetivo

Terceiro e último elo da cadeia. Dado o plano completo, detalha apenas UM passo — o primeiro a executar — em ações concretas ordenadas, com o critério de sucesso e o gatilho de rollback traduzidos em métricas práticas, e aponta explicitamente a informação que ainda falta e precisa vir do time.

## Quando usar

- Depois do Elo 2, para transformar o passo escolhido em algo que engenharia comece a executar sem ambiguidade.
- Quando é preciso traduzir critério de sucesso e rollback abstratos em métrica, limiar e janela.
- Para deixar explícito o que ainda precisa ser respondido pelo time antes de reduzir o risco do passo.

## Exemplo de uso

**Entrada:** o `{{plano}}` do Elo 2 + `{{passo_alvo}}` = "Passo 1" (instrumentar o Forge atual).

**Saída (trecho):** ações ordenadas (definir as três métricas mínimas, instrumentar o job Spark nas bordas, criar dashboard no Sentinel, coletar baseline por 5 dias úteis incluindo uma falha induzida); como medir sucesso (métricas estáveis e explicáveis, não só presentes); como detectar rollback (job passando de 60min por custo da instrumentação); e informação a solicitar a Bruce Banner, Steve Rogers e Sam Wilson.

## Limitações conhecidas

- Detalha um único passo por execução; para os demais passos, roda-se de novo variando `{{passo_alvo}}`.
- Fica em nível de plano de execução — não gera código pronto nem implementação linha a linha.
- A utilidade depende de o `{{plano}}` recebido já trazer o passo com objetivo e critérios definidos (saída do Elo 2).
