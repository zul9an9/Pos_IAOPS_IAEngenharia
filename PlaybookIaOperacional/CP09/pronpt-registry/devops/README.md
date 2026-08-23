# DevOps

Prompts voltados a **infraestrutura, automação e operação** de sistemas: pipelines de CI/CD, containers, orquestração, provisionamento, observabilidade, confiabilidade e segurança operacional.

## Escopo

Entram aqui prompts relacionados a:

- Pipelines de CI/CD (GitHub Actions, GitLab CI, Jenkins etc.).
- Containers e orquestração (Docker, Kubernetes, Helm).
- Infraestrutura como código (Terraform, Pulumi, Ansible).
- Provedores de nuvem (AWS, GCP, Azure) e seus recursos.
- Observabilidade (logs, métricas, tracing, alertas, dashboards).
- Confiabilidade, SRE, postmortems e análise de incidentes.
- Segurança operacional (hardening, secrets, políticas de acesso).

## Fora de escopo

- Escrita de código de aplicação → usar `desenvolvimento/`.
- Conteúdo educacional sobre DevOps (aulas, artigos, vídeos) → usar `criacao-conteudo/`.

## Prompts

- [triagem-de-pods](./triagem-de-pods/) — Cruza get/describe/logs de um snapshot do Kubernetes e devolve causa provável e ação por pod problemático.
- [nota-de-triagem-de-alerta](./nota-de-triagem-de-alerta/) — Converte um alerta cru do Sentinel em nota de triagem padronizada de cinco campos para o plantão.
- [analise-de-causa-raiz](./analise-de-causa-raiz/) — Cruza config, métricas e logs de uma janela para separar causa-raiz de sintomas e propor ação proporcional.
- [decisao-de-backpressure](./decisao-de-backpressure/) — Compara estratégias de backpressure contra cada restrição de negócio e engenharia antes de recomendar, expondo o trade-off aceito.
- [migracao-lote-evento-1-diagnostico](./migracao-lote-evento-1-diagnostico/) — Primeiro elo da cadeia: diagnostica pontos frágeis, consumidores por sensibilidade, riscos e pré-condições de um pipeline em lote.
- [migracao-lote-evento-2-plano](./migracao-lote-evento-2-plano/) — Segundo elo da cadeia: transforma o diagnóstico em uma sequência de passos reversíveis, com critério de sucesso e gatilho de rollback por passo.
- [migracao-lote-evento-3-detalhamento](./migracao-lote-evento-3-detalhamento/) — Terceiro elo da cadeia: detalha um passo do plano em ações concretas, métricas de sucesso/rollback e informações a solicitar ao time.
- [correcao-de-networkpolicy](./correcao-de-networkpolicy/) — Recebe um manifesto de NetworkPolicy permissivo e produz a versão default-deny corrigida, com loop de verificação e refino conduzido.
