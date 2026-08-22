---
nome: Correção de NetworkPolicy
descricao: Recebe um manifesto de NetworkPolicy permissivo e produz a versão default-deny corrigida, com loop de verificação e refino conduzido.
versao: 1.0.0
tags: [kubernetes, seguranca, networkpolicy, default-deny, hardening]
inputs:
  - nome: manifesto_permissivo
    descricao: O manifesto de NetworkPolicy barrado na revisão, a ser corrigido.
  - nome: padrao_seguranca
    descricao: As regras que a versão corrigida deve seguir (fluxos de ingress/egress permitidos, default-deny, comentário por regra).
  - nome: mapa_servicos
    descricao: "Mapa de identificação de cada serviço no cluster: namespace, label de pod e porta."
  - nome: provedor
    descricao: Provedor/modelo de destino, que define a formatação da saída.
---

# Correção de NetworkPolicy

## Objetivo

Receber um manifesto de NetworkPolicy permissivo e produzir a versão corrigida em modelo default-deny (allow-list), conduzindo um loop de verificação e refino em que a IA critica a própria saída (v1 → perguntas de revisão → v2 → v3). Entrega os manifestos finais comentados mais o log das iterações e uma nota de curadoria.

> **Nota de migração.** Os placeholders deste prompt foram normalizados para `snake_case` minúsculo na migração, seguindo a convenção `{{nome_variavel}}` do registry (o original do CP06 usava MAIÚSCULAS).

## Quando usar

- Ao revisar ou corrigir um manifesto de NetworkPolicy antes de aplicá-lo a um namespace de produção.
- Para fazer hardening de rede em um namespace, garantindo default-deny explícito e egress restrito por porta.
- Quando é crítico evitar as armadilhas clássicas (AND vs OR em `from`/`to`, DNS sem TCP, allow-all disfarçado).

## Exemplo de uso

**Entrada:** o manifesto `sentinel-allow` (podSelector `{}`, ingress `- {}`, egress `- {}` — um allow-all) + o padrão da Aegis + o mapa de serviços.

**Saída (trecho):** log das iterações pegando na v1 o `namespaceSelector`/`podSelector` em itens separados (vira OR e vaza) e o DNS só em UDP; a v2 colapsa os seletores no mesmo item (AND), adiciona TCP 53 e uma policy `default-deny-all` separada; a versão curada entrega os dois manifestos comentados, prontos para `kubectl apply`.

## Limitações conhecidas

- A correção depende de o `{{mapa_servicos}}` estar correto e completo; dado ausente é marcado `[VALIDAR]` em vez de inferido.
- Os `namespaceSelector` dependem do rótulo automático `kubernetes.io/metadata.name` (k8s ≥ 1.21); em clusters mais antigos é preciso rotular os namespaces manualmente.
- Decisões sem base no padrão (ex.: fixar porta de ingress) ficam como pergunta de curadoria para carimbo humano, não são resolvidas pelo prompt.

