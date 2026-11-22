# Tarefas

## 1. Projeto e fronteira de só leitura

- [x] 1.1 Criar a estrutura do projeto Python (pacote da aplicação, `tests/`, dependência fixada do cliente `kubernetes`, `pytest` para testes) e verificar que `pip install` e `pytest` rodam no Python local (3.14; se o cliente for incompatível, registrar e usar 3.12/3.13, conforme design.md)
- [x] 1.2 Criar a camada única de acesso, o único módulo que importa `kubernetes`, expondo só as funções de listagem listadas em design.md (D5), e verificar com um teste que o conjunto exportado é exatamente essa lista
- [x] 1.3 Escrever o teste estático de só leitura (D5): varredura `ast` de todos os `.py` do projeto, inclusive a camada de acesso, que falha com arquivo:linha em `create_`/`patch_`/`replace_`/`delete_`/`connect_`, `kubernetes.stream`, `watch.Watch`, argumento `watch=True` em qualquer chamada, `call_api`/`request` com método de escrita, `subprocess` com `kubectl` e import de `kubernetes` fora da camada; verificar que passa no projeto e falha, com arquivo:linha, em três arquivos plantados em diretório temporário: um com `delete_namespaced_pod`, um com `watch.Watch()` e um com `list_namespaced_pod(..., watch=True)`

## 2. Kubeconfig e contexto corrente

- [x] 2.1 Carregar o kubeconfig (respeitando `KUBECONFIG`) usando só o `current-context`, expor nome do contexto, servidor e o `namespace` do contexto (quando houver), e verificar com um kubeconfig de teste com dois contextos que só o corrente é usado e nenhum seletor de contexto existe
- [x] 2.2 Detectar kubeconfig sem `current-context` antes de qualquer chamada à API e classificar como `sem-contexto`, verificado por teste unitário com kubeconfig sem o campo, sem nenhuma chamada de rede
- [x] 2.3 Detectar kubeconfig inexistente, ilegível ou malformado antes de qualquer chamada à API e classificar como `kubeconfig-invalido`, com caminho tentado e tipo do problema, sem conteúdo do arquivo; verificar com testes unitários, sem chamada de rede, para: caminho inexistente, caminho que é diretório ou arquivo não legível, YAML inválido, e `current-context` apontando para usuário inexistente; verificar também que a mensagem difere da de `sem-contexto`

## 3. Fixtures reais e tradução API → tela

- [x] 3.1 Capturar do laboratório, só com `kubectl get -o json`, as fixtures de `nyx-prod` (pods, deployments, services, endpointslices, events), `orion-stg` (deployment `orion-web`, pods), `nyx-stg` (service e endpointslice `nyx-api`), `orion-prod` (service e endpointslice `orion-fake-shop`) e `kube-public` (listas vazias) em `tests/fixtures/`, e verificar que cada arquivo contém o caso descrito em proposal.md (Impact)
- [x] 3.2 Implementar a tradução de pods (fase, prontos x/y, soma de reinícios incluindo init containers, motivo com `waiting.reason` + `lastState.terminated.reason`/`exitCode` e marcação de init container) e verificar com a fixture `nyx-prod` que sai `Running`, `0/1`, `155`, `CrashLoopBackOff`, `OOMKilled (exit 137)`, e com `orion-stg` que sai `ImagePullBackOff`, `0`, e com um pod sem `containerStatuses` que sai `0` reinícios sem erro
- [x] 3.3 Implementar a tradução de deployments (`readyReplicas` ausente → 0, `spec.replicas` ausente → 1) e verificar com a fixture `orion-stg/orion-web` que sai `0/3`, com `orion-prod/orion-fake-shop` que sai `2/2`, e com um Deployment sintético sem `spec.replicas` nem `readyReplicas` que sai `0/1` e que o texto não contém `None`
- [x] 3.4 Implementar o resumo de endpoint agregando EndpointSlices por `kubernetes.io/service-name` com endereços únicos e contagem de `ready: true`, e verificar: `nyx-stg/nyx-api` → `sem endpoint`; `orion-prod/orion-fake-shop` → `2 endereços, 2 prontos`; `nyx-prod/nyx-api` → `2 endereços, 0 prontos`; caso sintético com o mesmo Service em dois slices e endereço repetido → soma sem duplicar; Service `ExternalName` → `ExternalName`
- [x] 3.5 Implementar a tradução de eventos (uma linha por objeto, `involvedObject`, `count` ausente → 1, fallback de carimbos para `eventTime`/`series.lastObservedTime` e depois `—`, ordem do mais recente) e verificar com a fixture `nyx-prod` que o `BackOff` de `count` 429 vira exatamente uma linha com 429
- [x] 3.6 Adicionar teste que renderiza todas as fixtures e falha se o HTML contiver termos de juízo de saúde (`saudável`, `healthy`, `OK` como rótulo, `✓`), verificando a armadilha (c)

