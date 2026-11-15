# Design

## Context

A motivação está em `proposal.md` (Why) e os requisitos em `specs/cluster-dashboard/spec.md`.

- **Projeto:** novo, sem código nem specs existentes.
- **Única dependência externa:** o cluster alcançado pelo contexto corrente do kubeconfig.
- **Cluster do laboratório:**
  - kind, contexto `kind-metacortex-lab`;
  - servidor v1.37.0, em que `Endpoints` já está depreciado (desde a 1.33) e `EndpointSlice` é a API estável;
  - Python local 3.14.

Restrições que moldam as decisões:
- somente o contexto corrente;
- coleta só sob demanda;
- nenhuma escrita;
- a API omite campos em vez de mandá-los vazios, como a coleta de 2026-09-27 mostrou: `orion-stg/orion-web` sem `readyReplicas` e `nyx-stg/nyx-api` com EndpointSlice `endpoints: null`.

## Goals / Non-Goals

**Goals:**
- Garantia de só leitura verificável por máquina, e não só por promessa. Ela tem três camadas independentes (D5) e é exposta na tela.
- Tradução da resposta da API para a tela num único ponto testável, com dados reais capturados do cluster como fixtures. Assim, as três armadilhas de dados viram testes unitários determinísticos, e não só verificação manual.

**Non-Goals (de design, além do escopo da proposta):**
- Persistência. Cada coleta vive só na memória do processo até a próxima coleta; nada é gravado em disco.
- Autenticação do próprio painel. Ele escuta só em `127.0.0.1`, garantia que está na spec. A fronteira de confiança é "quem tem shell nesta máquina já tem o kubeconfig", e o painel não cria uma fronteira nova.
- Empacotamento e distribuição (pip, script único, imagem). Fica adiado.

## Decisions

### D1: Python 3 com HTML servido localmente. Descartados Go e TUI
Python tem o cliente oficial com autenticação de kubeconfig completa (D2) e é a linguagem que o time já usa nos outros tickets. O HTML aproveita o navegador que já está aberto e comporta tabelas largas (pod, fase, prontos, reinícios, motivo) sem o limite de colunas do terminal. Uma página também pode ser capturada e colada no chamado.

O servidor usa `http.server` da biblioteca padrão, ligado fixo em `127.0.0.1` (requisito "Servidor local somente em 127.0.0.1"; só a porta é parâmetro). O HTML é gerado no servidor, e todo texto externo passa por `html.escape(..., quote=True)`, que cobre corpo e atributos (requisito "Escape de todo texto vindo da API"). Mensagens de evento são texto controlado por terceiros. O escape acontece num único ponto: o renderizador recebe só texto cru e é a única parte que monta HTML.

- **Descartado: Go.** O `client-go` é equivalente em capacidade, mas acrescenta uma segunda linguagem e toolchain para uma ferramenta de uma pessoa, sem ganho de comportamento.
- **Descartado: TUI.** Abre mais rápido e dispensa navegador. Por outro lado, quatro tabelas largas e filtráveis mais eventos cabem mal num terminal de largura fixa, e uma tela de terminal não vira anexo de chamado com a mesma facilidade.

### D2: Cliente oficial do Kubernetes para Python. Descartados kubectl como subprocesso e HTTP direto no apiserver
Autenticar a partir de kubeconfig não é só "um token". Envolve certificado de cliente, bearer token, CA do servidor, OIDC e plugins `exec` (comuns em clusters gerenciados). O cliente oficial implementa tudo isso com o mesmo comportamento do `kubectl`, e reimplementar essa autenticação é complexo demais.

- **Descartado: `kubectl` como subprocesso.** Transforma a saída do `kubectl` num contrato não oficial, exige o binário instalado, cria um processo por chamada e dificulta a agregação de EndpointSlices por Service (D4). Pior para o invariante: um subprocesso `kubectl` aceita qualquer verbo, inclusive de escrita, e escapa da camada única de acesso. Por isso o teste de D5 proíbe `kubectl` como subprocesso.
- **Descartado: HTTP direto no apiserver.** É a menor dependência, mas obriga a reimplementar a autenticação de kubeconfig (certificados, plugins `exec`, validação de CA), justamente o código sensível e fácil de errar que esta decisão evita.

