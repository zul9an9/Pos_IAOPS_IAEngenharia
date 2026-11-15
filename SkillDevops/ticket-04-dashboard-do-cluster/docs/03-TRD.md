# TRD — painel_cluster: requisitos e desenho técnico

| | |
|---|---|
| **Produto** | `painel_cluster` (Ticket 04) |
| **Estado** | Implementado (`painel_cluster/`, 7 módulos, cerca de 1.100 linhas) e coberto por 158 testes |
| **Fontes** | `design.md` do change `add-cluster-dashboard`, `openspec/specs/cluster-dashboard/spec.md`, o código em `painel_cluster/` e `tests/`, `deploy/` e `validacao/` |
| **Consolidado em** | 2026-11-08. Este documento descreve o que existe e remete cada decisão ao seu ADR |
| **Documentos irmãos** | [`02-PRD.md`](02-PRD.md) (o que e para quem) e [`adr/`](adr/README.md) (por que) |

## 1. Objetivo e escopo do documento

Descrever como o `painel_cluster` atende o [PRD](02-PRD.md): componentes, fluxo de uma requisição,
interfaces, regras de tradução, classificação de erros, garantias de segurança e estratégia de
testes. As decisões que sustentam o desenho estão nos ADRs, e aqui aparecem só pela sua consequência
técnica.

## 2. Contexto de execução

O painel roda na máquina de quem opera, como um processo único, e serve HTML em `127.0.0.1`. Não é
implantado como workload e não grava nada no cluster nem no disco.

```
 máquina de quem opera
┌──────────────────────────────────────────────────────────────────────────┐
│  navegador ──GET /?ns=…──► servidor.py (127.0.0.1:8765, só GET)          │
│                               │                                          │
│                               ▼                                          │
│          acesso.carregar_contexto()  ◄── KUBECONFIG | ~/.kube/config     │
│                               │  (só o current-context; sem chamada à API)│
│                               ▼                                          │
│                      coleta.coletar()  ── uma coleta por GET ──┐         │
│                               │                                 │         │
│          acesso.AcessoLeitura (única camada; só list_*) ◄───────┘         │
│                               │  JSON cru da API                          │
│                               ▼                                           │
│                      traducao.py (módulo puro, sem I/O)                   │
│                               │  linhas prontas, em texto cru             │
│                               ▼                                           │
│                      render.py (único que monta HTML; escapa)             │
│                               │                                           │
└───────────────────────────────┼───────────────────────────────────────────┘
                                ▼
                     apiserver do contexto corrente (só leitura)
```

## 3. Restrições de projeto

1. **Somente o contexto corrente.** Sem seleção de contexto nem multicluster.
2. **Coleta só sob demanda.** Sem polling e sem watch.
3. **Nenhuma escrita**, garantida em camadas (ADR-0005).
4. **A API omite campos em vez de mandá-los vazios**, como a coleta de 2026-09-27 mostrou:
   `orion-stg/orion-web` sem `readyReplicas` e `nyx-stg/nyx-api` com EndpointSlice `endpoints: null`.
5. **Python 3.12+** (validado com 3.14). A única dependência de runtime além da biblioteca padrão é
   o cliente oficial `kubernetes` (36.0.3), com `PyYAML` para ler o kubeconfig.

## 4. Componentes

| Módulo (`painel_cluster/`) | Responsabilidade | Fronteira que mantém |
|---|---|---|
| `__main__.py` | Ponto de entrada (`python -m painel_cluster`), opção `--porta`, logging | Só sobe o servidor |
| `servidor.py` | Servidor HTTP em `127.0.0.1`. Cada `GET /` produz **uma** coleta | Endereço fixo, não configurável. Qualquer método que não seja GET recebe `405` |
| `acesso.py` | Camada única de acesso: carrega o kubeconfig, expõe só `list_*` e traduz exceções em `ErroPainel` | **Único** módulo que importa `kubernetes`. Nunca grava no kubeconfig |
| `coleta.py` | Uma coleta: listagens independentes, cada uma com seu erro classificado | Só `nao-respondeu` e `credencial` valem para a tela inteira |
| `erros.py` | Categorias de erro (`ErroPainel`) | O renderizador recebe categoria e campos de exibição, nunca uma exceção |
| `traducao.py` | API → linhas da tela. Funções puras, sem I/O | Recebe o JSON cru e devolve **texto cru**; não escapa HTML |
| `render.py` | Monta o HTML de todas as páginas | É a **única** parte que monta HTML e a única que escapa |

`ErroPainel` carrega `categoria`, e opcionalmente `recurso`, `caminho`, `tipo`, `motivo` e
`detalhe`. O `detalhe` vai só para o log local, **nunca** para a tela.