## 4. Coleta e classificação de erros

- [x] 4.1 Implementar a coleta sob demanda: listagens independentes (namespaces; pods, deployments, services, endpointslices em todos os namespaces ou no selecionado; eventos só com namespace selecionado), paginadas, com timeout connect 3 s / read 10 s e sem retentativas, registrando o carimbo de hora com fuso, e verificar com a camada de acesso simulada que uma coleta faz exatamente essas chamadas e nenhuma outra
- [x] 4.2 Implementar a classificação de D6 (`nao-respondeu`, `credencial` incluindo 401, falha de plugin `exec` e 403 `system:anonymous`, `sem-permissao`, `vazio`, `inesperado`) e verificar com testes unitários, um por categoria, usando exceções simuladas
- [x] 4.3 Verificar com teste que uma coleta em que só a listagem de eventos retorna 403 produz o bloco de eventos `sem-permissao` e os blocos de pods, deployments e services com dados
- [x] 4.4 Implementar a degradação do seletor quando a listagem de namespaces retorna 403: aviso `sem permissão para listar namespaces`, namespace do contexto pré-selecionado quando houver, coleta passando a usar só listagens por namespace; verificar com testes: (a) 403 em namespaces e namespace do contexto `nyx-prod` resulta em seletor degradado com `nyx-prod` e blocos com dados; (b) sem namespace no contexto, o seletor pede o nome e nenhum bloco quebra

## 5. Servidor local e telas

- [x] 5.1 Implementar o servidor com `http.server` ligado fixo em `127.0.0.1` (só a porta é parâmetro), aceitando só GET e respondendo 405 aos demais métodos sem chamar a coleta; verificar com testes que o endereço do socket é `127.0.0.1`, que não existe opção para mudar o endereço, que uma conexão pelo IP de rede local da máquina é recusada, e que POST/PUT/PATCH/DELETE retornam 405 com zero chamadas à camada de acesso
- [x] 5.2 Implementar a página: cabeçalho com contexto, servidor, carimbo de hora e aviso permanente de somente leitura; blocos de namespaces, pods, deployments, services e eventos; todo texto externo escapado num único ponto com `html.escape(..., quote=True)`; verificar com testes que o aviso aparece em todas as telas, inclusive nas de erro; que um evento com `message` `<script>alert(1)</script>` gera `&lt;script&gt;` e nenhum elemento `<script>` vindo dele; e que um nome com aspas usado em atributo não encerra o atributo
- [x] 5.3 Implementar o filtro por namespace (gatilho de nova coleta), com campo para informar o nome manualmente validado como rótulo DNS-1123 antes de qualquer chamada, e a busca por nome no navegador (substring, sem distinguir maiúsculas, sobre `metadata.name` e `involvedObject.name`, sem nova coleta); verificar que a busca não altera o carimbo de hora e que `Nyx_Prod` e `<script>` são recusados sem chamada à API
- [x] 5.4 Implementar as mensagens em tela de cada categoria de D6 (`kubeconfig-invalido` com caminho e tipo, `sem-contexto`, `nao-respondeu` com servidor e horário, `credencial` com texto distinto, `sem permissão` por bloco com o recurso negado, vazio distinto de erro, `inesperado` genérico) e verificar com teste que nenhuma resposta HTML contém `Traceback` nem nome de classe de exceção

## 6. RBAC de exemplo

