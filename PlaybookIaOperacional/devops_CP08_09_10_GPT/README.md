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

# Migração do Forge para event-driven

## Objetivo

Quebrar uma migração grande em uma sequência de decisões menores, usando a saída de cada etapa como entrada da próxima e preservando rollback.

## Casos de uso

- Migração de jobs batch para consumidores contínuos.
- Mudanças em pipelines com vários consumidores downstream.
- Projetos em que dual-run, coexistência e rollback são necessários.

## Execução de referência

Modelo: GPT-5.6 Luna.

### Elo 1 — diagnóstico

```text
O Forge tem um agendamento horário, 14 etapas Spark (~40min), tabelas particionadas por hora e dependências do Sentinel, Cerebro e billing. O principal risco é alterar o ritmo de disponibilidade sem quebrar os consumidores existentes.
```

### Elo 2 — estratégia

```text
Introduzir consumo contínuo em paralelo ao batch, validar equivalência dos resultados e mover consumidores gradualmente. Evitar desligar o batch antes de comprovar cobertura e correção do novo fluxo.
```

### Elo 3 — plano

```text
1. instrumentar métricas de equivalência e lag;
2. executar fluxo contínuo em paralelo;
3. comparar resultados;
4. migrar consumidores por dependência;
5. reduzir gradualmente o batch;
6. aposentar o batch apenas após janela de estabilidade.
```

### Elo 4 — reversibilidade

```text
Rollback: reativar o caminho batch e os consumidores anteriores enquanto o fluxo novo é isolado. Reverter diante de divergência de dados, lag acima do limite ou impacto em Sentinel/Cerebro/billing.
```

## Limitações

- Não define implementação tecnológica detalhada sem requisitos adicionais.
- A cadeia depende de métricas de equivalência, qualidade dos dados e critérios de aceite reais.
- O parâmetro `resultado_anterior` é essencial para manter a continuidade entre os elos.
