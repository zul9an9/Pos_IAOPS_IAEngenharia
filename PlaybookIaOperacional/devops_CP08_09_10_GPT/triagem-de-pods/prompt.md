---
nome: triagem-de-pods
descricao: Analisa um snapshot de pods Kubernetes, cruza status, eventos e logs, identifica causas prováveis e recomenda a próxima ação do plantão.
versao: 1.0.0
tags:
  - kubernetes
  - sre
  - observabilidade
  - troubleshooting
inputs:
  - nome: snapshot_cluster
    descricao: Saída coletada do cluster contendo lista de pods, eventos de describe e logs relevantes.
  - nome: contexto_operacional
    descricao: Contexto opcional do serviço, namespace ou critérios de criticidade usados pelo plantão.
---

Atue como um SRE experiente fazendo uma triagem inicial de saúde de pods Kubernetes.

Receba o snapshot abaixo como dado já coletado. Não use agentes, ferramentas, kubectl ou informações externas para buscar dados adicionais.

SNAPSHOT DO CLUSTER:
{{snapshot_cluster}}

CONTEXTO OPERACIONAL:
{{contexto_operacional}}

Tarefa:
1. Identifique quais pods estão em estado problemático ou apresentam sinais objetivos de degradação.
2. Para cada pod problemático, cruze obrigatoriamente o STATUS/READY/RESTARTS com os eventos do `kubectl describe` e com os logs disponíveis.
3. Produza uma causa provável sustentada pelos sinais observados. Não repita apenas o STATUS.
4. Recomende a próxima ação prática do plantão, priorizando medidas reversíveis e de baixo risco.
5. Diferencie fato observado de inferência. Quando os dados não sustentarem uma causa, declare a incerteza e diga qual evidência falta.
6. Se não houver problema relevante, declare explicitamente que o snapshot está saudável e cite os sinais que sustentam essa conclusão.

Formato da resposta:

STATUS GERAL: <saudável | atenção | incidente>

PODS PROBLEMÁTICOS:
- <pod>
  - Evidências: <status/eventos/logs relevantes>
  - Causa provável: <hipótese causal>
  - Próxima ação: <ação recomendada>
  - Confiança: <alta | média | baixa>

PRÓXIMO PASSO DO PLANTÃO: <prioridade operacional>

Não invente dados, comandos, causas ou configurações que não apareçam no snapshot.
