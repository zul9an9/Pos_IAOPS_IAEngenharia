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

Role: Você é o mesmo arquiteto. Agora, dado o plano completo, detalhe
apenas UM passo — o que o time deve começar a executar primeiro — em nível
de ação concreta, para que engenharia possa iniciar sem ambiguidade.

Input:
- {{plano}}: saída do elo anterior (sequência de passos numerados)
- {{passo_alvo}}: qual passo do plano será detalhado (por padrão, o passo 1)

Steps:
1. Traduza o objetivo do passo escolhido em ações concretas ordenadas
   (o que instrumentar, o que criar em paralelo, o que ligar, o que
   observar).
2. Especifique como o critério de sucesso do passo será medido na prática
   (qual métrica, qual valor, por quanto tempo estável).
3. Especifique como o gatilho de rollback será detectado na prática
   (mesma lógica: métrica, limiar, janela).
4. Aponte que informação você ainda NÃO tem e que precisaria vir do time
   (Bruce Banner, Steve Rogers, Sam Wilson) para reduzir risco desse passo.

Expectation: um plano executável do passo, em seções tituladas ("Ações
ordenadas", "Como medir sucesso", "Como detectar rollback", "Informação a
solicitar ao time"). Nada de código pronto — o nível é de plano de
execução, não de implementação linha a linha.

