---
nome: Triagem de Pods
descricao: Cruza get/describe/logs de um snapshot do Kubernetes e devolve causa provável e ação por pod problemático.
versao: 1.0.0
tags: [kubernetes, sre, triagem, observabilidade, incidentes]
inputs:
  - nome: snapshot
    descricao: Bloco de texto com a saída de `kubectl get pods`, `kubectl describe pod` dos pods relevantes e trechos de log das aplicações.
---

# Triagem de Pods

## Objetivo

Servir de apoio de triagem para o plantão: recebe um snapshot já coletado do cluster e devolve, por pod problemático, a causa provável (cruzando status, eventos e logs — não apenas repetindo o `Reason` do describe) e a próxima ação concreta.

## Quando usar

- Durante um plantão, ao receber o snapshot de `kubectl` de um cluster com pods instáveis.
- Quando o `Reason` do describe (OOMKilled, ImagePullBackOff, Pending) não explica sozinho o mecanismo por trás da falha.
- Para decidir a próxima ação concreta, e não abrir uma investigação genérica.

## Exemplo de uso

**Entrada (`{{snapshot}}`):** pod `sentinel-api-...-h4m2t` reiniciando, limite de memória 512Mi, log mostrando heap subindo de 410Mi a 498Mi com "high GC pressure" antes de "out of memory".

**Saída (trecho):**
```
Pod: sentinel-api-7d9c8b6f4-h4m2t
Causa provável: OOMKilled. O heap sobe de 410Mi (carga do cache de alertas) até 498Mi contra o limite de 512Mi — estoura o próprio limite sob carga normal de startup, não é pico anômalo.
Ação recomendada: Aumentar o limite de memória (768Mi–1Gi) como mitigação e investigar o tamanho do cache carregado no startup.
```

## Limitações conhecidas

- A qualidade da análise depende diretamente da completude do snapshot; sem logs ou eventos, o cruzamento de fontes fica prejudicado.
- Não acessa o cluster ao vivo — trabalha só com o texto colado na entrada.
- Formato de saída rígido, pensado para ser validado por asserts de regex no CP08; alterá-lo quebra os testes.

