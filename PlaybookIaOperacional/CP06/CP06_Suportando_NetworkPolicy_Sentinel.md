# CP06 — Suportando a NetworkPolicy do Sentinel

> **Papel:** engenheiro de segurança de redes / segurança de TI
> **Framework do prompt:** RISE (Role · Input · Steps · Expectation)
> **Método:** prompt parametrizável criado via meta-prompting + loop de verificação/refino conduzido
> **Entregável de biblioteca:** o prompt parametrizável da seção 1 (o resto é execução curada)

---

## 1. Prompt parametrizável (artefato da biblioteca)

Este é o item que entra no playbook. Ele **não** resolve um caso único: recebe qualquer
manifesto permissivo, o padrão de segurança e o mapa de serviços por parâmetro, e devolve
a política corrigida **junto com** o log de verificação/refino.

```text
### ROLE
Você é engenheiro de segurança de redes Kubernetes, especialista em NetworkPolicy
e no modelo default-deny (allow-list). Você é conservador: nunca libera mais do que
o fluxo declarado, nunca inventa rótulos, e trata todo manifesto recebido como
potencialmente permissivo demais até prova em contrário.

### INPUT (parâmetros)
- MANIFESTO_PERMISSIVO: {{MANIFESTO_PERMISSIVO}}   # o manifesto barrado na revisão
- PADRAO_SEGURANCA:     {{PADRAO_SEGURANCA}}       # as regras que a versão corrigida deve seguir
- MAPA_SERVICOS:        {{MAPA_SERVICOS}}          # namespace + label + porta de cada serviço
- PROVEDOR:             {{PROVEDOR}}               # provedor/modelo de destino (formatação da saída)

### STEPS
1. AUDITORIA. Leia MANIFESTO_PERMISSIVO e liste, item a item, cada violação
   (podSelector aberto, regras `- {}`, allow-all em ingress/egress, ausência de default-deny).
2. GERAÇÃO v1. Produza a NetworkPolicy corrigida obedecendo PADRAO_SEGURANCA e MAPA_SERVICOS.
   Restrições rígidas:
   - identifique namespaces pelo rótulo real `kubernetes.io/metadata.name: <namespace>`
     (imutável, presente em todo namespace desde o k8s 1.21). NÃO invente labels;
   - use exatamente os labels de pod do MAPA_SERVICOS;
   - toda regra carrega um comentário `#` dizendo qual fluxo legítimo ela libera.
3. VERIFICAÇÃO. Assuma o papel de revisor de segurança e levante as perguntas de
   verificação que ele faria sobre a v1. No mínimo:
   - Em cada `from`/`to`, `namespaceSelector` e `podSelector` estão no MESMO item de lista
     (AND = pod dentro do namespace) ou em itens SEPARADOS (OR = vaza)?
   - DNS está liberado em UDP **e** TCP na porta 53?
   - Existe uma policy default-deny EXPLÍCITA cobrindo todo o namespace, ou só o implícito
     dos pods selecionados?
   - As portas de egress estão restritas (nada de saída sem porta)?
   - Sobrou algum `- {}` ou seletor vazio?
   - Toda regra tem comentário?
4. REFINO. Gere v2 (e v3 se necessário) resolvendo cada ponto levantado. Registre,
   para cada versão, O QUE mudou e POR QUÊ.

### EXPECTATION
Saída em três blocos:
(a) LOG das iterações — auditoria, v1, perguntas de verificação, diffs de v2/v3;
(b) MANIFESTOS FINAIS válidos, prontos para `kubectl apply`, no formato do PROVEDOR:
    uma policy `default-deny-all` + a policy específica do serviço, cada regra comentada;
(c) NOTA DE CURADORIA — decisões em aberto que exigem carimbo humano.
Nunca emita allow-all. Se um dado faltar no MAPA_SERVICOS, marque `[VALIDAR]` em vez de inferir.
```
---
## 2. Execução curada — instância do CP06

Parâmetros injetados nesta rodada:

- **`MANIFESTO_PERMISSIVO`** = o `sentinel-allow` barrado pela Natasha (podSelector `{}`, ingress `- {}`, egress `- {}`).
- **`PADRAO_SEGURANCA`** = ingress só de Relay + API gateway; egress só p/ Forge:5432, Cerebro:9200 e DNS; sem allow-all; default-deny explícito; comentário por regra.
- **`MAPA_SERVICOS`** = tabela namespace/label/porta do enunciado.
- **`PROVEDOR`** = YAML Kubernetes (`networking.k8s.io/v1`).

### 2.1. Auditoria do manifesto permissivo

| # | Violação encontrada | Impacto |
|---|---------------------|---------|
| 1 | `podSelector: {}` | aplica a **todos** os pods do namespace, não só ao Sentinel |
| 2 | `ingress: - {}` | aceita **qualquer** origem |
| 3 | `egress: - {}` | permite **qualquer** destino (exfiltração livre) |
| 4 | ausência de default-deny | o resto do namespace segue sem baseline de negação |

Diagnóstico: é um *allow-all* disfarçado de política. Descartar e reconstruir.

### 2.2. v1 — primeira geração (contém falhas propositais reais)

```yaml
# v1 — NÃO aplicar. Registrada para o log de refino.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-netpol
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: relay-prod
        - podSelector:                      # <-- item SEPARADO => vira OR
            matchLabels:
              app: relay
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: edge
        - podSelector:
            matchLabels:
              app: api-gateway
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: forge-prod
        - podSelector:                      # <-- item SEPARADO => vira OR
            matchLabels:
              app: forge
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: cerebro-prod
        - podSelector:
            matchLabels:
              app: cerebro
      ports:
        - protocol: TCP
          port: 9200
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP                     # <-- só UDP, falta TCP 53
          port: 53
