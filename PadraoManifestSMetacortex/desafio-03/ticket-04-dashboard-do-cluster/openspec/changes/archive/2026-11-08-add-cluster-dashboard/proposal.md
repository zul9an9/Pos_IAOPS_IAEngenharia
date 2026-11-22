# Proposta

## Why

Os primeiros dez minutos de um chamado de Kubernetes vão embora rodando sempre os mesmos `kubectl get`/`describe`, namespace por namespace, só para montar o quadro do que está quebrado. Um painel local, só de leitura, que lê o contexto corrente do kubeconfig e mostra esse quadro sob demanda, com carimbo de hora, elimina esse reconhecimento manual. E faz isso sem abrir nenhum caminho de escrita no cluster do cliente.

## What Changes

- Nova aplicação local (Python 3, HTML servido em `127.0.0.1`) que roda na máquina de quem opera, lê o kubeconfig e usa **somente o contexto corrente**. Não há troca de contexto nem multicluster.
- O painel mostra:
  - namespaces;
  - pods, com estado, contagem de reinícios e motivo quando em falha (inclusive de init containers);
  - deployments, com prontos/desejados;
  - services, dizendo se têm endpoint (via EndpointSlice);
  - eventos recentes do namespace selecionado.
- Filtro por namespace e busca por nome. A busca filtra a coleta já feita e não consulta o cluster de novo. Se a credencial não puder listar namespaces (caso típico de credencial restrita a um namespace), o seletor diz isso e aceita o nome digitado, já preenchido com o namespace do contexto quando houver. O filtro nunca fica inutilizável.
- Coleta **sob demanda**: só quando a pessoa pede (botão "Atualizar" ou troca de namespace). Toda tela exibe o carimbo de hora da coleta. Não há polling nem watch.
- Tratamento explícito de três armadilhas de dados da API:
  - **(a) Campo ausente não é campo vazio.** Deployment sem `readyReplicas` aparece como "0/N", e sem `spec.replicas` o N vale 1, o default da API. Service cujos EndpointSlices não trazem `endpoints` aparece como "sem endpoint". Pod sem `containerStatuses` aparece com 0 reinícios. Nunca tela em branco nem erro.
  - **(b) Evento é objeto próprio.** Cada evento aparece em uma linha, ligado ao `involvedObject`, com `count`, `firstTimestamp` e `lastTimestamp`. Um evento com `count` 21 é uma linha que diz 21, não 21 linhas.
  - **(c) "Pronto" não é "saudável".** O painel reproduz o que a API afirma (fase, razões, condições de endpoint `ready`) e não sintetiza juízo de saúde.
- Invariante **SÓ LEITURA**, visível no projeto em quatro lugares:
  - camada única de acesso ao cluster, só com operações de listagem/leitura;
  - teste automatizado que falha se aparecer identificador de escrita, ou abertura de watch, em qualquer lugar do código;
  - ClusterRole de exemplo só com `get`/`list`/`watch`. O `watch` entra por ser parte do conjunto canônico de leitura; o código não o usa e o teste o barra;
  - aviso permanente na tela.
- Duas garantias de segurança do próprio painel, verificáveis por teste:
  - o servidor escuta **somente em `127.0.0.1`**;
  - **todo texto vindo da API** (e do kubeconfig) é escapado antes de ir para o HTML.
- Os cinco cenários adversos obrigatórios, mais um sexto (kubeconfig inexistente, ilegível ou malformado), cada um com mensagem própria em tela e sem stack trace:
  - cluster não responde;
  - credencial expirada ou inválida (mensagem distinta de "não respondeu");
  - permissão negada para um tipo de recurso (só aquele bloco mostra "sem permissão", o resto funciona);
  - namespace vazio (distinto de erro);
  - kubeconfig sem contexto corrente;
  - kubeconfig inexistente, ilegível ou malformado (mensagem distinta de "sem contexto corrente").
- **Fora de escopo nesta fatia:** logs, métricas de consumo, histórico, multicluster e qualquer escrita no cluster.

## Capabilities

### New Capabilities
- `cluster-dashboard`: painel local e só de leitura para o contexto corrente do kubeconfig. Mostra namespaces, pods, deployments, services (endpoint via EndpointSlice) e eventos do namespace selecionado. Inclui filtro (com alternativa quando namespaces não podem ser listados), busca e coleta sob demanda com carimbo de hora. Trata explicitamente campos ausentes, eventos agregados e "pronto ≠ saudável", tem garantia de só leitura verificável, escuta só em 127.0.0.1, escapa todo texto externo e define o comportamento dos cenários adversos.

### Modified Capabilities
_Nenhuma: projeto novo, sem specs existentes._

## Impact

- **Código novo:** aplicação Python 3 usando o cliente oficial `kubernetes` para acesso e autenticação via kubeconfig, mais um servidor HTTP local que renderiza HTML no servidor. Não há build de frontend.
- **Artefato RBAC novo:** ClusterRole de exemplo (e binding) só com `get`/`list`/`watch`, para quem opera revisar e aplicar. Esta change não aplica nada no cluster.
- **Sistemas existentes:** nenhum impacto. O painel não altera estado do cluster e não é implantado como workload.
- **Alvo de validação:** cluster kind do laboratório, contexto `kind-metacortex-lab`, servidor v1.37.0. Estado conferido em modo leitura (`kubectl get`) em 2026-09-27. **Os cenários de aceite já existem no cluster e não precisam ser provisionados:**
  - `nyx-prod`: pods `nyx-api-*` com `waiting.reason: CrashLoopBackOff`, 155 reinícios cada, última terminação `OOMKilled` (exit 137). A `phase` segue `Running`, o que demonstra que o estado precisa vir dos containers e não só da fase.
  - `orion-stg`: Deployment `orion-web` 0/3. O `status` não traz `readyReplicas` nem `availableReplicas`. Os pods estão em `ImagePullBackOff`.
  - `nyx-stg`: Service `nyx-api` sem endpoint. O EndpointSlice existe com `endpoints: null`, porque o selector do Service (`app=nyx-api`) não casa com os pods (`app=nyxapi`).
  - `orion-prod`: Service `orion-fake-shop` com 2 endereços prontos.
  - `nyx-prod`: Service `nyx-api` tem 2 endereços com `ready: false`. É um terceiro estado, "tem endereço, nenhum pronto", tratado explicitamente na spec.
  - `nyx-prod`: eventos `BackOff` com `count` 429 e 427.
  - `kube-public`: existe e está vazio, servindo de caso de namespace vazio.
- **Correção em relação à versão anterior desta proposta:** a versão anterior dizia que `nyx-prod`, `nyx-stg` e `orion-stg` "não estão presentes no cluster hoje" e previa provisioná-los. Isso era falso: os três existem, nos estados acima. A tarefa de provisionar foi removida, porque seria escrita no cluster sem necessidade.