## 5. Fluxo de uma requisição

`servidor.Painel.pagina`:

1. **Carrega o contexto** (`acesso.carregar_contexto`), sem nenhuma chamada à API. Falha →
   `pagina_kubeconfig` (`kubeconfig-invalido` ou `sem-contexto`), tela inteira.
2. **Lê o parâmetro `ns`** da URL. Se existir e **não** for um rótulo DNS-1123 válido →
   `pagina_namespace_invalido`, **antes de qualquer chamada**.
3. **Coleta** (`coleta.coletar`) com a camada de acesso e o namespace (ou `None`).
4. **Renderiza** (`render.pagina`) e responde `200`. Qualquer exceção não prevista ao montar a
   página vira `pagina_inesperada`, sem detalhe na tela (o detalhe vai ao log).

## 6. Interfaces

### 6.1 Linha de comando

```
python -m painel_cluster [--porta 8765]
```

Só a porta é parâmetro. O endereço de escuta é fixo em `127.0.0.1`.

### 6.2 HTTP

| Requisição | Resposta |
|---|---|
| `GET /` (opcional `?ns=<namespace>`) | `200`, HTML. É o gatilho de **uma** coleta |
| `GET` em qualquer outro caminho | `404`, página simples |
| Qualquer outro método (`POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS` e métodos inventados) | `405` com `Allow: GET`, sem chegar à coleta |

