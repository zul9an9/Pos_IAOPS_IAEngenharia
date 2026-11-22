# Fluxo de origem — o que foi rodado antes da skill existir (e depois, quando o padrão chegou)

A skill não nasceu de rascunho. Nasceu desta sequência, executada numa sessão do Claude
(claude.ai com execução de código num container Linux x86_64) em 19/09/2026.

## Fase 1 — fluxo manual, antes de qualquer skill

| # | Passo | Evidência | O que ensinou |
|---|---|---|---|
| 1 | Clonar kube-news, fake-shop e encontros-tech e ler o código | commits `aab9356` (kube-news), `a3fa74f` (fake-shop) | Porta, probes, variáveis e migração só existem no código. O kube-news não lê `DATABASE_URL`. |
| 2 | Instalar o Trivy 0.74.0 e rodar `trivy config` no manifesto barrado | `01-trivy-config-nyx.txt` / `.json` | 18 achados, todos de securityContext, requests/limits, seccomp e `:latest`. Nenhum de nome, rótulo, selector, réplica, probe ou credencial. |
| 3 | `trivy fs --scanners secret` no mesmo manifesto | `02-trivy-secret-nyx.txt` | A senha em `DATABASE_URL` passa limpa. Segredo em manifesto precisa de regra própria. |
| 4 | Sondar o catálogo com manifests construídos para isso | `sondagem/`, `03-sondagem-trivy.txt` | Mapa dos IDs KSV. O Trivy cobre initContainers e acesso ao host, mas não cobra `automountServiceAccountToken` nem probes. |
| 5 | kubeconform no manifesto barrado | `04-kubeconform-nyx.txt` | O schema aceita `NyxAPI`. Só o API server ou uma regra própria rejeitam o nome. |

## Fase 2 — primeira versão contra um padrão assumido

O anexo oficial ainda não estava disponível. A v1 da skill foi construída contra uma
reconstrução do padrão e executada nos dois modos. O método (divisão script/instrução, o Trivy
primeiro, os dois modos, o Bloco 4 fora) sobreviveu. As regras, não: ver `../curadoria.md` §7.

## Fase 3 — chegada do padrão oficial (rev. 2026-07-29)

| # | Passo | Resultado |
|---|---|---|
| 6 | Comparar regra por regra o padrão oficial com o assumido | 12 regras ou mecanismos inventados removidos, 2 invertidas (limite de CPU, UID 10001), 5 novas, severidades e regime de exceção incorporados |
| 7 | Reaproveitar a sondagem da fase 1 para refazer o mapa KSV→regra | KSV-0011 passa de suprimido a 2.1; KSV-0020 passa de informativo a 3.2; seccomp, hostIPC e hostPath passam a informativos |
| 8 | Reescrever o `conferir.py` com a numeração oficial e testar os caminhos novos | `05-testes-do-script.txt`: 3.3 em ConfigMap e comentário, 1.3 `managed-by`, degradação sem Trivy, erro de leitura |
| 9 | Rodar a skill de novo nos dois modos | `../execucoes/` |

Observação de ambiente: o download do bundle atualizado de checks do Trivy foi bloqueado pela
rede do container (`mirror.gcr.io`), e o Trivy usou os checks embutidos da 0.74.0. Revise o mapa
KSV quando o Trivy do pipeline de S&C for atualizado.
