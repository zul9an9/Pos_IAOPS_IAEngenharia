---
nome: Migração Lote→Evento — Plano (Elo 2)
descricao: "Segundo elo da cadeia: transforma o diagnóstico em uma sequência de passos reversíveis, com critério de sucesso e gatilho de rollback por passo."
versao: 1.0.0
tags: [migracao, arquitetura-de-dados, event-driven, planejamento, prompt-chaining]
inputs:
  - nome: diagnostico
    descricao: "Saída do Elo 1: pontos frágeis, consumidores por sensibilidade, riscos e pré-condições."
  - nome: restricoes
    descricao: Restrições explícitas da migração (consumo contínuo do Relay, manter dependentes funcionando, nada de big-bang, reversível).
---

# Migração Lote→Evento — Plano (Elo 2)

## Objetivo

Segundo elo da cadeia. A partir do diagnóstico do Elo 1 e das restrições, produz a sequência de passos da migração — cada passo reversível isoladamente, mantendo consumidores funcionando e endereçando pelo menos um ponto frágil — com critério de sucesso (avançar por evidência) e gatilho de rollback por passo. A saída alimenta o `{{plano}}` do Elo 3.

## Quando usar

- Depois do Elo 1, com o diagnóstico em mãos, para desenhar o caminho da migração.
- Quando a restrição inegociável é não fazer big-bang e poder reverter cada passo.
- Para produzir um plano operável (com critérios de avanço e reversão), não um roteiro abstrato.

## Exemplo de uso

**Entrada:** o `{{diagnostico}}` do Elo 1 + as três restrições da migração.

**Saída (trecho):** cinco passos numerados — (1) instrumentar o lote atual, (2) rodar consumer event-driven em modo sombra, (3) migrar uma etapa de transformação por vez, (4) cortar consumidores um a um (Cerebro → Sentinel → billing), (5) desligar o lote — cada um com Objetivo, Critério de sucesso e Gatilho de rollback, sendo o desligamento o único passo irreversível e por isso o último.

## Limitações conhecidas

- Depende de um `{{diagnostico}}` estruturado como entrada; sem ele, o plano perde o acoplamento com o cenário real.
- Fica no nível de sequência e lógica dos passos — não entra em código, tooling ou vendor (isso é o Elo 3).
- As restrições precisam estar completas: uma restrição não declarada não será respeitada no plano.
