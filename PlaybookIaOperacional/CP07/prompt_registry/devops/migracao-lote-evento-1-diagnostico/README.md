---
nome: Migração Lote→Evento — Diagnóstico (Elo 1)
descricao: "Primeiro elo da cadeia: diagnostica pontos frágeis, consumidores por sensibilidade, riscos e pré-condições de um pipeline em lote."
versao: 1.0.0
tags: [migracao, arquitetura-de-dados, event-driven, diagnostico, prompt-chaining]
inputs:
  - nome: estado_atual
    descricao: "Descrição do pipeline hoje: ingestão em cron, etapas de transformação, destinos, dependências e pontos frágeis."
---

# Migração Lote→Evento — Diagnóstico (Elo 1)

## Objetivo

Primeiro elo de uma cadeia de três prompts (prompt chaining) para migrar um pipeline de lote para event-driven. Este elo apenas diagnostica — identifica pontos frágeis estruturais, mapeia consumidores por sensibilidade à latência, lista riscos de continuidade e aponta pré-condições. A saída alimenta o `{{diagnostico}}` do Elo 2.

## Quando usar

- No início da avaliação de uma migração lote→evento, antes de propor qualquer plano.
- Quando é preciso separar o que torna a migração necessária do que apenas seria desejável.
- Como primeiro passo da cadeia, cuja saída estruturada é entrada do elo de planejamento.

## Exemplo de uso

**Entrada (`{{estado_atual}}`):** o Forge, pipeline em cron de 60min com 14 etapas Spark encadeadas, consumido por Sentinel, Cerebro e billing.

**Saída (trecho):** pontos frágeis (job de 1h indivisível, efeito bola de neve, latência estrutural ~40min, cron como ponto único); consumidores por sensibilidade (Sentinel alta, Cerebro média, billing baixa mas crítica em janela); riscos de continuidade e pré-condições (instrumentação de lag ainda inexistente).

## Limitações conhecidas

- É apenas o diagnóstico — não propõe como migrar (isso é o Elo 2). Usar isolado não entrega um plano.
- A profundidade depende de `{{estado_atual}}` ser específico; descrições genéricas produzem diagnóstico genérico.
- Faz parte de uma cadeia: o valor pleno aparece quando a saída é passada ao Elo 2 (plano) e ao Elo 3 (detalhamento).