Cabeçalhos de toda resposta: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` e
`Content-Security-Policy`:

```
default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-<hash do script de busca>';
form-action 'self'; base-uri 'none'; frame-ancestors 'none'
```

O único `<script>` da página é o script estático de busca, e a política só o permite por hash.

### 6.3 Kubeconfig

`acesso.carregar_contexto` lê, na ordem do `kubectl`, os caminhos de `KUBECONFIG` (lista) ou
`~/.kube/config`, mescla os documentos (o primeiro arquivo que define um valor vence) e usa só o
`current-context`. Falha **antes de qualquer chamada à API** quando:

| Situação | Categoria |
|---|---|
| Nenhum arquivo existe, ou não pôde ser lido, ou não é YAML válido, ou não tem estrutura de kubeconfig | `kubeconfig-invalido` (tipo `inexistente`, `ilegível` ou `malformado`) |
| O contexto corrente aponta para contexto, cluster ou usuário que não existem, ou o cluster não tem endereço de servidor | `kubeconfig-invalido` (`malformado`) |
| O cliente do Kubernetes recusa o conteúdo | `kubeconfig-invalido` (`malformado`) |
| Não há `current-context` | `sem-contexto` |

A mensagem cita o **caminho e o tipo**, nunca o conteúdo. O cliente é criado com
`persist_config=False` (o painel nunca grava no kubeconfig de quem opera) e `retries = False`.

### 6.4 Operações de leitura

A camada de acesso expõe **exatamente** estas operações (`OPERACOES_PERMITIDAS`):

`list_namespace` · `list_pod_for_all_namespaces` · `list_namespaced_pod` ·
`list_deployment_for_all_namespaces` · `list_namespaced_deployment` ·
`list_service_for_all_namespaces` · `list_namespaced_service` ·
`list_endpoint_slice_for_all_namespaces` · `list_namespaced_endpoint_slice` ·
`list_namespaced_event`

Cada listagem é paginada (`limit` de 500, seguindo `continue`), com `timeout` de **3 s** de
conexão e **10 s** de leitura, **sem retentativas**. Os itens voltam como o JSON cru da API
(`_preload_content=False`), de modo que campo ausente continua ausente, e a tradução o trata num só
lugar.

## 7. Coleta

Uma coleta (`coleta.coletar`) faz, cada uma isolada das demais:

| Sem namespace selecionado | Com namespace selecionado |
|---|---|
| `list_namespace` | `list_namespace` |
| pods, deployments, services e EndpointSlices de **todos** os namespaces | pods, deployments, services e EndpointSlices **do namespace** |
| (sem eventos: o bloco pede que se selecione um namespace) | eventos do namespace |

Regras:

- Se `list_namespace` falha com `nao-respondeu` ou `credencial`, **não insiste**: a tela inteira
  mostra o erro.
- Se `list_namespace` falha com **403**, o seletor degrada (seção 8) e a coleta passa a usar só as
  listagens **por namespace**, com o namespace do contexto quando não houver um selecionado.
- Se **todas** as listagens caem em `nao-respondeu` ou `credencial`, a tela inteira mostra essa
  mensagem.
- Se só os EndpointSlices forem negados, a coluna "Endpoint" dos Services mostra
  `sem permissão para ler endpointslices` (ou `não foi possível ler endpointslices`), e o resto do
  bloco continua.

## 8. Classificação de erros (por bloco)

`acesso.classificar` traduz a exceção do cliente numa categoria ([ADR-0006](adr/ADR-0006-erros-classificados-por-bloco.md)):

| Origem | Categoria | Onde aparece |
|---|---|---|
| Kubeconfig inexistente, ilegível, YAML inválido, ou contexto apontando para algo ausente (antes de qualquer chamada) | `kubeconfig-invalido` | Tela inteira |
| Kubeconfig sem `current-context` (antes de qualquer chamada) | `sem-contexto` | Tela inteira |
| Conexão recusada, DNS, TLS de servidor, `timeout`, status HTTP 0 | `nao-respondeu` | Tela inteira |
| HTTP 401; falha de plugin `exec` ou do carregamento de credencial; HTTP 403 cujo corpo cita `system:anonymous` | `credencial` | Tela inteira |
| HTTP 403 de usuário autenticado | `sem-permissao` | Só o bloco |
| Lista vazia com HTTP 200 | `vazio` | Só o bloco |
| Outro status HTTP ou qualquer outra exceção | `inesperado` (mensagem genérica, detalhe só no log) | Só o bloco |

Os textos de tela de cada categoria são distintos. Em particular, `nao-respondeu` e `credencial`
**não** compartilham mensagem. O bloco negado mostra `sem permissão para listar <recurso>`, onde o
recurso é traduzido para exibição (por exemplo, `events` aparece como `eventos`).

**Seletor de namespace sem permissão.** O 403 na listagem de namespaces **não** vira bloco de erro:
o seletor vira um campo de texto com o aviso `sem permissão para listar namespaces`, pré-preenchido
com o `namespace` do contexto corrente quando existir, e o bloco de namespaces mostra o mesmo aviso.
O nome digitado é validado como rótulo DNS-1123 (minúsculas, dígitos e hífen, até 63 caracteres)
**antes** de qualquer chamada, e escapado ao ser reapresentado.

## 9. Tradução API → tela

`traducao.py` é puro: recebe o JSON cru e devolve texto cru ([ADR-0007](adr/ADR-0007-traducao-em-modulo-puro-com-fixtures-reais.md)).

| Objeto | Regra |
|---|---|
| **Pod** | `fase` (ou `—`); `prontos` = contêineres com `ready: true` sobre o total declarado em `spec.containers`; `reinicios` = soma de `restartCount` de contêineres **e** init containers; `motivo` = razão do pod, mais, por contêiner (init e normais), `waiting.reason` ou terminação com código diferente de zero, mais `última terminação: <razão> (exit <código>)` quando houve reinício. Pod sem `containerStatuses` aparece com 0 reinícios |
| **Deployment** | `readyReplicas` ausente → `0`; `spec.replicas` ausente → `1` (default da API). Mostra `prontas/desejadas` |
| **Service** | Tipo, `clusterIP`, portas e o resumo de endpoint. `ExternalName` mostra `ExternalName (<alvo>)` |
| **Endpoint** (`resumo_endpoints`) | Agrupa EndpointSlices por `kubernetes.io/service-name`. Conta **endereços únicos** e, separadamente, os com `conditions.ready` diferente de `false` (a API define `ready` ausente como `true`). Sem endereços → `sem endpoint`; senão `N endereços, M prontos` ([ADR-0004](adr/ADR-0004-endpointslice-agregado-por-service.md)) |
| **Evento** | Um objeto, uma linha: tipo, razão, mensagem, objeto envolvido, `count` (ausente → `series.count` → `1`), primeira e última ocorrência (com fallback para `eventTime` e `series.lastObservedTime`). Ordenado do mais recente para o mais antigo |

A tela não rotula nada como "saudável": um teste renderiza todas as fixtures e falha se o HTML
contiver termos de juízo de saúde.

## 10. Renderização

`render.py` monta uma página única, com: cabeçalho (contexto, servidor e carimbo de hora da coleta),
**aviso permanente de somente leitura**, controles (seletor ou campo de namespace, botão
**Atualizar** e o campo de busca) e os blocos Namespaces, Pods, Deployments, Services e Eventos.

- Cada bloco está num de quatro estados: **dados**, **vazio** (`Nenhum item de <recurso> neste
  namespace` ou `no cluster`), **erro** (a mensagem da categoria) ou **aviso** (por exemplo, "Selecione
  um namespace para ver os eventos").
- O bloco de eventos traz a nota de que a API retém eventos por tempo limitado (padrão do
  Kubernetes: 1 hora).
- **Escape:** todo texto externo passa por `html.escape(..., quote=True)`, e só o renderizador
  monta HTML.
- **Busca:** o campo de busca **não pertence ao formulário** e não tem `name`. Um script estático
  esconde as linhas (`tr[data-nome]`) que não contêm o termo e atualiza a contagem de cada bloco
  para `visíveis de total`. O script não faz requisições nem usa temporizadores, e por isso não muda
  o carimbo de hora. A busca alcança os eventos pelo nome do objeto envolvido.

## 11. Garantia de somente leitura

Três camadas independentes, mais as proteções do servidor ([ADR-0005](adr/ADR-0005-somente-leitura-em-tres-camadas.md)):

1. **Camada única de acesso.** Só `acesso.py` importa `kubernetes`, e só expõe as `list_*` da seção
   6.4.
2. **Teste estático** (`tests/test_somente_leitura.py`). Percorre com `ast` todos os `.py` do
   projeto, inclusive a camada de acesso, e falha com arquivo e linha ao encontrar: atributo
   chamado com prefixo `create_`, `patch_`, `replace_`, `delete_` ou `connect_` (este cobre exec,
   attach, port-forward e proxy); `kubernetes.stream`, `watch.Watch` ou o argumento `watch=True`;
   `call_api` ou `request` com método de escrita; `subprocess` invocando `kubectl`; e import de
   `kubernetes` fora da camada de acesso. Outro teste confirma que a camada exporta exatamente a
   lista permitida, e um terceiro **planta** arquivos proibidos num diretório temporário e exige
   que o scanner os detecte, para provar que o teste não passa por vacuidade.
3. **RBAC de exemplo** (`deploy/rbac/clusterrole-somente-leitura.yaml`). ClusterRole com
   `get`/`list`/`watch`, sem curingas, só nos recursos lidos. O `watch` entra por fazer parte do
   conjunto canônico de leitura (o mesmo do papel embutido `view`), e o código não o usa: o papel diz
   o que a credencial *poderia* ler, e o teste da camada 2 garante que o código *não* abre watch.

As camadas 1 e 2 valem para qualquer credencial. A camada 3 só protege se o painel rodar com a
credencial ligada ao papel de exemplo, e não com o kubeconfig pessoal.

Somam-se: o servidor só aceita GET e só escuta em `127.0.0.1`, o kubeconfig nunca é gravado
(`persist_config=False`) e o aviso de somente leitura aparece em toda tela.

## 12. Artefatos de RBAC e de laboratório

| Arquivo | Para quê |
|---|---|
| `deploy/rbac/clusterrole-somente-leitura.yaml` | Papel de exemplo: Namespace `painel-cluster`, ServiceAccount, ClusterRole e ClusterRoleBinding |
| `deploy/lab/sem-eventos.yaml` | **Só laboratório**: igual ao exemplo, porém **sem `events`**. Valida o cenário 8.5 (permissão negada para um tipo) |
| `deploy/lab/so-um-namespace.yaml` | **Só laboratório**: ServiceAccount com Role e RoleBinding só em um namespace, sem acesso de cluster. Valida o cenário 8.9 |
| `deploy/lab/README.md` | Como aplicar os manifestos e gerar um kubeconfig por ServiceAccount (token de 8 h) |
| `manifests-lab/` | Manifests dos workloads de laboratório (`orion-prod` e `helio-prod`), gerados pela skill do Ticket 01 |

Quem opera aplica tudo com `kubectl`. O painel e o change não aplicam nada.

## 13. Estratégia de testes

158 testes, com `pytest`, em 8 arquivos. Os testes usam **fixtures reais** capturadas do cluster de
laboratório só com `kubectl get -o json` (`tests/fixtures/`, recapturáveis por
`tests/fixtures/capturar.sh`), e um `AcessoFalso` que substitui a camada de acesso.

| Arquivo | Testes | O que garante |
|---|---|---|
| `test_render.py` | 62 | Aviso de somente leitura, escape (incluindo mensagem de evento com `<script>`), mensagens de cada categoria, busca no navegador sem coleta, ausência de juízo de saúde |
| `test_coleta.py` | 25 | As chamadas exatas de cada coleta, namespace vazio distinto de erro, classificação, eventos negados com o resto funcionando, namespaces negados |
| `test_traducao.py` | 22 | As três armadilhas de dados, com as fixtures dos casos reais |
| `test_servidor.py` | 14 | Escuta só em `127.0.0.1`, endereço não configurável, outra interface recusada, `405` sem coleta, `404`, cabeçalho CSP, namespace inválido recusado sem chamar a API, erro inesperado sem traceback |
| `test_kubeconfig.py` | 11 | Só o contexto corrente, nada gravado no kubeconfig, e os casos de sem contexto, inexistente, ilegível, YAML inválido e contexto apontando para cluster ou usuário ausente. O motivo nunca expõe o conteúdo |
| `test_fixtures.py` | 8 | Que cada fixture traz o caso real esperado (`nyx-prod` com `OOMKilled` e evento de `count` alto, `orion-stg` sem `readyReplicas`, `nyx-stg` com `endpoints: null`, `orion-prod` com dois endereços prontos, `nyx-prod` com nenhum pronto, `kube-public` vazio) e que não contêm as senhas do laboratório |
| `test_somente_leitura.py` | 8 | A varredura por `ast`, os arquivos plantados e a lista exata de operações |
| `test_rbac.py` | 8 | O ClusterRole de exemplo (só `get`/`list`/`watch`, sem curingas, cobrindo exatamente os recursos do painel, com o verbo `watch` explicado), os dois papéis de laboratório, e que nenhum script do projeto aplica manifestos |

Os cenários que dependem do cluster vivo (grupo 8 das tarefas) ficam em
[`../validacao/registro-laboratorio.md`](../validacao/registro-laboratorio.md). O cluster vivo é a
validação final, mas **não o único teste**: o estado do laboratório muda (`nyx-prod` continua
acumulando reinícios), então os testes de tradução verificam os valores contra as fixtures
congeladas, e o registro de validação anota os valores vivos.

## 14. Não objetivos de design

1. **Persistência.** Cada coleta vive só na memória do processo até a próxima.
2. **Autenticação do próprio painel.** A fronteira de confiança é "quem tem shell nesta máquina já
   tem o kubeconfig".
3. **Empacotamento e distribuição.** Adiado.

## 15. Riscos técnicos e mitigações

| Risco | Mitigação |
|---|---|
| Credencial ampla derruba a camada 3 | Camadas 1 e 2 valem para qualquer credencial; documentação do contexto dedicado |
| 403 anônimo confundido com falta de permissão | `system:anonymous` classificado como `credencial`, com teste |
| Listagem em todos os namespaces exige permissão de cluster | O seletor degrada para digitação e a coleta passa a ser por namespace (validado com Role restrita a `nyx-prod`) |
| Nome de namespace digitado como vetor | Validação DNS-1123 antes de qualquer chamada, mais escape |
| Cluster grande | Coleta sob demanda e listagem paginada. Não há limite superior de exibição (PRD, Q1) |
| Eventos expiram (TTL de 1 h) | Nota na tela |
| Compatibilidade do cliente `kubernetes` com o Python 3.14 | Versão fixada e validada na tarefa 1.1 |
| Tela estática tomada por atual | Carimbo de hora sempre visível, sem temporizador escondido |

## 16. Implantação e operação

Projeto novo, sem migração nem nada implantado no cluster.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m painel_cluster                     # http://127.0.0.1:8765/
.venv/Scripts/python -m painel_cluster --porta 9000        # outra porta
.venv/Scripts/python -m pytest                             # suíte completa
```

