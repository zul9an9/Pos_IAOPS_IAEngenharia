# Spec Delta

## Purpose

Dar a quem opera um retrato rápido e só de leitura do cluster do contexto corrente do kubeconfig: namespaces, pods, deployments, services e eventos recentes. Assim, os primeiros minutos de um chamado não dependem de rodar à mão a mesma sequência de `kubectl`.

## ADDED Requirements

### Requirement: Acesso somente ao contexto corrente
O sistema SHALL ler o kubeconfig de quem opera e usar exclusivamente o contexto marcado como `current-context`. O sistema SHALL exibir no cabeçalho de toda tela o nome desse contexto e o endereço do servidor. O sistema SHALL NOT oferecer seleção ou troca de contexto ou cluster nesta fatia.

#### Scenario: kubeconfig com vários contextos
- **WHEN** o kubeconfig carregado define mais de um contexto
- **THEN** o painel lê e exibe apenas dados do `current-context`, mostra o nome dele no cabeçalho e não oferece opção para escolher outro

### Requirement: Lista de namespaces
O sistema SHALL listar os namespaces que as credenciais do contexto corrente conseguem listar e SHALL usá-los como opções do filtro por namespace.

Quando a listagem de namespaces for negada (HTTP 403 de usuário autenticado), o painel SHALL NOT ficar sem filtro. Nesse caso:
- o seletor SHALL exibir `sem permissão para listar namespaces`;
- o seletor SHALL permitir informar o nome do namespace manualmente;
- se o contexto corrente do kubeconfig definir `namespace`, o seletor SHALL vir preenchido e selecionado com ele;
- o nome informado SHALL ser validado como nome de namespace (rótulo DNS-1123: minúsculas, dígitos e hífen, até 63 caracteres). Nome inválido é recusado com mensagem, sem chamada à API;
- os demais blocos da tela SHALL continuar funcionando.

#### Scenario: namespaces disponíveis
- **WHEN** a pessoa abre o painel contra o cluster do laboratório
- **THEN** aparecem, entre outros, `nyx-prod`, `nyx-stg`, `orion-prod`, `orion-stg`, `helio-prod` e `kube-public`

#### Scenario: listagem de namespaces negada com namespace no contexto
- **WHEN** a credencial é restrita a um namespace, a listagem de namespaces retorna 403 e o contexto corrente define `namespace: nyx-prod`, com pods, deployments, services, endpointslices e eventos de `nyx-prod` permitidos
- **THEN** o seletor mostra `sem permissão para listar namespaces`, vem com `nyx-prod` selecionado e permite digitar outro nome, e os blocos de pods, deployments, services e eventos exibem os dados de `nyx-prod`

#### Scenario: listagem de namespaces negada sem namespace no contexto
- **WHEN** a listagem de namespaces retorna 403 e o contexto corrente não define `namespace`
- **THEN** o seletor mostra `sem permissão para listar namespaces` com campo para informar o nome, e, depois que a pessoa informa um namespace válido, os blocos exibem os dados dele

#### Scenario: nome de namespace inválido informado
- **WHEN** a pessoa informa manualmente um nome que não é rótulo DNS-1123 válido, por exemplo `Nyx_Prod` ou `<script>`
- **THEN** o painel recusa o nome com mensagem, sem chamada à API e sem stack trace

### Requirement: Estado dos pods
Para cada pod, o sistema SHALL mostrar: nome, namespace, a `phase` reportada, contêineres prontos sobre o total, a soma de `restartCount` de todos os contêineres (inclusive init containers) e, quando algum contêiner estiver em falha, o motivo reportado pela API. Um contêiner está em falha quando traz `state.waiting.reason`, `state.terminated` com `exitCode` diferente de zero, ou `lastState.terminated` junto com reinícios. O motivo SHALL incluir:
- o `state.waiting.reason` (ou `state.terminated.reason`);
- quando existir, o `lastState.terminated.reason` com o `exitCode`;
- a identificação do contêiner quando ele for init container.

O estado SHALL vir dos contêineres e não apenas da `phase`.

