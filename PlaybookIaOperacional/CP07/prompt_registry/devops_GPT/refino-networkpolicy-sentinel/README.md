---
nome: refino-networkpolicy-sentinel
descricao: Corrige uma NetworkPolicy permissiva, verifica seletores e fluxos legítimos e refina o manifesto por rodadas de crítica de segurança.
versao: 1.0.0
tags:
  - kubernetes
  - networkpolicy
  - seguranca
  - devsecops
inputs:
  - nome: manifesto_atual
    descricao: NetworkPolicy atual a ser revisada.
  - nome: requisitos_de_seguranca
    descricao: Fluxos permitidos e restrições que a política corrigida deve respeitar.
  - nome: mapa_de_servicos
    descricao: Namespaces, labels e portas que podem ser usados para construir os seletores sem inventar rótulos.
  - nome: resultado_anterior
    descricao: Manifesto e perguntas de revisão produzidos pela rodada anterior, quando houver.
---

# Refino de NetworkPolicy do Sentinel

## Objetivo

Transformar uma política Kubernetes permissiva em uma política restritiva e revisável, submetendo a saída a pelo menos uma rodada crítica antes de tratá-la como versão final.

## Casos de uso

- Revisão de políticas antes de deploy.
- Migração para default-deny.
- Ajuste de ingress/egress com seletores conhecidos.

## Execução de referência

Modelo: GPT-5.6 Luna.

### V1 — correção inicial

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-default-deny
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel
  policyTypes:
    - Ingress
    - Egress
```

A rodada de segurança percebe que o manifesto acima estabelece isolamento, mas ainda não libera os fluxos legítimos exigidos.

### Crítica

```text
- Falta ingress do Relay e do API gateway.
- Falta egress para Forge:5432 e Cerebro:9200.
- Falta egress para DNS interno:53.
- A intenção default-deny está correta para os pods selecionados, mas as exceções necessárias precisam ser explícitas.
```

### V2 — refinamento

A versão final deve conter regras de `from` e `to` usando os namespaces e labels fornecidos pelo checkpoint, com portas 5432, 9200 e 53 onde especificadas, além de comentários que expliquem cada fluxo.

## Limitações

- A NetworkPolicy não cria infraestrutura que não exista; selectors válidos dependem dos labels reais.
- A implementação de default-deny é por pod/policyTypes e deve ser validada no cluster alvo.
- O prompt não substitui revisão de segurança nem testes de conectividade.