Reversão: basta não executar o painel. Ele não guarda estado no cluster nem no disco.

## 17. Rastreabilidade das decisões

| ADR | Decisão | `design.md` |
|---|---|---|
| [0001](adr/ADR-0001-python-com-html-servido-localmente.md) | Python 3 com HTML servido localmente (descartados Go e TUI) | D1 |
| [0002](adr/ADR-0002-cliente-oficial-do-kubernetes.md) | Cliente oficial do Kubernetes (descartados `kubectl` e HTTP direto) | D2 |
| [0003](adr/ADR-0003-atualizacao-sob-demanda.md) | Atualização sob demanda com carimbo de hora (descartados polling e watch) | D3 |
| [0004](adr/ADR-0004-endpointslice-agregado-por-service.md) | EndpointSlice agregado por Service (descartados `Endpoints` e inferência pelo selector) | D4 |
| [0005](adr/ADR-0005-somente-leitura-em-tres-camadas.md) | Garantia de somente leitura em três camadas | D5 |
| [0006](adr/ADR-0006-erros-classificados-por-bloco.md) | Erros classificados por bloco, com mensagem por categoria | D6 |
| [0007](adr/ADR-0007-traducao-em-modulo-puro-com-fixtures-reais.md) | Tradução API → tela em módulo puro, testado com fixtures reais | D7 |
| [0008](adr/ADR-0008-escopo-da-primeira-fatia.md) | Escopo da primeira fatia | `proposal.md`; `CURADORIA.md` §3.4 |