#### Scenario: pod em CrashLoopBackOff com fase Running
- **WHEN** um pod tem `phase: Running`, contêiner com `state.waiting.reason: CrashLoopBackOff`, `lastState.terminated.reason: OOMKilled`, `exitCode: 137` e `restartCount: 155` (caso `nyx-prod/nyx-api-*`)
- **THEN** a linha do pod mostra fase `Running`, prontos `0/1`, reinícios `155` e motivo `CrashLoopBackOff`, com última terminação `OOMKilled (exit 137)`

#### Scenario: pod em ImagePullBackOff
- **WHEN** um pod tem contêiner com `state.waiting.reason: ImagePullBackOff` e `restartCount: 0` (caso `orion-stg/orion-web-*`)
- **THEN** a linha mostra motivo `ImagePullBackOff` e reinícios `0`

#### Scenario: falha em init container
- **WHEN** o contêiner em falha é um init container
- **THEN** o motivo identifica que se trata de init container e dá o nome dele

#### Scenario: pod sem containerStatuses
- **WHEN** a API retorna um pod sem o campo `status.containerStatuses` (por exemplo, pendente de agendamento)
- **THEN** a linha mostra a fase reportada e reinícios `0`, sem erro e sem linha em branco

### Requirement: Prontidão dos deployments
Para cada Deployment, o sistema SHALL mostrar réplicas prontas sobre desejadas no formato `prontas/desejadas`. `prontas` vem de `status.readyReplicas` e `desejadas` de `spec.replicas`. A ausência de qualquer um dos dois segue o requisito "Campo ausente exibido como valor semântico".

#### Scenario: deployment totalmente pronto
- **WHEN** `status.readyReplicas` é igual a `spec.replicas` (caso `orion-prod/orion-fake-shop`, 2 de 2)
- **THEN** o painel mostra `2/2`

### Requirement: Endpoint dos services via EndpointSlice
Para cada Service, o sistema SHALL determinar endpoints agregando todos os EndpointSlices do mesmo namespace com o rótulo `kubernetes.io/service-name=<nome do Service>`. O sistema SHALL NOT inferir endpoints a partir do `selector` do Service nem ler o recurso `Endpoints`. Cada endereço é contado uma vez, mesmo que apareça em mais de um slice. O resumo exibido SHALL ser um destes, derivado só do que a API reporta:
- `sem endpoint`: nenhum endereço em nenhum slice, inclusive quando não há slice ou quando o slice vem com `endpoints` ausente ou nulo;
- `N endereço(s), M pronto(s)`: há endereços. `M` conta os que têm `conditions.ready: true`.
- Para Service `type: ExternalName`, que não usa endpoints: `ExternalName` e o nome externo.

#### Scenario: service com endereços prontos
- **WHEN** os slices de um Service trazem 2 endereços com `conditions.ready: true` (caso `orion-prod/orion-fake-shop`)
- **THEN** o painel mostra `2 endereços, 2 prontos`

#### Scenario: service com endereços mas nenhum pronto
- **WHEN** os slices de um Service trazem 2 endereços, ambos com `conditions.ready: false` (caso `nyx-prod/nyx-api`)
- **THEN** o painel mostra `2 endereços, 0 prontos` e não mostra `sem endpoint`

#### Scenario: endereços repartidos em vários slices
- **WHEN** os endereços de um Service estão distribuídos em mais de um EndpointSlice
- **THEN** o resumo soma os endereços de todos os slices daquele Service, sem contar duas vezes o mesmo endereço

### Requirement: Eventos recentes do namespace selecionado
Quando um namespace estiver selecionado, o sistema SHALL mostrar os eventos daquele namespace retidos pela API, do mais recente para o mais antigo. Cada objeto Event ocupa uma linha com:
- tipo, razão e mensagem;
- o objeto envolvido (`involvedObject.kind` e `involvedObject.name`);
- `count`, `firstTimestamp` e `lastTimestamp`.

O sistema SHALL NOT desdobrar um evento em várias linhas por causa do seu `count`. Sem namespace selecionado, o bloco de eventos SHALL pedir a seleção de um namespace em vez de listar eventos do cluster inteiro.

