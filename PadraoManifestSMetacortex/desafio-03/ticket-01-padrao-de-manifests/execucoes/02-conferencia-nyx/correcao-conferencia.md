$ python3 skill/metacortex-manifests/scripts/conferir.py correcao-proposta
# Conferência — Padrão de Manifests da Metacortex (rev. 2026-07-29)

Entrada: correcao-proposta  
Trivy: executado

## Resumo por regra

| Regra | Severidade | Descrição | Resultado | Fonte |
|---|---|---|---|---|
| 1.1 | obrigatório | Nome de recurso em kebab-case | ok | script |
| 1.2 | obrigatório | Namespace <cliente>-<dev|stg|prod> | ok | script |
| 1.3 | obrigatório | Quatro rótulos app.kubernetes.io/* em todo objeto | ok | script |
| 1.4 | obrigatório | Seletor idêntico aos rótulos do pod | ok | script |
| 1.5 | recomendado | Anotação metacortex.io/owner | ok | script |
| 1.6 | recomendado | Nome de container igual ao componente | ok | script |
| 2.1 | obrigatório | requests e limits de CPU e memória | revisar (ler projeto) | trivy |
| 2.2 | obrigatório | readinessProbe e livenessProbe em endpoints reais | revisar (ler projeto) | script |
| 2.3 | obrigatório | replicas >= 2 em prod | ok | script |
| 2.4 | obrigatório | RollingUpdate maxUnavailable 0 / maxSurge 1 em prod | ok | script |
| 2.5 | recomendado | PodDisruptionBudget em prod com mais de uma réplica | ok | script |
| 2.6 | recomendado | terminationGracePeriodSeconds compatível com a aplicação | revisar (ler projeto) | script |
| 3.1 | proibido | Tag :latest | ok | trivy + script |
| 3.2 | obrigatório | securityContext (non-root, UID 10001, sem escalonamento, FS read-only, drop ALL) | revisar (ler projeto) | trivy |
| 3.3 | proibido | Segredo em texto puro (env, ConfigMap, comentário) | revisar (ler projeto) | script |
| 3.4 | obrigatório | automountServiceAccountToken: false | revisar (ler projeto) | script |
| 3.5 | recomendado | ServiceAccount dedicada | ok | script |
| 3.6 | proibido | hostNetwork, hostPID, privileged | ok | trivy |
| 3.7 | obrigatório | Imagem só de registry.metacortex.io | ok | script |

## Falhas — barram a subida

Nenhuma.

## Avisos — recomendado; exceção precisa de justificativa no PR

Nenhuma.

## Revisar lendo o projeto (instrução do SKILL.md)

- **2.2** `Deployment/nyx-api:api` — confirmar no código que os destinos existem; readiness e liveness NÃO podem ser o mesmo endpoint que checa banco. {"readinessProbe": "http /ready:http", "livenessProbe": "http /health:http"}
- **3.3** `Deployment/nyx-api` — confrontar as variáveis entregues ['DB_DATABASE', 'DB_HOST', 'DB_PASSWORD', 'DB_PORT', 'DB_USERNAME'] com as que o código lê, e decidir quais são sensíveis
- **3.2** `Deployment/nyx-api` — com readOnlyRootFilesystem, confirmar no projeto onde a aplicação escreve e montar emptyDir
- **2.1** `Deployment/nyx-api` — limits de memória devem ficar entre 1,5x e 2x o consumo observado em regime — conferir contra métrica real
- **2.6** `Deployment/nyx-api` — terminationGracePeriodSeconds=30 (padrão): a aplicação trata SIGTERM e drena nesse tempo?
- **3.4** `Deployment/nyx-api` — confirmar no código que a aplicação não fala com o apiserver

**Total:** 0 falha(s), 0 aviso(s), 6 ponto(s) a revisar lendo o projeto.

código de saída: 0

$ kubeconform -summary -strict correcao-proposta
Summary: 4 resources found in 1 file - Valid: 4, Invalid: 0, Errors: 0, Skipped: 0
