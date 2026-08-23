---
nome: migracao-forge-event-driven
descricao: Conduz uma cadeia de análise e planejamento para migrar o Forge de lote horário para processamento orientado a eventos, preservando dependências e reversibilidade.
versao: 1.0.0
tags:
  - data-platform
  - event-driven
  - migracao
  - arquitetura
inputs:
  - nome: estado_atual
    descricao: Arquitetura, fluxo de processamento, dependências e fragilidades atuais do Forge.
  - nome: requisitos_migracao
    descricao: Garantias que precisam ser mantidas durante a mudança, incluindo continuidade e ausência de big-bang.
  - nome: resultado_anterior
    descricao: Saída do elo anterior da cadeia; no primeiro elo, pode ser vazia.
---

Atue como um arquiteto de dados responsável por planejar uma migração incremental e reversível.

ESTADO ATUAL:
{{estado_atual}}

REQUISITOS DA MIGRAÇÃO:
{{requisitos_migracao}}

RESULTADO DO ELO ANTERIOR:
{{resultado_anterior}}

Execute esta cadeia em quatro elos. Use a saída de cada elo como entrada do seguinte.

ELO 1 — DIAGNÓSTICO
- descreva o fluxo atual;
- identifique acoplamentos e pontos de falha;
- liste o que precisa permanecer funcionando.

ELO 2 — ESTRATÉGIA
- proponha uma transição incremental;
- escolha pontos de coexistência entre lote e eventos;
- defina critérios de sucesso e de interrupção.

ELO 3 — PLANO DETALHADO
- transforme a estratégia em etapas pequenas;
- detalhe dados, consumidores, dual-run/compatibilidade quando necessários;
- destaque dependências do Sentinel, Cerebro e billing.

ELO 4 — REVERSIBILIDADE
- defina rollback por etapa;
- liste sinais que autorizam avançar;
- liste sinais que exigem pausa ou reversão;
- não permita big-bang.

Formato de cada elo:
OBJETIVO
SAÍDA
RISCOS
DECISÕES
ENTRADA PARA O PRÓXIMO ELO

Não invente tecnologias específicas que não sejam necessárias para explicar o plano.
