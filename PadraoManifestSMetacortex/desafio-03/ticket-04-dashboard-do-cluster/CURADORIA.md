# Curadoria do Ticket 04: dashboard do cluster

Este documento cobre o que o enunciado pede além do código: onde os documentos
precisaram ser corrigidos, o que o agente entendeu diferente do que foi
escrito, e a justificativa estendida de cada decisão aberta. A versão curta de
cada decisão está em `openspec/changes/archive/2026-11-08-add-cluster-dashboard/design.md`; aqui
cada uma é comparada com pelo menos duas alternativas descartadas, dizendo o que
se ganha e o que se perde.

O registro do comportamento das duas skills está em
[`REGISTRO-SKILLS.md`](REGISTRO-SKILLS.md).

## 1. Onde o documento precisou ser corrigido

**1.1 A proposta afirmava algo falso sobre o cluster.** A primeira versão de
`proposal.md` dizia que `nyx-prod`, `nyx-stg` e `orion-stg` não existiam no
cluster e previa provisioná-los. Os três já existiam, nos estados de
laboratório. A correção está registrada na própria proposta, e a tarefa de
provisionar foi removida: seria uma escrita no cluster sem necessidade, num
projeto cujo invariante é só ler.

**1.2 Critério de aceite amarrado a estado vivo.** A spec e a proposta citam
`155` reinícios e `count: 429` nos eventos, valores lidos do cluster em
2026-09-27. Na validação, algumas horas depois, a tela mostrou `163` e `164`
reinícios e `count` de `467` e `466`. Nenhum dos dois estava errado: o pod
continua caindo e os números sobem. A lição virou a decisão D7 (fixtures
capturadas em `tests/fixtures/`, com o cluster vivo como validação final e não
como único teste). Os testes de tradução verificam `155` e `429` contra a
fixture congelada, e o registro de validação registra os valores vivos.

**1.3 Tarefa que dependia de duas coisas diferentes.** A tarefa 8.2 juntava
"a busca não dispara nova coleta" (verificável por teste automatizado) com "a
tela mostra menos linhas" (só verificável no navegador). O registro de validação
separou as duas: a primeira ficou coberta por teste, a segunda dependeu da
confirmação visual feita depois.

**1.4 Cinco lacunas da spec, fechadas antes da implementação.** Revisada a spec gerada pelo
`/opsx:propose` (15 requisitos), a revisão apontou cinco lacunas, e os ajustes entraram por
`/opsx:update` antes de qualquer código:

1. `spec.replicas` ausente não estava entre os campos omitidos. Sem isso, um Deployment sem `replicas`
   explícito viraria `0/None` na tela. Passou a valer 1, o default da API.
2. Faltava o comportamento quando a listagem de namespaces é negada, o caso mais provável de credencial
   restrita. Passou a existir o seletor degradado (`sem permissão para listar namespaces`, com campo
   de digitação). Foi exatamente o que o cenário 8.9 validou.
3. Escape de HTML e escuta só em `127.0.0.1` existiam apenas no design e nas tarefas. Foram promovidos a
   requisitos verificáveis da spec (hoje são 16).
4. Kubeconfig inexistente, ilegível ou malformado não tinha cenário, e é diferente de "sem contexto
   corrente". A proposta passou de cinco para **seis** cenários adversos.
5. Dois requisitos citavam `watch` de formas que pareciam se contradizer: o código não abre watch, mas
   o ClusterRole de exemplo inclui o verbo. A spec e o YAML passaram a explicar que o `watch` entra por
   ser parte do conjunto canônico de leitura, e que o teste de só leitura o barra no código.

**1.5 Origem da change anterior e idioma.** Ao abrir o projeto havia uma change `add-cluster-dashboard`
em inglês que ninguém lembrava de ter criado. A investigação do agente a atribuiu a uma sessão anterior
do Claude Code na mesma pasta, às 15:39 de 2026-09-27, com o mesmo pedido. Essa sessão afirmou que os
namespaces não existiam, sem consultar o cluster (ver 1.1). A decisão foi reescrevê-la em **português**,
como os outros três tickets, verificando o cluster em modo leitura.

**1.6 Correções de fechamento (2026-11-08).** Ao arquivar o change, o CLI do OpenSpec recusou a
estrutura recebida, porque arquivos com ponto no nome tinham sido renomeados no empacotamento:
`specs/` aparecia como `spec/`, `.openspec.yaml` como `openspec.yaml`, e o `.gitignore` e os `.gitkeep`
como `download`. Os nomes foram restaurados e o change foi arquivado como
`2026-11-08-add-cluster-dashboard`, com 16 requisitos sincronizados em
`openspec/specs/cluster-dashboard/spec.md`. A validação normal passa. A `--strict` acusa 7 avisos de
requisitos com mais de 500 caracteres no CLI 1.16.1, que não foram reescritos.