#### Scenario: evento repetido
- **WHEN** um Event reporta `count: 429` (caso `BackOff` em `nyx-prod`)
- **THEN** o painel mostra exatamente uma linha para esse evento, com contagem 429, primeira e última ocorrência

#### Scenario: nenhum namespace selecionado
- **WHEN** o filtro está em "todos os namespaces"
- **THEN** o bloco de eventos mostra um aviso pedindo a seleção de um namespace, sem erro

### Requirement: Filtro por namespace e busca por nome
O sistema SHALL permitir filtrar as listas por namespace e buscar por nome. A busca não diferencia maiúsculas de minúsculas, casa por substring e se aplica ao `metadata.name` de pods, deployments e services e ao `involvedObject.name` dos eventos. A busca SHALL atuar sobre a coleta já exibida, sem nova consulta ao cluster e sem mudar o carimbo de hora.

#### Scenario: filtro reduz a lista
- **WHEN** a pessoa seleciona o namespace `nyx-prod`
- **THEN** pods, deployments e services exibidos são apenas os de `nyx-prod`, e o total exibido é menor que o de "todos os namespaces"

#### Scenario: busca reduz a lista
- **WHEN** a pessoa digita `postgres` na busca
- **THEN** permanecem visíveis apenas recursos cujo nome contém `postgres`, e o carimbo de hora da coleta não muda

### Requirement: Coleta sob demanda com carimbo de hora
O sistema SHALL consultar o cluster apenas em resposta a uma ação explícita: abrir o painel, acionar "Atualizar" ou trocar o namespace selecionado (inclusive informando um nome manualmente). O sistema SHALL NOT atualizar por temporizador nem abrir watch. Toda tela com dados SHALL exibir a data e hora da coleta que a produziu, com fuso horário.

#### Scenario: atualização manual
- **WHEN** a pessoa aciona "Atualizar"
- **THEN** o painel faz uma nova coleta, exibe o resultado e mostra o carimbo de hora dessa coleta

#### Scenario: sem atualização em segundo plano
- **WHEN** a pessoa não aciona nenhuma ação
- **THEN** os dados e o carimbo de hora exibidos não mudam, mesmo que o cluster mude

### Requirement: Campo ausente exibido como valor semântico
Quando a API omite um campo por não haver o que reportar, o sistema SHALL exibir o valor semântico correspondente. O sistema SHALL NOT exibir tela em branco, célula vazia ou erro por causa de campo ausente. Os valores mínimos são:
- `readyReplicas` ausente vale 0;
- `spec.replicas` ausente num Deployment vale 1, que é o default da API;
- `endpoints` ausente ou nulo num EndpointSlice vale nenhum endereço;
- `containerStatuses` ausente vale 0 reinícios;
- `count` ausente num evento vale 1;
- `firstTimestamp` ou `lastTimestamp` ausentes são substituídos por `eventTime` ou `series.lastObservedTime` quando existirem, e por `—` caso contrário.

#### Scenario: deployment sem readyReplicas
- **WHEN** o `status` de um Deployment não traz `readyReplicas` e `spec.replicas` é 3 (caso `orion-stg/orion-web`)
- **THEN** o painel mostra `0/3`

#### Scenario: deployment sem spec.replicas e sem readyReplicas
- **WHEN** um Deployment chega sem `spec.replicas` e sem `status.readyReplicas`
- **THEN** o painel mostra `0/1`, nunca `0/None`, `0/` ou `0/null`

#### Scenario: service sem endpoint
- **WHEN** o único EndpointSlice de um Service vem com `endpoints` nulo (caso `nyx-stg/nyx-api`)
- **THEN** o painel mostra `sem endpoint` numa linha normal, sem erro

### Requirement: Apenas o que a API afirma, sem juízo de saúde
O sistema SHALL exibir fase, razões, condições e contagens exatamente como a API reporta. O sistema SHALL NOT exibir rótulo, palavra, ícone ou cor que expresse juízo de saúde não presente na resposta da API, como "saudável", "OK", "healthy" ou um sinal de verificação. Pod pronto, deployment `N/N` ou service com endereços prontos são exibidos como tais, e não como "saudável".

