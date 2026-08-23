# Testes determinísticos da correção de NetworkPolicy (origem: CP06).
# Rodar da pasta do prompt: `promptfoo eval`
#
# Providers: gpt-4o-mini + claude-haiku-4.5 — geração de YAML estruturado.
# O prompt conduz o próprio loop de verificação/refino, então a saída já vem
# curada; os asserts abaixo checam as invariantes de segurança do resultado.
description: "correcao-de-networkpolicy — YAML default-deny válido, sem allow-all, com fluxos e comentários"

prompts:
  - file://prompt.md

providers:
  - openai:gpt-4o-mini
  - anthropic:messages:claude-haiku-4-5-20251001

defaultTest:
  assert:
    - type: latency
      threshold: 5000
    - type: cost
      threshold: 0.01

tests:
  - description: "Manifesto permissivo sentinel-allow -> versão default-deny corrigida"
    vars:
      manifesto_permissivo: |
        apiVersion: networking.k8s.io/v1
        kind: NetworkPolicy
        metadata:
          name: sentinel-allow
          namespace: sentinel-prod
        spec:
          podSelector: {}
          policyTypes:
            - Ingress
            - Egress
          ingress:
            - {}
          egress:
            - {}
      padrao_seguranca: |
        - pods do Sentinel só aceitam ingress do Relay (consumo de eventos) e do gateway de API da plataforma
        - pods do Sentinel só fazem egress para: Forge (warehouse, porta 5432), Cerebro (busca, porta 9200) e DNS interno
        - nada de "allow all" em ingress ou egress
        - política default-deny explícita no namespace
        - toda regra precisa de comentário dizendo qual fluxo legítimo ela libera
      mapa_servicos: |
        Sentinel     -> namespace sentinel-prod, pods app=sentinel
        Relay        -> namespace relay-prod,    pods app=relay
        API gateway  -> namespace edge,          pods app=api-gateway
        Forge        -> namespace forge-prod,    pods app=forge,   porta 5432 (Postgres do warehouse)
        Cerebro      -> namespace cerebro-prod,  pods app=cerebro, porta 9200 (Elasticsearch)
        DNS interno  -> namespace kube-system,   pods k8s-app=kube-dns, porta 53
      provedor: "YAML Kubernetes (networking.k8s.io/v1)"
    assert:
      # é um manifesto de NetworkPolicy...
      - type: contains
        value: "kind: NetworkPolicy"
      # ...com os dois policyTypes
      - type: contains
        value: "Ingress"
      - type: contains
        value: "Egress"
      # sem regra allow-all (a saída não pode conter "- {}")
      - type: not-contains
        value: "- {}"
      # egress libera Forge:5432 e Cerebro:9200; ingress libera o Relay
      - type: contains
        value: "5432"
      - type: contains
        value: "9200"
      - type: contains
        value: "app: relay"
      # toda regra (from/to) tem pelo menos um comentário (#): nº de comentários >= nº de regras (>=3 regras)
      - type: javascript
        value: >-
          (output.match(/-\s+(from|to):/g) || []).length >= 3
          && (output.match(/#/g) || []).length >= (output.match(/-\s+(from|to):/g) || []).length
