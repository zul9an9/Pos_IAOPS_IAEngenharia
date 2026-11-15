# PRD — painel_cluster: painel local e somente leitura do cluster

| | |
|---|---|
| **Produto** | `painel_cluster`, painel local do Ticket 04 (cenário Metacortex) |
| **Fatia** | 1 (um cluster, o do contexto corrente do kubeconfig) |
| **Estado** | Implementado e validado contra o cluster kind do laboratório em 2026-09-27. Change `add-cluster-dashboard` arquivado em 2026-11-08 |
| **Fontes** | `openspec/changes/archive/2026-11-08-add-cluster-dashboard/` (`proposal.md`, `design.md`, `tasks.md`), `openspec/specs/cluster-dashboard/spec.md`, `README.md`, `CURADORIA.md` e `validacao/` |
| **Consolidado em** | 2026-11-08, a partir das fontes acima. Nenhuma decisão nova foi introduzida neste documento |
| **Documentos irmãos** | [`03-TRD.md`](03-TRD.md) (como é construído) e [`adr/`](adr/README.md) (por que cada decisão foi tomada) |

## 1. Resumo

Os primeiros dez minutos de um chamado de Kubernetes vão embora rodando sempre os mesmos
`kubectl get` e `describe`, namespace por namespace, só para montar o quadro do que está quebrado.
O `painel_cluster` é uma aplicação **local** que lê o **contexto corrente** do kubeconfig e mostra
esse quadro numa única página: namespaces, pods, deployments, services e os eventos recentes do
namespace selecionado.

Ele é **somente leitura**, e essa garantia é verificável por máquina, não só prometida. A coleta é
**sob demanda**, com carimbo de hora, e o painel afirma só o que a API afirma: não sintetiza juízo
de saúde.

## 2. Problema

