$ python3 skill/metacortex-manifests/scripts/conferir.py manifests/orion-prod
# Conferência — Padrão de Manifests da Metacortex (rev. 2026-07-29)

Entrada: manifests/orion-prod  
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
| 2.3 | obrigatório | replicas >= 2 em prod | **falha (1)** | script |
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

| Regra | Recurso | Detalhe | Fonte |
|---|---|---|---|
| 2.3 | `StatefulSet/orion-postgres` | replicas=1 em prod (exceção só com aprovação escrita de S&C no PR, com prazo) | script |

## Avisos — recomendado; exceção precisa de justificativa no PR

Nenhuma.

## Revisar lendo o projeto (instrução do SKILL.md)

- **2.2** `StatefulSet/orion-postgres:postgres` — readiness e liveness no MESMO destino — verificar se ele toca o banco. confirmar no código que os destinos existem; readiness e liveness NÃO podem ser o mesmo endpoint que checa banco. {"startupProbe": "exec pg_isready -h 127.0.0.1 -p 5432", "readinessProbe": "exec pg_isready -h 127.0.0.1 -p 5432", "livenessProbe": "exec pg_isready -h 127.0.0.1 -p 5432"}
- **3.3** `StatefulSet/orion-postgres` — confrontar as variáveis entregues ['PGDATA', 'POSTGRES_DB', 'POSTGRES_PASSWORD', 'POSTGRES_USER'] com as que o código lê, e decidir quais são sensíveis
- **3.2** `StatefulSet/orion-postgres` — com readOnlyRootFilesystem, confirmar no projeto onde a aplicação escreve e montar emptyDir
- **2.1** `StatefulSet/orion-postgres` — limits de memória devem ficar entre 1,5x e 2x o consumo observado em regime — conferir contra métrica real
- **2.6** `StatefulSet/orion-postgres` — terminationGracePeriodSeconds=60: a aplicação trata SIGTERM e drena nesse tempo?
- **3.4** `StatefulSet/orion-postgres` — confirmar no código que a aplicação não fala com o apiserver
- **2.2** `Deployment/orion-web:web` — confirmar no código que os destinos existem; readiness e liveness NÃO podem ser o mesmo endpoint que checa banco. {"startupProbe": "http /metrics:http", "readinessProbe": "http /:http", "livenessProbe": "http /metrics:http"}
- **3.3** `Deployment/orion-web` — confrontar as variáveis entregues ['DB_HOST', 'DB_NAME', 'DB_PASSWORD', 'DB_PORT', 'DB_USER', 'FLASK_APP', 'PROMETHEUS_MULTIPROC_DIR'] com as que o código lê, e decidir quais são sensíveis
- **3.2** `Deployment/orion-web` — com readOnlyRootFilesystem, confirmar no projeto onde a aplicação escreve e montar emptyDir
- **2.1** `Deployment/orion-web` — limits de memória devem ficar entre 1,5x e 2x o consumo observado em regime — conferir contra métrica real
- **2.6** `Deployment/orion-web` — terminationGracePeriodSeconds=30 (padrão): a aplicação trata SIGTERM e drena nesse tempo?
- **3.4** `Deployment/orion-web` — confirmar no código que a aplicação não fala com o apiserver

**Total:** 1 falha(s), 0 aviso(s), 12 ponto(s) a revisar lendo o projeto.

código de saída: 1
