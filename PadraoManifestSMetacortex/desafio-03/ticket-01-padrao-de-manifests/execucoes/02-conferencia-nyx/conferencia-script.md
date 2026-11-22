$ python3 skill/metacortex-manifests/scripts/conferir.py manifest-barrado
# Conferência — Padrão de Manifests da Metacortex (rev. 2026-07-29)

Entrada: manifest-barrado  
Trivy: executado

## Resumo por regra

| Regra | Severidade | Descrição | Resultado | Fonte |
|---|---|---|---|---|
| 1.1 | obrigatório | Nome de recurso em kebab-case | **falha (1)** | script |
| 1.2 | obrigatório | Namespace <cliente>-<dev|stg|prod> | ok | script |
| 1.3 | obrigatório | Quatro rótulos app.kubernetes.io/* em todo objeto | **falha (3)** | script |
| 1.4 | obrigatório | Seletor idêntico aos rótulos do pod | **falha (1)** | script |
| 1.5 | recomendado | Anotação metacortex.io/owner | **aviso (1)** | script |
| 1.6 | recomendado | Nome de container igual ao componente | ok | script |
| 2.1 | obrigatório | requests e limits de CPU e memória | **falha (4)** | trivy |
| 2.2 | obrigatório | readinessProbe e livenessProbe em endpoints reais | **falha (2)** | script |
| 2.3 | obrigatório | replicas >= 2 em prod | **falha (1)** | script |
| 2.4 | obrigatório | RollingUpdate maxUnavailable 0 / maxSurge 1 em prod | **falha (1)** | script |
| 2.5 | recomendado | PodDisruptionBudget em prod com mais de uma réplica | ok | script |
| 2.6 | recomendado | terminationGracePeriodSeconds compatível com a aplicação | revisar (ler projeto) | script |
| 3.1 | proibido | Tag :latest | **falha (1)** | trivy + script |
| 3.2 | obrigatório | securityContext (non-root, UID 10001, sem escalonamento, FS read-only, drop ALL) | **falha (9)** | trivy |
| 3.3 | proibido | Segredo em texto puro (env, ConfigMap, comentário) | **falha (1)** | script |
| 3.4 | obrigatório | automountServiceAccountToken: false | **falha (1)** | script |
| 3.5 | recomendado | ServiceAccount dedicada | **aviso (1)** | script |
| 3.6 | proibido | hostNetwork, hostPID, privileged | ok | trivy |
| 3.7 | obrigatório | Imagem só de registry.metacortex.io | ok | script |

## Falhas — barram a subida

| Regra | Recurso | Detalhe | Fonte |
|---|---|---|---|
| 1.1 | `Deployment/NyxAPI` | 'NyxAPI' não é kebab-case minúsculo (sem camelCase, underscore ou ponto) | script |
| 1.3 | `Deployment/NyxAPI` | rótulos ausentes: app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by (o rótulo curto 'app' não substitui os quatro) | script |
| 1.3 | `Deployment/NyxAPI` | rótulos ausentes (template do pod): app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by (o rótulo curto 'app' não substitui os quatro) | script |
| 1.3 | `Service/nyx-api` | rótulos ausentes: app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by | script |
| 1.4 | `Service/nyx-api` | selector {'app': 'nyx-api'} não casa com nenhum pod do conjunto — o Service fica sem endpoint | script |
| 2.1 | `nyx-api.yaml` | KSV-0011 (LOW): Container 'api' of Deployment 'NyxAPI' should set 'resources.limits.cpu' | trivy |
| 2.1 | `nyx-api.yaml` | KSV-0015 (LOW): Container 'api' of Deployment 'NyxAPI' should set 'resources.requests.cpu' | trivy |
| 2.1 | `nyx-api.yaml` | KSV-0016 (LOW): Container 'api' of Deployment 'NyxAPI' should set 'resources.requests.memory' | trivy |
| 2.1 | `nyx-api.yaml` | KSV-0018 (LOW): Container 'api' of Deployment 'NyxAPI' should set 'resources.limits.memory' | trivy |
| 2.2 | `Deployment/NyxAPI:api` | sem readinessProbe | script |
| 2.2 | `Deployment/NyxAPI:api` | sem livenessProbe | script |
| 2.3 | `Deployment/NyxAPI` | replicas=1 em prod (exceção só com aprovação escrita de S&C no PR, com prazo) | script |
| 2.4 | `Deployment/NyxAPI` | strategy (padrão do Kubernetes: 25%/25%) — prod exige RollingUpdate maxUnavailable: 0, maxSurge: 1 | script |
| 3.1 | `nyx-api.yaml` | KSV-0013 (MEDIUM): Container 'api' of Deployment 'NyxAPI' should specify an image tag | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0001 (MEDIUM): Container 'api' of Deployment 'NyxAPI' should set 'securityContext.allowPrivilegeEscalation' to false | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0003 (LOW): Container 'api' of Deployment 'NyxAPI' should add 'ALL' to 'securityContext.capabilities.drop' | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0004 (LOW): Container 'api' of 'deployment' 'NyxAPI' in 'nyx-prod' namespace should set securityContext.capabilities.drop | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0012 (MEDIUM): Container 'api' of Deployment 'NyxAPI' should set 'securityContext.runAsNonRoot' to true | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0014 (HIGH): Container 'api' of Deployment 'NyxAPI' should set 'securityContext.readOnlyRootFilesystem' to true | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0020 (LOW): Container 'api' of Deployment 'NyxAPI' should set 'securityContext.runAsUser' > 10000 | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0106 (LOW): container should drop all | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0118 (HIGH): container NyxAPI in nyx-prod namespace is using the default security context | trivy |
| 3.2 | `nyx-api.yaml` | KSV-0118 (HIGH): deployment NyxAPI in nyx-prod namespace is using the default security context, which allows root privileges | trivy |
| 3.3 | `nyx-api.yaml:25` | URL com usuário:senha em texto (valor) | script |
| 3.4 | `Deployment/NyxAPI` | automountServiceAccountToken não é false (no pod nem na ServiceAccount do conjunto) | script |

## Avisos — recomendado; exceção precisa de justificativa no PR

| Regra | Recurso | Detalhe | Fonte |
|---|---|---|---|
| 1.5 | `Deployment/NyxAPI` | sem metacortex.io/owner (justificar no PR) | script |
| 3.5 | `Deployment/NyxAPI` | usa a ServiceAccount default do namespace | script |

## Revisar lendo o projeto (instrução do SKILL.md)

- **2.2** `Deployment/NyxAPI:api` — confirmar no código que os destinos existem; readiness e liveness NÃO podem ser o mesmo endpoint que checa banco. Nenhuma probe declarada — descobrir endpoints no projeto.
- **3.3** `Deployment/NyxAPI` — confrontar as variáveis entregues ['DATABASE_URL'] com as que o código lê, e decidir quais são sensíveis
- **3.2** `Deployment/NyxAPI` — com readOnlyRootFilesystem, confirmar no projeto onde a aplicação escreve e montar emptyDir
- **2.1** `Deployment/NyxAPI` — limits de memória devem ficar entre 1,5x e 2x o consumo observado em regime — conferir contra métrica real
- **2.6** `Deployment/NyxAPI` — terminationGracePeriodSeconds=30 (padrão): a aplicação trata SIGTERM e drena nesse tempo?
- **3.4** `Deployment/NyxAPI` — confirmar no código que a aplicação não fala com o apiserver

## Informativo — catálogo do Trivy fora do padrão (não barra)

- KSV-0021 (LOW) Runs with GID <= 10000 — Container 'api' of Deployment 'NyxAPI' should set 'securityContext.runAsGroup' > 10000
- KSV-0030 (LOW) Runtime/Default Seccomp profile not set — Either Pod or Container should set 'securityContext.seccompProfile.type' to 'RuntimeDefault'
- KSV-0104 (MEDIUM) Seccomp policies disabled — container "api" of deployment "NyxAPI" in "nyx-prod" namespace should specify a seccomp profile

**Total:** 25 falha(s), 2 aviso(s), 6 ponto(s) a revisar lendo o projeto.

código de saída: 1