- [x] 6.1 Escrever `deploy/rbac/clusterrole-somente-leitura.yaml` (ClusterRole + ClusterRoleBinding para ServiceAccount dedicada) com só `get`/`list`/`watch` em `namespaces`, `pods`, `services`, `events` (core), `deployments` (apps) e `endpointslices` (discovery.k8s.io), e um comentário no YAML explicando que `watch` entra por ser do conjunto canônico de leitura, mas o código não o usa e o teste de só leitura o barra; e um teste que lê o YAML e falha se houver verbo fora de `{get, list, watch}` ou `*` em verbos, recursos ou grupos
- [x] 6.2 Escrever dois manifestos só para o laboratório: `deploy/lab/sem-eventos.yaml`, igual à 6.1 porém sem `events`; e `deploy/lab/so-um-namespace.yaml`, com ServiceAccount, Role e RoleBinding em `nyx-prod` só com `get`/`list`/`watch` em pods, services, events, deployments e endpointslices, sem acesso a namespaces. Escrever também um README curto com os comandos para quem opera aplicar os manifestos e gerar kubeconfigs com o token de cada ServiceAccount (o de `so-um-namespace` com `namespace: nyx-prod` no contexto); verificar por leitura que nenhum script do projeto aplica esses arquivos (a aplicação é manual, por quem opera)

## 7. Documentação

- [x] 7.1 Escrever o README do painel: como executar, que só usa o contexto corrente, as três camadas da garantia de só leitura, como rodar sob o ClusterRole de exemplo e o limite dos eventos retidos pela API; verificar que cada comando do README funciona como descrito

## 8. Validação contra o cluster kind do laboratório

Todos os cenários adversos usam cópias de kubeconfig em diretório temporário via `KUBECONFIG`. O kubeconfig real de quem opera e o cluster não são alterados pelo painel.

- [x] 8.1 Com o contexto `kind-metacortex-lab`, verificar na tela: pods `nyx-prod/nyx-api-*` com `CrashLoopBackOff`, motivo com `OOMKilled` e mais de 150 reinícios; `orion-stg/orion-web` em `0/3`; `nyx-stg/nyx-api` com `sem endpoint`; `orion-prod/orion-fake-shop` com `2 endereços, 2 prontos`; eventos de `nyx-prod` com uma linha por evento e `count` na casa das centenas
- [x] 8.2 Verificar que o filtro `nyx-prod` e a busca `postgres` reduzem a lista em relação a "todos os namespaces" e que a busca não muda o carimbo de hora
- [x] 8.3 Cenário cluster não responde: kubeconfig cópia com `server: https://127.0.0.1:1`; verificar mensagem `nao-respondeu`, sem stack trace
- [x] 8.4 Cenário credencial inválida: kubeconfig cópia com token inválido no usuário; verificar mensagem de credencial distinta da de 8.3, sem stack trace
- [x] 8.5 Cenário permissão parcial: depois que quem opera aplicar `deploy/lab/sem-eventos.yaml` e gerar o kubeconfig da ServiceAccount (6.2), selecionar `nyx-prod` e verificar eventos com `sem permissão` e pods, deployments e services com dados
- [x] 8.6 Cenário namespace vazio: selecionar `kube-public` e verificar o estado vazio em todos os blocos, distinto de erro e de `sem permissão`
- [x] 8.7 Cenário sem contexto corrente: kubeconfig cópia sem `current-context`; verificar a mensagem dedicada e que nenhuma conexão ao apiserver foi tentada
- [x] 8.8 Cenário kubeconfig inválido: `KUBECONFIG` apontando para um caminho inexistente e, depois, para uma cópia com YAML quebrado; verificar nos dois casos a mensagem `kubeconfig-invalido` com o caminho, distinta da de 8.7, sem stack trace e sem conexão ao apiserver
- [x] 8.9 Cenário credencial restrita a um namespace: depois que quem opera aplicar `deploy/lab/so-um-namespace.yaml` e gerar o kubeconfig (6.2), abrir o painel e verificar seletor com `sem permissão para listar namespaces`, `nyx-prod` pré-selecionado e pods, deployments, services e eventos de `nyx-prod` exibidos
- [x] 8.10 Verificar com o painel rodando que `netstat -ano` mostra a porta escutando só em `127.0.0.1` e que abrir `http://<IP-da-rede-local>:<porta>` falha
- [x] 8.11 Rodar a suíte completa (`pytest`) e confirmar que o teste de só leitura (incluindo watch), o de ClusterRole, o de escape de HTML e o de ausência de juízo de saúde passam, anexando a saída ao registro da validação
