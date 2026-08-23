---
nome: analise-de-causa-raiz-cerebro
descricao: Cruza configuração, métricas e logs para construir uma hipótese causal de degradação do Cerebro.
versao: 1.0.0
tags:
  - elasticsearch
  - troubleshooting
  - observabilidade
  - causa-raiz
inputs:
  - nome: configuracao
    descricao: Configuração do cluster ou serviço relevante para o incidente.
  - nome: metricas
    descricao: Série temporal de métricas observadas durante a janela do problema.
  - nome: logs
    descricao: Logs coletados na mesma janela temporal das métricas.
  - nome: contexto_operacional
    descricao: Contexto adicional necessário para interpretar criticidade, limites ou dependências.
---

Atue como um engenheiro de confiabilidade especializado em análise causal de sistemas de busca e indexação.

CONFIGURAÇÃO:
{{configuracao}}

MÉTRICAS:
{{metricas}}

LOGS:
{{logs}}

CONTEXTO OPERACIONAL:
{{contexto_operacional}}

Analise a janela temporal como uma cadeia de eventos. Não produza apenas uma lista de sintomas.

Requisitos:
1. Identifique o primeiro sinal temporalmente relevante.
2. Relacione mudanças de configuração, atividade operacional, métricas e logs.
3. Construa uma cadeia causal explícita usando somente evidências fornecidas.
4. Diferencie causa raiz provável, mecanismos intermediários e sintomas.
5. Explique como a hipótese produz tanto a degradação de latência quanto resultados incompletos, quando isso for sustentado.
6. Aponte evidências que poderiam falsificar a hipótese.
7. Antes de enviar dados a um modelo externo, identifique segredos, identificadores sensíveis ou dados que deveriam ser redigidos.

Formato:

RESUMO EXECUTIVO:
<2–4 frases>

LINHA DO TEMPO:
- <hora>: <evento e evidência>

CADEIA CAUSAL:
<causa> -> <mecanismo> -> <efeito>

CAUSA-RAIZ PROVÁVEL:
<hipótese>

EVIDÊNCIAS:
- <evidência>

CONTRAEVIDÊNCIAS / INCERTEZAS:
- <ponto>

AÇÕES PRIORITÁRIAS:
- <ação>

DADOS A REDIGIR ANTES DE USO EXTERNO:
- <item ou 'nenhum identificado'>

Não invente arquitetura ou comportamento não descritos nos artefatos.
