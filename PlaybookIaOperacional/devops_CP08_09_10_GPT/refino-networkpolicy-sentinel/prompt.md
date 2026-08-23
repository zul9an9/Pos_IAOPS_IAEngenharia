---
nome: refino-networkpolicy-sentinel
descricao: Corrige uma NetworkPolicy permissiva, verifica seletores e fluxos legítimos e refina o manifesto por rodadas de crítica de segurança.
versao: 1.1.0
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

Atue como revisor de segurança Kubernetes especializado em NetworkPolicy.

MANIFESTO ATUAL:
{{manifesto_atual}}

REQUISITOS DE SEGURANÇA:
{{requisitos_de_seguranca}}

MAPA DE SERVIÇOS:
{{mapa_de_servicos}}

RESULTADO DA RODADA ANTERIOR:
{{resultado_anterior}}

Produza uma revisão iterativa.

RODADA 1 — V1
1. Identifique explicitamente os elementos permissivos ou incorretos.
2. Gere uma política corrigida sem inventar labels ou namespaces.
3. Explique cada regra e adicione comentários no YAML para os fluxos legítimos.

RODADA 2 — CRÍTICA
Revise a V1 como um segundo revisor de segurança. Pergunte:
- existe allow-all implícito ou explícito?
- ingress e egress estão restritos às origens/destinos exigidos?
- os selectors usam exatamente o mapa fornecido?
- as portas estão restritas quando o requisito fornece porta?
- DNS interno está contemplado?
- a política continua compreensível e revisável?

RODADA 3 — V2/V3
Corrija os achados e apresente uma nova versão. Registre o que mudou e por quê.

Formato:

V1:
```yaml
...
```

ACHADOS DA CRÍTICA:
- ...

V2 (ou V3):
```yaml
...
```

MUDANÇAS:
- ...

Não trate `podSelector: {}` ou regras `ingress: - {}` / `egress: - {}` como restrições. Não invente labels, namespaces ou dependências.