#### Scenario: recurso pronto sem rótulo de saúde
- **WHEN** um pod tem todos os contêineres prontos e um deployment está `2/2`
- **THEN** o painel mostra `Running`, `1/1` e `2/2`, sem nenhum rótulo adicional de saúde

### Requirement: Acesso ao cluster somente leitura
Todo acesso à API do Kubernetes SHALL passar por uma única camada de acesso que só expõe operações de listagem e leitura. O projeto SHALL conter um teste automatizado que falha, apontando arquivo e linha, se aparecer em qualquer arquivo de código do projeto (inclusive na própria camada de acesso) um identificador de operação de escrita ou execução. Isso inclui:
- chamadas `create_*`, `patch_*`, `replace_*`, `delete_*`, `delete_collection_*` e `connect_*`;
- execução de `kubectl` como subprocesso;
- chamada direta de API com métodos POST, PUT, PATCH ou DELETE;
- abertura de watch, seja por `watch.Watch` ou pelo argumento `watch=True` em qualquer chamada.

O servidor HTTP local SHALL aceitar apenas GET e responder 405 a qualquer outro método.

#### Scenario: identificador de escrita introduzido
- **WHEN** uma alteração adiciona, em qualquer arquivo de código, uma chamada como `delete_namespaced_pod`
- **THEN** o teste falha e indica o arquivo e a linha da chamada

#### Scenario: watch introduzido no código
- **WHEN** uma alteração adiciona `watch.Watch()` ou uma chamada de listagem com `watch=True`
- **THEN** o teste falha e indica o arquivo e a linha

#### Scenario: método de escrita no servidor local
- **WHEN** alguém envia POST, PUT, PATCH ou DELETE ao servidor local do painel
- **THEN** o servidor responde 405 e não faz nenhuma chamada ao cluster

### Requirement: ClusterRole de exemplo com privilégio mínimo
O projeto SHALL incluir um ClusterRole de exemplo, com o respectivo binding, que concede apenas os verbos `get`, `list` e `watch`, sem curingas, e apenas sobre os recursos que o painel lê: `namespaces`, `pods`, `services` e `events` no grupo core, `deployments` em `apps` e `endpointslices` em `discovery.k8s.io`. Um teste automatizado SHALL validar essa restrição no arquivo.

O verbo `watch` entra no papel por fazer parte do conjunto canônico de leitura do Kubernetes (o mesmo do papel embutido `view`), e não porque o painel o use. O painel SHALL NOT abrir watch (requisito "Coleta sob demanda com carimbo de hora"). O teste de só leitura SHALL barrar `watch.Watch` e `watch=True` no código, de modo que a presença de `watch` no ClusterRole não contradiz a proibição. O ClusterRole de exemplo SHALL trazer um comentário explicando isso.

#### Scenario: revisão do ClusterRole
- **WHEN** o teste lê o ClusterRole de exemplo
- **THEN** ele passa apenas se todos os verbos pertencem a `{get, list, watch}` e não há `*` em verbos, recursos ou grupos

#### Scenario: watch no papel mas não no código
- **WHEN** o ClusterRole de exemplo concede `watch` e o código do projeto não contém `watch.Watch` nem `watch=True`
- **THEN** o teste do ClusterRole e o teste de só leitura passam. Se qualquer uma das formas de watch for introduzida no código, o teste de só leitura falha, mesmo com o papel inalterado

### Requirement: Servidor local somente em 127.0.0.1
O servidor HTTP do painel SHALL escutar somente no endereço de loopback `127.0.0.1`. O endereço de escuta SHALL NOT ser configurável nesta fatia; apenas a porta pode ser escolhida. O servidor SHALL NOT escutar em `0.0.0.0`, `::` nem em qualquer outra interface.

#### Scenario: endereço de escuta
- **WHEN** o painel é iniciado
- **THEN** o socket do servidor está ligado a `127.0.0.1`, e o endereço de escuta informado pelo processo é `127.0.0.1:<porta>`