```

### 2.3. Verificação — perguntas do revisor de segurança (Natasha)

1. **AND ou OR?** Em `ingress[0].from` e nos dois primeiros `egress`, `namespaceSelector`
   e `podSelector` estão em **itens de lista separados** → o k8s interpreta como **OR**.
   Consequência real: libera *todos* os pods de `relay-prod` (qualquer label) **e** qualquer
   pod `app=relay` em *qualquer* namespace. Mesma falha em `forge-prod`/`cerebro-prod`.
   **Fura o princípio de menor privilégio.**
2. **DNS incompleto.** Só UDP 53. Respostas DNS grandes e alguns resolvers usam **TCP 53** →
   resolução intermitente e egress bloqueado sem motivo aparente.
3. **Default-deny ausente.** A v1 nega o não-listado *apenas* para os pods `app=sentinel`.
   O padrão pede baseline **explícito para todo o namespace**.
4. **Comentários por regra.** Faltam — o padrão Aegis exige um `#` por fluxo.
5. **Sobras `- {}`?** Nenhuma. ✔
6. **Portas de egress restritas?** Sim (5432/9200/53). ✔

### 2.4. v2 — endereça 1, 2, 3 e 4

- Colapsa `namespaceSelector` + `podSelector` no **mesmo item** de lista (AND).
- Acrescenta **TCP 53** ao DNS.
- Adiciona a policy separada **`default-deny-all`**.
- Comenta cada regra.

### 2.5. v3 — polimento final

- Confirma que `kubernetes.io/metadata.name` é o rótulo **real** de namespace (não inventado).
- Confirma o label do CoreDNS/kube-dns: `k8s-app: kube-dns`.
- Registra a decisão em aberto sobre **fixar porta no ingress** (ver Nota de curadoria).
- Sem mudança estrutural além disso → v3 é a versão curada.

---

## 3. Manifestos finais (curados) — prontos para `kubectl apply`

### 3.1. Baseline: default-deny explícito no namespace

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: sentinel-prod
spec:
  podSelector: {}            # aplica a TODOS os pods do namespace
  policyTypes:
    - Ingress
    - Egress
  # sem blocos ingress/egress = nega toda entrada e toda saída por padrão.
  # As liberações vêm, de forma aditiva, na policy específica abaixo.
```

### 3.2. Policy específica do Sentinel

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-netpol
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel          # aplica só aos pods do Sentinel
  policyTypes:
    - Ingress
    - Egress

  ingress:
    # ingress 1: consumo de eventos vindo do Relay (namespace relay-prod, app=relay)
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: relay-prod
          podSelector:                      # MESMO item => AND (pod app=relay DENTRO de relay-prod)
            matchLabels:
              app: relay

    # ingress 2: tráfego do API gateway da plataforma (namespace edge, app=api-gateway)
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: edge
          podSelector:
            matchLabels:
              app: api-gateway

  egress:
    # egress 1: consulta ao warehouse Postgres do Forge (forge-prod, app=forge, 5432/TCP)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: forge-prod
          podSelector:
            matchLabels:
              app: forge
      ports:
        - protocol: TCP
          port: 5432

    # egress 2: busca no Cerebro / Elasticsearch (cerebro-prod, app=cerebro, 9200/TCP)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: cerebro-prod
          podSelector:
            matchLabels:
              app: cerebro
      ports:
        - protocol: TCP
          port: 9200

    # egress 3: resolução de DNS interno (kube-system, k8s-app=kube-dns, 53 UDP+TCP)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

---

## 4. Nota de curadoria

- **Ordem de aplicação:** aplicar `default-deny-all` **primeiro**. Como as policies são
  aditivas (allow-list), a `sentinel-netpol` só reabre os fluxos declarados para os pods
  `app=sentinel`; o resto do namespace permanece negado.
- **Decisão em aberto (carimbo humano):** o padrão não fixou **porta de ingress** do Sentinel.
  A versão curada deixa o ingress sem restrição de porta (todas as portas dos pods Sentinel
  ficam acessíveis a Relay e API gateway). Se o Sentinel expõe uma porta única de consumo,
  vale pinar essa porta no `ingress` — `[VALIDAR]` com a Natasha.
- **Pré-requisito de ambiente:** os `namespaceSelector` dependem do rótulo automático
  `kubernetes.io/metadata.name`. Em clusters < 1.21 (ou com `NamespaceDefaultLabelName`
  desabilitado) esse rótulo não existe → rotular os namespaces manualmente antes de aplicar.
- **Egress de DNS:** mantidos UDP **e** TCP 53. Remover o TCP reintroduz falha intermitente
  de resolução — foi exatamente o ponto pego na v1.

---

## Apêndice — meta-prompt semente (não faz parte da biblioteca)

O prompt da seção 1 foi derivado dirigindo a IA com o meta-prompt abaixo. Guardado só
para rastreabilidade; o artefato versionado é o prompt parametrizável, não este.

```text
Você é um projetista de prompts para um playbook de segurança de redes.
Gere um PROMPT PARAMETRIZÁVEL (framework RISE) que:
- receba por parâmetro um manifesto de NetworkPolicy permissivo, um padrão de segurança
  e um mapa de serviços (namespace/label/porta);
- produza a NetworkPolicy corrigida em modelo default-deny, sem inventar labels;
- conduza ele mesmo um loop de verificação/refino, assumindo o papel de revisor de
  segurança, cobrindo no mínimo: AND vs OR em from/to, DNS UDP+TCP, default-deny explícito
  no namespace, restrição de portas de egress, comentário por regra e ausência de `- {}`;
- registre as iterações (v1 -> perguntas -> v2 -> v3) e separe uma nota de curadoria.
Devolva só o prompt final, pronto para uso, com placeholders {{...}}.
```