O reconhecimento inicial de um chamado é manual e repetitivo, e o quadro que ele produz depende de
quem digita os comandos. Soma-se a isso que a API do Kubernetes **omite campos** em vez de mandá-los
vazios, e uma tela ingênua erra exatamente nesses casos (por exemplo, mostra um Service como "tem
endpoint" quando nenhum endereço está pronto).

Restrições do contexto, fixadas pelo ticket e não negociáveis:

- O painel **só lê**. Nenhum caminho de escrita no cluster do cliente.
- Roda na máquina de quem opera e usa as credenciais que essa pessoa já tem.
- O objetivo é **encurtar** os dez minutos iniciais, não substituir o terminal.

## 3. Objetivos e não objetivos

### 3.1 Objetivos

1. Mostrar, numa página, o estado de namespaces, pods, deployments, services e eventos do contexto
   corrente, com carimbo de hora.
2. Tratar corretamente as três armadilhas de dados da API: campo ausente, evento como objeto
   próprio e "pronto" não é "saudável".
3. Garantir a **somente leitura** em camadas independentes e verificáveis.
4. Degradar por bloco: a falta de permissão para um tipo de recurso não esconde o resto da tela.
5. Dar mensagem própria, sem stack trace, para cada cenário adverso do ticket.

### 3.2 Não objetivos da fatia 1

| Fora de escopo | Motivo |
|---|---|
| Logs e métricas de consumo | Aumentam a permissão exigida (são outros recursos) e estendem o RBAC mínimo. O objetivo é encurtar os dez minutos, não substituir o terminal |
| Histórico e persistência | Cada coleta vive só na memória do processo. Nada é gravado em disco |
| Troca de contexto e multicluster | Amplia o risco de olhar (ou, no futuro, agir) no cluster errado. Quem quer outro cluster troca o contexto por fora |
| Qualquer escrita no cluster | Invariante do projeto |
| Autenticação do próprio painel | Ele escuta só em `127.0.0.1`, e quem tem shell na máquina já tem o kubeconfig. O painel não cria uma fronteira nova |
| Empacotamento e distribuição (pip, script único, imagem) | Adiado |
| Atualização automática (polling) e watch | Ver [ADR-0003](adr/ADR-0003-atualizacao-sob-demanda.md) |

## 4. Quem usa e como

| Quem | Como usa | O que precisa |
|---|---|---|
| **Quem opera durante um chamado** | Abre a página, vê o retrato, filtra por namespace e busca por nome | Um quadro estável para ler, com a hora da coleta sempre visível, e que diga o que a API afirma sem inventar diagnóstico |
| **Quem tem credencial restrita** (por tipo de recurso ou por namespace) | Roda o painel com uma ServiceAccount de menos privilégio | Que o painel continue útil: o bloco negado avisa, e o resto funciona |
| **Quem revisa segurança e aplica o RBAC** | Lê o ClusterRole de exemplo e decide se aplica | Poucos verbos, sem curingas, e a garantia de que o painel não usa o que não precisa |
| **Quem mantém a ferramenta** | Altera ou estende o painel | Testes que quebrem o build se alguém introduzir uma escrita |

## 5. Escopo da fatia 1

**O painel mostra:**

- **namespaces**;
- **pods**: fase, contêineres prontos, reinícios (incluindo init containers) e o motivo quando em
  falha;
- **deployments**: prontas/desejadas;
- **services**: tipo, IP, portas e o resumo de endpoint lido dos EndpointSlices;
- **eventos recentes** do namespace selecionado: um objeto Event por linha, com razão, mensagem,
  objeto envolvido, contagem e carimbos.

**Gatilhos de coleta:** abrir a página, clicar em **Atualizar** e trocar o namespace. A busca por
nome **não** é gatilho: ela filtra a coleta já exibida, no navegador.

**Fonte de credencial:** o kubeconfig indicado por `KUBECONFIG` ou, na falta dele, `~/.kube/config`,
**somente o contexto corrente**.

## 6. Requisitos funcionais

A coluna "Spec" aponta o requisito normativo em `openspec/specs/cluster-dashboard/spec.md`.

| ID | Requisito | Spec |
|---|---|---|
| RF-01 | Usar exclusivamente o `current-context` do kubeconfig, mostrando no cabeçalho de toda tela o nome do contexto e o endereço do servidor. Sem seleção ou troca de contexto | *Acesso somente ao contexto corrente* |
| RF-02 | Listar namespaces. Se a listagem for negada (403), o seletor diz `sem permissão para listar namespaces` e aceita o nome digitado, já preenchido com o `namespace` do contexto quando houver. O filtro nunca fica inutilizável | *Lista de namespaces* |
| RF-03 | Mostrar o estado real dos pods a partir dos contêineres, e não só da fase: prontos, reinícios (incluindo init containers) e motivo | *Estado dos pods* |
| RF-04 | Mostrar deployments como prontas/desejadas | *Prontidão dos deployments* |
| RF-05 | Resumir o endpoint de cada Service pelos EndpointSlices, com três saídas: `sem endpoint`, `N endereços, M prontos` e `ExternalName` | *Endpoint dos services via EndpointSlice* |
| RF-06 | Mostrar os eventos do namespace selecionado, um objeto por linha, com `count` e carimbos | *Eventos recentes do namespace selecionado* |
| RF-07 | Filtrar por namespace (gatilho de nova coleta) e buscar por nome (só no navegador, sem nova coleta) | *Filtro por namespace e busca por nome* |
| RF-08 | Coletar sob demanda e exibir o carimbo de hora da coleta em toda tela. Sem polling nem watch | *Coleta sob demanda com carimbo de hora* |
| RF-09 | Exibir campo ausente como valor semântico, nunca tela em branco, `None` ou erro | *Campo ausente exibido como valor semântico* |
| RF-10 | Afirmar só o que a API afirma, sem juízo de saúde | *Apenas o que a API afirma, sem juízo de saúde* |
| RF-11 | Acessar o cluster somente por operações de listagem, numa camada única, com teste que barra escrita | *Acesso ao cluster somente leitura* |
| RF-12 | Fornecer um ClusterRole de exemplo com `get`, `list` e `watch`, sem curingas, só nos recursos que o painel lê | *ClusterRole de exemplo com privilégio mínimo* |
| RF-13 | Escutar somente em `127.0.0.1`, aceitando só GET | *Servidor local somente em 127.0.0.1* |
| RF-14 | Escapar todo texto vindo da API e do kubeconfig antes de ir para o HTML | *Escape de todo texto vindo da API* |
| RF-15 | Mostrar um aviso permanente de somente leitura em toda tela | *Aviso de só leitura na tela* |
| RF-16 | Tratar seis cenários adversos, cada um com mensagem própria e sem stack trace | *Cenários adversos sem stack trace* |

### 6.1 As três armadilhas de dados (RF-09, RF-06 e RF-10)

| Armadilha | O que a API faz | O que o painel mostra |
|---|---|---|
| **(a) Campo ausente não é campo vazio** | Deployment sem `readyReplicas`; Deployment sem `spec.replicas`; EndpointSlice com `endpoints: null`; Pod sem `containerStatuses` | `0/N` (e `N` vale 1 se `spec.replicas` faltar, o default da API, nunca `0/None`); `sem endpoint`; 0 reinícios |
| **(b) Evento é objeto próprio** | Um Event com `count: 21` é um objeto, não 21 | Uma linha, com a contagem 21 |
| **(c) "Pronto" não é "saudável"** | A fase de um pod pode ser `Running` com o contêiner em `CrashLoopBackOff`; um Service pode ter endereços, todos com `ready: false` | O que a API reporta (fase, razões, condição `ready`), sem rótulo de "saudável" |

### 6.2 Os seis cenários adversos (RF-16)

| Cenário | Alcance da mensagem |
|---|---|
| Cluster não responde | Tela inteira (cita servidor e horário) |
| Credencial inválida ou expirada (mensagem distinta de "não respondeu") | Tela inteira |
| Permissão negada para **um** tipo de recurso | Só aquele bloco mostra `sem permissão`; o resto funciona |
| Namespace vazio (distinto de erro) | Cada bloco em estado vazio |
| Kubeconfig sem `current-context` | Tela inteira |
| Kubeconfig inexistente, ilegível ou malformado (distinto de "sem contexto") | Tela inteira |

## 7. Requisitos não funcionais e invariantes

| ID | Requisito | Como é garantido (resumo) |
|---|---|---|
| RNF-01 | **Somente leitura**, verificável por máquina | Três camadas: acesso único só com `list_*`, teste estático por `ast` que falha com arquivo e linha, e RBAC de exemplo ([ADR-0005](adr/ADR-0005-somente-leitura-em-tres-camadas.md)) |
| RNF-02 | **Somente `127.0.0.1`**, só GET | Endereço fixo no código (só a porta é parâmetro), `405` para qualquer outro método; `netstat` no registro 8.10 ([ADR-0001](adr/ADR-0001-python-com-html-servido-localmente.md)) |
| RNF-03 | **Todo texto externo é escapado** | `html.escape(..., quote=True)` num único ponto (o renderizador), mais `Content-Security-Policy` que só permite o script de busca |
| RNF-04 | **Degradação por bloco**, sem stack trace | Cada listagem é classificada isoladamente ([ADR-0006](adr/ADR-0006-erros-classificados-por-bloco.md)) |
| RNF-05 | **Testável sem o cluster** | Tradução num módulo puro, com fixtures reais do laboratório ([ADR-0007](adr/ADR-0007-traducao-em-modulo-puro-com-fixtures-reais.md)) |
| RNF-06 | **Autenticação idêntica à do `kubectl`** | Cliente oficial `kubernetes` ([ADR-0002](adr/ADR-0002-cliente-oficial-do-kubernetes.md)) |
| RNF-07 | **Sem escrita no kubeconfig** | `persist_config=False` ao carregar |
| RNF-08 | **Carga mínima no apiserver** | Coleta pedida, listagens paginadas (`limit` de 500), sem retentativas, `timeout` de 3 s (conexão) e 10 s (leitura) |

## 8. Critérios de aceite

Validados contra o cluster kind do laboratório (`kind-metacortex-lab`, Kubernetes v1.37.0). O
detalhe, com as tabelas e as telas, está em [`../validacao/registro-laboratorio.md`](../validacao/registro-laboratorio.md).

| Tarefa | Critério | Resultado registrado |
|---|---|---|
| 8.1 | Pod em `CrashLoopBackOff` com estado, motivo e reinícios; Deployment `0/N` sem `readyReplicas`; Service sem endpoint e outro com endereços; eventos uma linha por objeto | `nyx-prod` com `CrashLoopBackOff` e última terminação `OOMKilled` (exit 137); `orion-web` `0/3`; `nyx-stg/nyx-api` `sem endpoint`; `orion-fake-shop` `2 endereços, 2 prontos`; `nyx-prod/nyx-api` `2 endereços, 0 prontos` |
| 8.2 | O filtro e a busca reduzem a lista, e a busca não muda o carimbo de hora | Filtro: 25 pods em "todos" contra 3 em `nyx-prod`. Busca `postgres`: Pods 1 de 3, Deployments 1 de 2, Services 1 de 2, Eventos 4 de 20. A busca não faz coleta por construção e por teste |
| 8.3, 8.4, 8.6, 8.7 e 8.8 | Cluster não responde, credencial inválida, namespace vazio, sem contexto, kubeconfig inválido | Mensagem própria em cada um, sem stack trace |
| 8.5 | Permissão negada para um tipo: só aquele bloco mostra `sem permissão` | Eventos com `sem permissão para listar eventos`; pods, deployments e services com dados |
| 8.9 | Credencial restrita a um namespace | Seletor com `sem permissão para listar namespaces`, `nyx-prod` pré-selecionado, quatro blocos com dados |
| 8.10 | Escuta só em `127.0.0.1` | `netstat` mostra `127.0.0.1:8765`; conexão ao IP da rede local recusada |
| 8.11 | Suíte automatizada | 158 testes passando (`validacao/pytest-2026-09-27.txt`) |

## 9. Premissas e dependências

- Python 3.12 ou superior (validado com 3.14) e o cliente `kubernetes` 36.0.3, fixado em
  `requirements.txt`.
- Um kubeconfig com `current-context` válido, em `KUBECONFIG` ou `~/.kube/config`.
- Credencial com permissão de `list` nos recursos que o painel lê. O ClusterRole de exemplo está em
  `deploy/rbac/`, e os dois papéis de laboratório (sem `events` e restrito a um namespace) em
  `deploy/lab/`.
- Servidor de laboratório Kubernetes v1.37.0, em que `Endpoints` já está depreciado (desde a 1.33) e
  `EndpointSlice` é a API estável.
- **Quem opera aplica o RBAC.** O painel e o change não aplicam nada no cluster.

## 10. Riscos de produto

| Risco | Mitigação |
|---|---|
| **Credencial ampla derruba a camada 3** (o RBAC não impede uma escrita se o painel rodar com o kubeconfig pessoal, geralmente administrativo) | As camadas 1 e 2 valem para qualquer credencial. A documentação explica como gerar um contexto dedicado ligado ao ClusterRole de exemplo |
| **Tela estática tomada por atual** | Carimbo de hora sempre visível no cabeçalho e nenhum temporizador escondido |
| **403 anônimo confundido com falta de permissão** | HTTP 403 cujo sujeito é `system:anonymous` é classificado como `credencial`, e é coberto por teste |
| **Nome de namespace digitado como vetor** | Validação DNS-1123 antes de qualquer chamada, mais o escape ao reapresentá-lo |
| **Eventos expiram** (TTL padrão de 1 h) | A tela diz isso junto ao bloco de eventos |
| **Cluster grande** | Coleta só quando pedida e listagem paginada |
| **Compatibilidade do cliente com o Python 3.14** | Versão do cliente fixada e validada na tarefa 1.1 |

## 11. Limites conhecidos e questões em aberto

| # | Item | Estado |
|---|---|---|
| Q1 | **Limite superior de exibição** com aviso "mostrando X de Y" | O design o deixou como ajuste de implementação, e o código **não** o tem: a listagem é paginada, mas a tela exibe tudo o que foi coletado |
| Q2 | **Empacotamento e distribuição** | Adiado. Hoje exige Python 3.12+ e um venv |
| Q3 | **Porta padrão** | Resolvida na implementação: 8765, com a opção `--porta` |
| Q4 | **Capturas de tela da validação** | Os prints dos cenários 8.2, 8.5 e 8.9 foram tirados na sessão de 2026-09-27, mas não estão no repositório. Ver o registro de validação |

## 12. Evolução prevista

Fora da fatia 1: logs de um pod (para a causa de um `CrashLoopBackOff` ainda é preciso o
`kubectl logs --previous`), métricas de consumo, troca de contexto e empacotamento. Cada item
amplia a permissão exigida ou o risco de olhar o cluster errado, e exigiria uma nova revisão do
RBAC mínimo.

## 13. Rastreabilidade

| Pergunta | Documento |
|---|---|
| Como o painel é construído? | [`03-TRD.md`](03-TRD.md) |
| Por que cada decisão foi tomada? | [`adr/README.md`](adr/README.md) e [`../CURADORIA.md`](../CURADORIA.md) |
| Qual é o contrato normativo? | `openspec/specs/cluster-dashboard/spec.md` |
| O que foi validado, e como? | [`../validacao/registro-laboratorio.md`](../validacao/registro-laboratorio.md) |
| Como as duas skills se comportaram? | [`../REGISTRO-SKILLS.md`](../REGISTRO-SKILLS.md) |
| Como se usa? | [`../README.md`](../README.md) |