### D3: Atualização sob demanda com carimbo de hora da coleta. Descartados polling e watch
Durante um chamado, a pessoa precisa de um retrato estável para ler, não de uma tela que se rearranja enquanto ela lê. Cada coleta é um conjunto finito de chamadas `list` pedido explicitamente, e o carimbo de hora torna auditável "de quando é isto". São gatilhos de coleta: abrir o painel, clicar em "Atualizar" e trocar o namespace, porque os eventos dependem do namespace. A busca por nome filtra a coleta atual no navegador e não é gatilho. Um namespace digitado manualmente, quando a listagem de namespaces é negada, é gatilho como qualquer troca de namespace, depois de validado como rótulo DNS-1123.

Uma coleta faz:
- listagem de namespaces;
- listagem de pods, deployments, services e endpointslices em todos os namespaces, ou no namespace selecionado;
- listagem de eventos do namespace selecionado, se houver um.

Cada listagem é independente, para que a falha de uma não derrube as outras (D6).

- **Descartado: polling.** Gera carga contínua no apiserver sem benefício numa sessão curta de triagem, e ainda precisaria de carimbo de hora para responder "isto é atual?". A essa altura, não ganha nada sobre o sob demanda.
- **Descartado: watch.** Uma conexão longa tende a ficar obsoleta em silêncio justamente quando cluster ou rede estão ruins, que é a situação sob diagnóstico. Também exige manter um estado reconciliado em memória: mais código e mais pontos para erros do tipo "ausente significa o quê", numa fatia que exclui histórico. O teste de D5 também proíbe `watch.Watch` e o argumento `watch=True` no código, para que a decisão não regrida.

### D4: EndpointSlice agregado por `kubernetes.io/service-name`. Descartados Endpoints e inferência pelo selector
`Endpoints` está depreciado desde a 1.33. O laboratório já roda 1.37, então construir sobre `Endpoints` dá ao painel prazo de validade curto. `EndpointSlice` é a escolha durável. Como um Service pode ter vários slices, a coleta lista os EndpointSlices e agrupa pelo rótulo `kubernetes.io/service-name`. O resumo conta endereços únicos e, separadamente, os que têm `conditions.ready: true`.

Esse desenho responde a um caso real encontrado no laboratório. `nyx-prod/nyx-api` tem 2 endereços, ambos com `ready: false`. Um resumo booleano "tem endpoint: sim" afirmaria algo que a API não afirma: a armadilha (c). Por isso a spec define três saídas: `sem endpoint`, `N endereços, M prontos` e `ExternalName`.

- **Descartado: `Endpoints`.** Funciona hoje e é um objeto por Service, o que é mais simples. Mas está em depreciação, e é a base errada para uma fatia que será estendida, não substituída. Além disso, `Endpoints` sem endereço simplesmente não traz `subsets`: a mesma armadilha de ausência, com vida útil menor.
- **Descartado: inferir pelo `selector` do Service.** Reimplementa o controlador de endpoints (readiness, terminating, portas nomeadas, Services sem selector) e pode divergir do que o plano de controle publica. É o mesmo tipo de erro que "juízo inventado" proíbe. Ler o objeto que o plano de controle já calcula é mais simples e correto por construção. No caso `nyx-stg` (selector `app=nyx-api` e pods `app=nyxapi`), o slice publicado diz exatamente `endpoints: null`.

### D5: Garantia de só leitura em três camadas. Descartados só RBAC e só revisão de código
1. **Camada única de acesso.** Um módulo, e só ele, importa o cliente `kubernetes`. Ele expõe apenas estas funções de leitura:
   - `list_namespace`;
   - `list_pod_for_all_namespaces` / `list_namespaced_pod`;
   - `list_deployment_for_all_namespaces` / `list_namespaced_deployment`;
   - `list_service_for_all_namespaces` / `list_namespaced_service`;
   - `list_endpoint_slice_for_all_namespaces` / `list_namespaced_endpoint_slice`;
   - `list_namespaced_event`.
2. **Teste estático.** O teste percorre com `ast` todos os `.py` do projeto, inclusive a camada de acesso, exceto o próprio arquivo de teste. Ele falha, com arquivo e linha, quando encontra:
   - atributo chamado com prefixo `create_`, `patch_`, `replace_`, `delete_` ou `connect_` (`connect_*` cobre exec, attach, port-forward e proxy);
   - uso de `kubernetes.stream`, `watch.Watch`, argumento nomeado `watch=True` em qualquer chamada, ou `call_api`/`request` com método de escrita. `watch=True` num `list_*` abre watch sem passar por `watch.Watch`, por isso é barrado à parte;
   - `subprocess` invocando `kubectl`;
   - import do cliente `kubernetes` fora da camada de acesso.

   Um segundo teste confirma que a camada exporta exatamente a lista permitida. Um terceiro planta um arquivo com `delete_namespaced_pod` num diretório temporário e exige que o scanner o detecte, para provar que o teste não passa por vacuidade.
