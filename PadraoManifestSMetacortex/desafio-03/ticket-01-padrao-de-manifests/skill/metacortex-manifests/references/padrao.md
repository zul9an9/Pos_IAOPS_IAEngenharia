# Padrão de Manifests da Metacortex (rev. 2026-07-29): regras, severidade e forma de conferência

Destilado dos Blocos 1 a 3 e da seção "Exceções" do wiki de Plataforma. O Bloco 4 (vocabulário)
ficou de fora de propósito (ver `curadoria.md` da entrega).

Na coluna **Como**:
- **trivy**: catálogo do Trivy, traduzido pelo `conferir.py`;
- **script**: verificação própria do `conferir.py`;
- **instrução**: resolvida lendo o projeto.

| Regra | Sev. | Texto essencial | Como | O que o mecânico não alcança |
|---|---|---|---|---|
| 1.1 | obr. | Nome minúsculo, palavras separadas por hífen; sem camelCase, underscore ou ponto | script | — |
| 1.2 | obr. | Namespace `<cliente>-<dev\|stg\|prod>`. O Construct só cria nesse formato | script | — |
| 1.3 | obr. | Todo objeto (Deployment, Service, ConfigMap, Secret, Job, CronJob) com `app.kubernetes.io/name` (componente), `instance` (instalação, ex.: `nyx-prod`), `part-of` (produto do cliente), `managed-by` (`platform`\|`argocd`\|`helm`). O `app:` curto pode coexistir, mas não substitui | script | se `part-of` é mesmo o produto |
| 1.4 | obr. | O selector do Service e o `matchLabels` são idênticos aos rótulos do template, caractere por caractere | script | — |
| 1.5 | rec. | `metacortex.io/owner` (time) e `metacortex.io/runbook` (URL, quando existir) | script (owner) | se existe runbook |
| 1.6 | rec. | Container com o nome do componente (`api`, `worker`), nunca `app`, `main`, `container` | script | — |
| 2.1 | obr. | requests **e limits** de CPU e memória em todo container. Limite de memória entre 1,5x e 2x o consumo observado | trivy (KSV-0011/15/16/18) + instrução | o valor certo exige métrica real |
| 2.2 | obr. | readiness e liveness em qualquer ambiente, em endpoints que a app expõe. Nunca as duas no mesmo endpoint que checa banco | script (presença; mesmo destino) + instrução | se o endpoint existe e o que ele checa |
| 2.3 | obr. | `replicas >= 2` em prod; em dev e stg, 1 é aceitável | script | se uma exceção é legítima |
| 2.4 | obr. em prod | `RollingUpdate`, `maxUnavailable: 0`, `maxSurge: 1` | script (Deployment) | — |
| 2.5 | rec. | PDB com `minAvailable >= 1` em prod com mais de uma réplica | script | — |
| 2.6 | rec. | `terminationGracePeriodSeconds` compatível; a app trata SIGTERM | instrução | tudo: depende do código e do PID 1 |
| 3.1 | **proib.** | `:latest`. Usar tag imutável ou digest | trivy (KSV-0013) + script (tag que não parece versão vira "revisar") | se a tag é de fato imutável no registry |
| 3.2 | obr. | `runAsNonRoot`, `runAsUser: 10001`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `drop: ["ALL"]`; emptyDir onde a app escreve | trivy (KSV-0001/03/04/12/14/20/106/118) | onde a app escreve |
| 3.3 | **proib.** | Nenhum valor sensível em `env.value`, ConfigMap ou comentário; sempre `secretKeyRef`. Secret não se versiona no Git | script (URL com credencial no texto cru; nome sensível com valor literal; ConfigMap; Secret com dados) | quais variáveis a app lê e quais são sensíveis |
| 3.4 | obr. | `automountServiceAccountToken: false` quando a app não fala com a API (obrigatório desde 2026-07-29) | script (pod ou ServiceAccount) + instrução | se a app fala com a API |
| 3.5 | rec. | ServiceAccount dedicada, com RBAC mínimo ou nenhum | script | — |
| 3.6 | **proib.** | `hostNetwork`, `hostPID`, `privileged` | trivy (KSV-0009/10/17) | — |
| 3.7 | obr. | Imagem só de `registry.metacortex.io`; imagem pública entra pelo Loom | script | se a imagem existe no registry (é triagem) |

**Exceções.** Regra obrigatória: aprovação escrita de S&C no PR, com prazo. Regra recomendada:
justificativa no PR. Regra proibida: sem exceção para workload de cliente.

## Mapa Trivy → padrão

Levantado rodando o Trivy 0.74.0 (checks embutidos) no manifesto barrado e em manifests de
sondagem.

| IDs KSV | Regra |
|---|---|
| 0013 | 3.1 |
| 0001, 0003, 0004, 0012, 0014, 0020, 0106, 0118 | 3.2 |
| 0009, 0010, 0017 | 3.6 |
| 0011, 0015, 0016, 0018 | 2.1 |

**Suprimido** (`scripts/trivyignore`): KSV-0125. É falso positivo de registry "não confiável"
para `registry.metacortex.io`; a 3.7 é conferida pelo script.

**Informativo** (fora do padrão, não barra):
- KSV-0008 (hostIPC), KSV-0023 e KSV-0121 (hostPath): o padrão só proíbe hostNetwork, hostPID e
  privileged;
- KSV-0021 (GID > 10000);
- KSV-0030 e KSV-0104 (seccomp).

O KSV-0020 cobra UID > 10000; o padrão mostra `runAsUser: 10001`.

**O que o Trivy comprovadamente não acusa**, e por isso é escopo do script:
- nome fora de kebab-case;
- rótulos;
- selector sem pods;
- ausência de probes;
- réplicas e strategy;
- PDB;
- senha em `env.value` (nem com `trivy fs --scanners secret`);
- `automountServiceAccountToken`;
- ServiceAccount default;
- nome de container.