## 2. O que o agente entendeu diferente do que foi escrito

Fonte: o histórico da revisão e dos prompts na conversa de 2026-09-27 e os artefatos do projeto. As
sessões do Claude Code não estão no repositório, e o autor pode acrescentar casos.

| Eu escrevi | O agente entendeu ou fez | O que mudou |
|---|---|---|
| O pedido de proposta, sem dizer quais namespaces existiam | A sessão antiga **afirmou** que `nyx-prod`, `nyx-stg` e `orion-stg` não existiam e previu provisioná-los, sem consultar o cluster | A tarefa de provisionar foi removida (seria escrita sem necessidade) e a proposta foi corrigida. Ver 1.1 e 1.5 |
| Barrar `watch.Watch` no teste de só leitura | O agente **fechou também** a brecha do argumento `watch=True` num `list_*`, que abre watch sem passar por `watch.Watch` | O teste passou a barrar as duas formas. Foi além do pedido, no sentido certo |
| "Permitir informar o namespace manualmente" quando a listagem é negada | O agente tratou o texto digitado como **entrada não confiável**: validação DNS-1123 antes de qualquer chamada, mais o escape ao reapresentá-lo | Passou a ser requisito e risco nomeado no design |
| Cinco cenários adversos obrigatórios | Com o kubeconfig inválido, o agente reescreveu a proposta para **seis** | A proposta e a spec ficaram coerentes com o sexto cenário |
| Quatro decisões de design (D1 a D4) | O agente acrescentou **três decisões que não estavam no prompt**: D5 (só leitura em três camadas), D6 (erros por bloco, com o 403 `system:anonymous` tratado como credencial) e D7 (tradução num módulo puro, com fixtures reais) | Foram aceitas na revisão e viraram os ADR-0005, 0006 e 0007 |
| "Gere manifests no padrão da casa" | A `metacortex-manifests` incluiu **NetworkPolicies**, que o padrão não exige e que o Ticket 01 tinha deixado de fora | Registrado em `REGISTRO-SKILLS.md`. Não foi tratado como erro |
| Comandos de rotina para o laboratório | O agente respondeu em **sintaxe de bash** (continuação de linha com `\`, e o `deploy/lab/README.md` assume Git Bash), e o autor usa PowerShell | Cada bloco foi traduzido à mão, e os `kubectl create secret` viraram uma linha só |

## 3. Decisões abertas, com alternativas

### 3.1 Linguagem e stack

**Escolhido: Python 3 com HTML gerado no servidor e `http.server` da biblioteca padrão.**

| Opção | O que se ganha | O que se perde |
|---|---|---|
| **Python + HTML local** (escolhida) | Cliente oficial com autenticação de kubeconfig completa. É a linguagem que o time já usa nos outros tickets. Tabelas largas cabem no navegador, e a página pode ser capturada e anexada ao chamado. Sem build de frontend. | Distribuição: exige Python 3.12+ e um venv, sem binário único. Empacotamento ficou adiado. |
| Go | Binário único, fácil de distribuir. `client-go` é equivalente em capacidade. | Uma segunda linguagem e toolchain para o time manter, numa ferramenta de uma pessoa, sem ganho de comportamento. |
| TUI no terminal | Abre mais rápido e dispensa navegador. | Quatro tabelas largas e filtráveis mais eventos cabem mal numa largura fixa, e uma tela de terminal vira anexo de chamado com mais dificuldade. |

### 3.2 Como falar com a API do Kubernetes

**Escolhido: cliente oficial `kubernetes` para Python, isolado num único módulo (`acesso.py`).**

| Opção | O que se ganha | O que se perde |
|---|---|---|
| **Cliente oficial** (escolhida) | Autenticação idêntica à do `kubectl`: certificado de cliente, token, CA, OIDC e plugins `exec`. Tipagem e paginação prontas. | Uma dependência pesada, atrelada à compatibilidade com a versão do Python (tratada fixando a versão e validando na tarefa 1.1). |
| `kubectl` como subprocesso | Nenhuma biblioteca de cliente para manter. | Exige o binário instalado, trata a saída como contrato não oficial, cria um processo por chamada e dificulta agregar EndpointSlices. E é o pior caso para o invariante: um subprocesso aceita qualquer verbo, inclusive escrita, e escapa da camada única. Por isso o teste barra `kubectl` como subprocesso. |
| HTTP direto no apiserver | Menor dependência possível. | Obriga a reimplementar a autenticação de kubeconfig (certificados, plugins `exec`, validação de CA), que é exatamente o código sensível e fácil de errar. |

### 3.3 Como manter a tela atualizada

**Escolhido: coleta sob demanda, com carimbo de hora.**

| Opção | O que se ganha | O que se perde |
|---|---|---|
| **Sob demanda** (escolhida) | Um retrato estável para ler durante o chamado. Cada coleta é um conjunto finito de `list`, pedido explicitamente e auditável pelo carimbo. Carga mínima no apiserver. | A tela pode ficar aberta e desatualizada. Mitigado com o carimbo sempre visível e sem temporizador escondido. Exige um clique em **Atualizar**. |
| Polling em intervalo fixo | A tela se atualiza sozinha. | Carga contínua no apiserver sem benefício numa sessão curta de triagem, e a tela se rearranja enquanto se lê. Ainda precisaria de carimbo para responder "isto é atual?". |
| Watch | Menor atraso entre o cluster e a tela. | Uma conexão longa pode ficar obsoleta em silêncio justamente quando cluster ou rede estão ruins, que é a situação diagnosticada. Exige estado reconciliado em memória. Barrado por teste (`watch.Watch` e `watch=True`), para a decisão não regredir. |

### 3.4 Escopo da primeira fatia

**Escolhido: namespaces, pods, deployments, services com endpoint, eventos do namespace, filtro, busca e os seis cenários adversos. Fora: logs, métricas, histórico, multicluster e qualquer escrita.**

*Esta comparação foi redigida a partir de `proposal.md` e `design.md`; revise se o seu raciocínio na época era outro.*

| Opção | O que se ganha | O que se perde |
|---|---|---|
| **Fatia escolhida** | Cobre o quadro dos "primeiros dez minutos" e os três chamados do laboratório (container, imagem, Service sem endpoint). Superfície pequena, verificável e sem escrita. | Sem logs nem métricas: para a causa de um `CrashLoopBackOff` ainda é preciso o terminal (o `--previous` do `kubectl logs`). |
| Só pods | Mais rápido de entregar. | O Chamado 3 (Service sem endpoint) ficaria invisível, e é o caso que o enunciado destaca. |
| Incluir logs e métricas | Mais perto de substituir o terminal. | Aumenta a permissão exigida (logs e métricas são outros recursos), estica o RBAC mínimo e a superfície a testar. O enunciado diz que o objetivo é encurtar os dez minutos, não substituir o terminal. |
| Troca de contexto na tela (multicluster) | Conveniência de olhar vários clusters. | Fora do escopo do ticket e amplia o risco de olhar (ou, no futuro, agir) no cluster errado. Quem quer outro cluster troca o contexto por fora. |

### 3.5 Endpoints ou EndpointSlice

**Escolhido: EndpointSlice, agregado por `kubernetes.io/service-name`.**

| Opção | O que se ganha | O que se perde |
|---|---|---|
| **EndpointSlice agregado** (escolhida) | API durável (o laboratório roda 1.37; `Endpoints` está depreciado desde a 1.33). Distingue três estados: `sem endpoint`, `N endereços, M prontos` e `ExternalName`. Pegou o caso real `nyx-prod/nyx-api` (2 endereços, 0 prontos). | Mais código: um Service pode ter vários slices, então é preciso agrupar e contar endereços únicos. |
| `Endpoints` | Um objeto por Service, mais simples. | Base com prazo de validade. E `Endpoints` sem endereço nem traz `subsets`: a mesma armadilha de campo ausente. |
| Inferir pelo `selector` do Service | Não precisa ler outro objeto. | Reimplementa o controlador de endpoints (readiness, terminating, portas nomeadas, Services sem selector) e pode divergir do que o plano de controle publica. |

### 3.6 Decisões complementares

| Decisão | Escolhida | Descartadas | Ganha / perde da escolhida |
|---|---|---|---|
| **D5** garantia de só leitura | Três camadas: acesso único, teste estático por `ast`, RBAC de exemplo | Só RBAC; só revisão de código | Ganha uma regressão que quebra o build, e vale para qualquer credencial. Perde simplicidade: são três artefatos para manter, e a camada 3 só protege se o painel rodar com a credencial certa. |
| **D6** erros | Classificação por bloco, com mensagem por categoria | Deixar a exceção subir; uma tela de erro global | Ganha "o resto da tela funciona" quando só um recurso é negado. Perde a simplicidade de um único tratamento de erro. |
| **D7** tradução | Módulo puro, testado com fixtures reais do laboratório | Tratar ausência no template; testar só contra o cluster vivo | Ganha testes determinísticos das três armadilhas de dado. Perde a fidelidade automática ao estado vivo, compensada pelas tarefas do grupo 8. |

## 4. Números do projeto

- 158 testes passando em 8 arquivos (`pytest`, saída completa em
  `validacao/pytest-2026-09-27.txt`).
- 34 de 34 tarefas do OpenSpec concluídas, 16 requisitos na spec. Change arquivado em
  2026-11-08 (`openspec/changes/archive/2026-11-08-add-cluster-dashboard/`).
- Escuta só em `127.0.0.1` (evidência: `netstat` no registro, item 8.10).
- Nenhuma escrita no cluster: o painel só lista, e as fixtures foram capturadas
  só com `kubectl get`.
