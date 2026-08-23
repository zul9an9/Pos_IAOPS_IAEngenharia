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

Role: Você é o mesmo arquiteto do passo anterior. Agora, com o diagnóstico
em mãos, seu papel é propor o passo a passo da migração — sem detalhar
implementação ainda, só a sequência de passos e a lógica de cada um.

Input:
- {{diagnostico}}: saída do elo anterior (pontos frágeis, consumidores,
  riscos, pré-condições)
- {{restricoes}}: as restrições explícitas da migração (consumo contínuo
  do Relay, manter dependentes funcionando, nada de big-bang, reversível)

Steps:
1. Proponha uma sequência de passos ordenada, do estado atual (lote) ao
   estado alvo (event-driven). Cada passo precisa: (a) ser reversível
   isoladamente; (b) manter os consumidores identificados no diagnóstico
   funcionando durante o passo; (c) endereçar pelo menos um dos pontos
   frágeis ou riscos do diagnóstico.
2. Para cada passo, identifique explicitamente qual é o critério de
   sucesso que autoriza avançar para o próximo (não avançar por tempo,
   avançar por evidência).
3. Para cada passo, identifique o gatilho de rollback — que sinal indica
   que o passo precisa ser desfeito.

Expectation: uma sequência numerada de passos, cada um com "Objetivo",
"Critério de sucesso", "Gatilho de rollback". A cadeia deve terminar no
estado event-driven pretendido, mas nenhum passo isolado pode ser um
big-bang. Não entre em detalhe de código, tooling ou vendor — isso é a
próxima etapa.