#### Scenario: acesso por outra interface
- **WHEN** alguém tenta conectar à porta do painel por outro endereço da máquina, como o IP da rede local
- **THEN** a conexão é recusada

### Requirement: Escape de todo texto vindo da API
Todo texto originado na API do Kubernetes ou no kubeconfig SHALL ser escapado para HTML antes de ir para a página, tanto no corpo quanto em valores de atributos. Isso inclui nomes, namespaces, razões, mensagens de evento e de contêiner, rótulos, nome de contexto e endereço do servidor. O mesmo vale para texto que a pessoa digita e o painel reapresenta, como o namespace informado manualmente. O painel SHALL NOT inserir nenhum desses textos na página como HTML ou script.

#### Scenario: mensagem de evento com script
- **WHEN** um Event tem `message` igual a `<script>alert(1)</script>`
- **THEN** a página mostra o texto literal `<script>alert(1)</script>`, o HTML gerado contém `&lt;script&gt;` e nenhum elemento `<script>` é criado a partir dele

#### Scenario: aspas em valor usado como atributo
- **WHEN** um nome ou rótulo vindo da API contém aspas (`"` ou `'`) e é usado em atributo HTML
- **THEN** as aspas saem escapadas e o atributo não é encerrado nem ganha atributos novos

### Requirement: Aviso de só leitura na tela
O sistema SHALL exibir, em toda tela, inclusive nas telas de erro, um aviso permanente de que o painel é somente leitura e não altera nada no cluster.

#### Scenario: aviso visível em toda tela
- **WHEN** o painel renderiza qualquer tela, inclusive a de cluster que não responde
- **THEN** o aviso de somente leitura está visível

### Requirement: Cenários adversos sem stack trace
O sistema SHALL tratar cada condição abaixo com mensagem própria em linguagem humana, sem stack trace e sem texto bruto de exceção na tela. Qualquer erro não previsto SHALL resultar em mensagem genérica, também sem stack trace, com o detalhe técnico registrado apenas no log local do processo.

#### Scenario: cluster não responde
- **WHEN** o servidor da API do contexto corrente recusa a conexão ou não responde dentro do tempo limite
- **THEN** a tela informa que o cluster não respondeu, com o endereço do servidor e o carimbo de hora da tentativa, sem stack trace

#### Scenario: credencial expirada ou inválida
- **WHEN** o servidor da API rejeita a autenticação (HTTP 401), ou o plugin de credencial do kubeconfig falha ao obter credencial
- **THEN** a tela informa que a credencial foi recusada ou expirou, com texto distinto do de "cluster não respondeu", sem stack trace

#### Scenario: permissão negada para um tipo de recurso
- **WHEN** o servidor da API nega (HTTP 403) a listagem de exatamente um tipo de recurso, por exemplo eventos, e permite os demais
- **THEN** apenas o bloco daquele tipo mostra `sem permissão`, com o recurso negado, e os demais blocos da mesma tela exibem seus dados normalmente

#### Scenario: namespace vazio
- **WHEN** o namespace selecionado existe e não contém pods, deployments nem services (caso `kube-public`)
- **THEN** cada bloco mostra um estado explícito de vazio, visualmente distinto de erro e de `sem permissão`

#### Scenario: kubeconfig sem contexto corrente
- **WHEN** o kubeconfig carregado não tem `current-context` definido
- **THEN** a tela informa que não há contexto corrente configurado e como definir um, sem stack trace e sem tentar nenhuma chamada à API

#### Scenario: kubeconfig inexistente, ilegível ou malformado
- **WHEN** o arquivo de kubeconfig não existe no caminho resolvido (`KUBECONFIG` ou `~/.kube/config`), não pode ser lido, não é YAML válido, ou tem um contexto corrente que aponta para cluster ou usuário que não existe no arquivo
- **THEN** a tela informa que o kubeconfig não pôde ser carregado, indica o caminho tentado e o tipo de problema (inexistente, ilegível ou malformado) sem expor o conteúdo do arquivo, usa texto distinto de "sem contexto corrente", não mostra stack trace e não tenta nenhuma chamada à API