3. **RBAC de exemplo.** ClusterRole só com `get`/`list`/`watch` nos recursos listados na spec. Com o painel rodando sob esse papel, um erro que escape das camadas 1 e 2 é negado pelo próprio apiserver. `watch` entra no papel porque faz parte do conjunto de leitura canônico, o mesmo do papel embutido `view`. Isso não contradiz D3: o papel diz o que a credencial *poderia* ler, e o teste da camada 2 garante que o código *não* abre watch. A spec torna isso explícito no requisito do ClusterRole, e o YAML traz um comentário com a mesma explicação.

Somam-se a isso o servidor local, que aceita só GET e escuta só em `127.0.0.1`, e o aviso permanente na tela, que tornam o invariante visível também para quem usa.

- **Descartado: só RBAC.** É defesa real, mas não quebra o build. A regressão chega silenciosa a quem roda com o próprio kubeconfig de plantão, geralmente com privilégio amplo, que é o caso comum.
- **Descartado: só revisão de código.** É processo humano, não é automatizável nem "visível no projeto". Um revisor cansado não pega um `patch_` perdido numa função auxiliar.

### D6: Erros classificados por bloco, com mensagem por categoria. Descartados propagar a exceção e uma única tela de erro global
Cada listagem da coleta é executada e classificada isoladamente. O resultado de um bloco é "dados", "vazio" ou um erro classificado:

| Origem | Categoria | Onde aparece |
|---|---|---|
| kubeconfig inexistente, ilegível, YAML inválido, ou contexto corrente apontando para cluster/usuário ausente (detectado antes de qualquer chamada; a mensagem cita o caminho e o tipo, nunca o conteúdo) | `kubeconfig-invalido` | tela inteira |
| kubeconfig sem `current-context` (detectado antes de qualquer chamada) | `sem-contexto` | tela inteira |
| conexão recusada, DNS, TLS de servidor, timeout (connect 3 s, read 10 s, sem retentativas) | `nao-respondeu` | tela inteira |
| HTTP 401; falha de plugin `exec`; certificado de cliente expirado; HTTP 403 cujo sujeito é `system:anonymous` (credencial que não autenticou) | `credencial` | tela inteira |
| HTTP 403 de usuário autenticado | `sem-permissao` | só o bloco |
| lista vazia com HTTP 200 | `vazio` | só o bloco |
| qualquer outra exceção | `inesperado` (mensagem genérica, detalhe só no log local) | só o bloco |

Quando todas as listagens caem em `nao-respondeu` ou `credencial`, a tela inteira mostra essa mensagem.

A listagem de namespaces é um caso especial. O 403 nela não vira bloco de erro: degrada o seletor para `sem permissão para listar namespaces` com campo de digitação, pré-preenchido com o `namespace` do contexto corrente quando existir. Com esse namespace, a coleta passa a usar só as listagens por namespace. Isso atende a credencial restrita a um namespace, que de outro modo teria 403 também em todas as listagens de "todos os namespaces". `nao-respondeu` e `credencial` são textos diferentes. Nenhuma exceção chega ao HTML: o renderizador recebe só categoria e dados.

- **Descartado: deixar a exceção propagar até o servidor HTTP.** Produz stack trace ou página 500 genérica. É exatamente o que a spec proíbe.
- **Descartado: uma tela de erro global para qualquer falha.** Um 403 em eventos esconderia pods e deployments, violando "o resto da tela funciona".

### D7: Tradução API → tela num único módulo puro, testado com fixtures reais. Descartados tratar ausência no template e testar só contra o cluster vivo
Um módulo sem I/O recebe os objetos da API e devolve linhas prontas para exibir. As três armadilhas vivem só nele:
- (a) valores semânticos de campo ausente, inclusive `spec.replicas` ausente → 1, para que nunca saia `0/None`;
- (b) um evento, uma linha, com `count` e carimbos (com fallback para `eventTime`/`series` quando os campos legados faltam);
- (c) só campos reportados, sem juízo de saúde.

