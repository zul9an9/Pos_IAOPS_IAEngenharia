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

# Triagem de pods

## Objetivo

Transformar um snapshot já coletado do Kubernetes em uma triagem legível, cruzando estado, eventos e logs para chegar à causa provável e à próxima ação do plantão.

## Casos de uso

- Plantões SRE em que um pod reinicia, não sobe ou perde disponibilidade.
- Primeira triagem antes de escalar para o time responsável pelo serviço.
- Situações em que é importante separar sintoma (`CrashLoopBackOff`, `Pending`, `ImagePullBackOff`) de causa.

## Exemplo

Entrada baseada no primeiro caso do Checkpoint 01:

```text
$ kubectl get pods -n sentinel-prod
sentinel-api-7d9c8b6f4-h4m2t  0/1  CrashLoopBackOff  14 (90s ago)  42m

Last State: Terminated / OOMKilled / Exit Code 137
Limits: memory: 512Mi

Logs:
heap 410Mi/512Mi
heap 498Mi/512Mi
out of memory, shutting down process
```

Execução de referência: o resultado deve apontar que o pod está em `CrashLoopBackOff`, mas que a causa provável é pressão de memória culminando em `OOMKilled`, sustentada pelo heap próximo ao limite e pelo log fatal de falta de memória. A próxima ação deve ser investigar o consumo de memória e a adequação do limite antes de apenas reiniciar o pod.

## Modelo e saída de referência

Modelo: GPT-5.6 Luna, usado nesta migração para executar o prompt contra os dados do checkpoint.

Saída resumida:

```text
STATUS GERAL: incidente

PODS PROBLEMÁTICOS:
- sentinel-api-7d9c8b6f4-h4m2t
  - Evidências: CrashLoopBackOff; Last State OOMKilled; Exit Code 137; heap 498Mi/512Mi; log de falta de memória.
  - Causa provável: limite de memória insuficiente para a carga de cache, provocando pressão de heap e OOMKill.
  - Próxima ação: confirmar o padrão de consumo e revisar limite/uso de memória antes de nova intervenção.
  - Confiança: alta

PRÓXIMO PASSO DO PLANTÃO: investigar a pressão de memória e acompanhar os demais pods.
```

## Limitações

- O prompt não coleta dados do cluster e depende integralmente do snapshot fornecido.
- A causa provável é uma hipótese baseada nas evidências disponíveis, não prova causal definitiva.
- Um snapshot incompleto pode levar a uma hipótese de baixa confiança.