As fixtures são capturadas do laboratório com `kubectl get -o json`, uma operação de leitura, e versionadas em `tests/fixtures/`. Os casos: `nyx-prod` (CrashLoopBackOff, OOMKilled, 155 reinícios, evento `count` 429), `orion-stg` (0/3 sem `readyReplicas`), `nyx-stg` (`endpoints: null`), `orion-prod` (2 prontos) e o slice de `nyx-prod` (2 endereços, 0 prontos).

- **Descartado: tratar ausência no template HTML.** Espalha `if campo existe` pela apresentação, com um lugar diferente para errar em cada coluna, e é difícil de testar sem renderizar.
- **Descartado: testar só contra o cluster vivo.** O estado do laboratório muda: `orion-prod` foi corrigido hoje e `nyx-prod` pode ser corrigido amanhã. Critério de aceite que depende de estado mutável não é reproduzível. O cluster vivo continua sendo a validação final (tarefas do grupo 8), mas não o único teste.

## Risks / Trade-offs

- **[Risco] Credencial ampla derruba a camada 3.** Com o kubeconfig pessoal, geralmente administrativo, o RBAC não impede uma escrita que escape das camadas 1 e 2. → **Mitigação:** as camadas 1 e 2 valem para qualquer credencial. A documentação explica como gerar um contexto dedicado ligado ao ClusterRole de exemplo.
- **[Risco] 403 anônimo confundido com falta de permissão.** Com `anonymous-auth` ligado, credencial inválida pode virar 403 `system:anonymous` em vez de 401. → **Mitigação:** a classificação de D6 trata esse caso como `credencial`, e ele é coberto por teste unitário.
- **[Risco] Listagem em todos os namespaces exige permissão de cluster.** Quem tem só papéis por namespace recebe 403 no modo "todos" e na listagem de namespaces. → **Mitigação:** comportamento definido na spec (requisito "Lista de namespaces"). O seletor degrada para digitação, com o namespace do contexto pré-selecionado, e a coleta passa a ser por namespace (D6). Validado no laboratório com Role restrita a `nyx-prod`.
- **[Risco] Nome de namespace digitado usado como vetor.** O nome vai para a URL da API e volta para a página. → **Mitigação:** validação DNS-1123 antes de qualquer chamada, mais o escape de D1 ao reapresentá-lo.
- **[Risco] Cluster grande.** Listar tudo em todos os namespaces pode ser pesado. → **Mitigação:** a coleta é sob demanda e só quando pedida, e a listagem é paginada (`limit`/`continue`). Um limite superior de exibição com aviso "mostrando X de Y" fica como ajuste de implementação.
- **[Risco] Eventos expiram.** O TTL padrão é de 1 h, então "recentes" é o que a API ainda retém. → **Mitigação:** a tela diz isso junto ao bloco. Histórico está fora de escopo.
- **[Risco] Compatibilidade do cliente `kubernetes` com Python 3.14.** → **Mitigação:** fixar a versão do cliente e validar a instalação logo na tarefa 1.1. Se houver incompatibilidade, usar o Python 3.12 ou 3.13 disponível.
- **[Trade-off] Tela estática pode ser tomada por atual.** O painel sob demanda pode ficar aberto e desatualizado. → **Mitigação:** carimbo de hora sempre visível no cabeçalho, sem temporizador escondido que desfaria D3.

## Migration Plan

Projeto novo: não há migração, usuários existentes nem nada implantado no cluster.

1. Montar o projeto, a camada de acesso e os testes de só leitura antes de qualquer tela, para que tudo seja construído sobre a fronteira já garantida.
2. Capturar as fixtures do laboratório (só leitura) e implementar o módulo de tradução com testes.
3. Implementar a coleta com classificação de erros, o servidor local só-GET e as telas.
4. Escrever o ClusterRole de exemplo e os manifestos de laboratório para testar permissão parcial (sem eventos, e credencial restrita a um namespace). **Quem opera os aplica com `kubectl`. O painel e esta change não aplicam nada.**
5. Validar contra o laboratório.

Reversão: basta não executar o painel. Ele não guarda estado no cluster nem no disco.

## Open Questions

- Porta padrão do servidor local. Não altera spec, abordagem nem tarefas, e pode ser escolhida na implementação, com opção de linha de comando.
