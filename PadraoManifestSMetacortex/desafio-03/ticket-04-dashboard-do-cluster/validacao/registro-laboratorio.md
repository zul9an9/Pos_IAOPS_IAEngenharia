# Registro de validação: cluster kind do laboratório

- **Data:** 2026-09-27, cerca de 20:10 a 20:20 (UTC-3), e complemento à noite
  (cenários 8.2, 8.5 e 8.9, captura das 22:12:07).
- **Contexto:** `kind-metacortex-lab`, servidor Kubernetes v1.37.0.
- **Painel:** `python -m painel_cluster`, Python 3.14.6, cliente `kubernetes` 36.0.3.
- **Escrita no cluster:** nenhuma. O painel só lista. As fixtures foram
  capturadas só com `kubectl get` (`tests/fixtures/capturar.sh`).
- **Cenários adversos:** usaram cópias de kubeconfig no diretório temporário
  da sessão, apagadas ao final. O kubeconfig real não foi alterado.

## 8.1 Critérios de aceite na tela

**nyx-prod, pods:**

| Namespace | Nome | Fase | Prontos | Reinícios | Motivo |
|---|---|---|---|---|---|
| nyx-prod | nyx-api-7665bb6885-57f5b | Running | 0/1 | 163 | CrashLoopBackOff; última terminação: OOMKilled (exit 137) |
| nyx-prod | nyx-api-7665bb6885-rc6vw | Running | 0/1 | 164 | CrashLoopBackOff; última terminação: OOMKilled (exit 137) |
| nyx-prod | nyx-postgres-5f5f4d5847-vdl55 | Running | 1/1 | 1 | última terminação: Unknown (exit 255) |

**orion-stg, deployments:**

| Nome | Prontas/desejadas |
|---|---|
| orion-postgres | 1/1 |
| orion-web | **0/3** (o `status` não traz `readyReplicas`) |

**Services:**

| Service | Endpoint |
|---|---|
| nyx-stg/nyx-api | **sem endpoint** |
| orion-prod/orion-fake-shop | **2 endereços, 2 prontos** |
| nyx-prod/nyx-api | 2 endereços, 0 prontos |

**nyx-prod, eventos:** uma linha por objeto Event.

| Última | Primeira | Contagem | Tipo | Razão | Objeto |
|---|---|---|---|---|---|
| 2026-09-27T23:11:41Z | 2026-09-27T14:11:28Z | 467 | Warning | BackOff | Pod nyx-api-7665bb6885-rc6vw |
| 2026-09-27T23:06:47Z | 2026-09-27T14:11:29Z | 466 | Warning | BackOff | Pod nyx-api-7665bb6885-57f5b |

Também aparecem Pulled (109 e 108) e Created (107).

## 8.2 Filtro e busca

- **Filtro:**
  - "todos os namespaces" mostra 25 pods, 10 deployments e 12 services;
  - `nyx-prod` mostra 3 pods, 2 deployments e 2 services.
- **Busca:** roda no navegador sobre a coleta exibida. O campo de busca não
  pertence ao formulário e não tem `name`, e o script não faz requisições nem
  usa temporizadores. Isso é coberto por teste automatizado.
- **Confirmação visual:** com o filtro `nyx-prod` e a busca `postgres`, a tela
  mostra Pods **1 de 3**, Deployments **1 de 2**, Services **1 de 2** e Eventos
  de `nyx-prod` **4 de 20**. A lista encolheu em cada bloco, e a busca alcança
  os eventos pelo nome do objeto envolvido.
- **Carimbo de hora da coleta:**
  - **Antes de digitar `postgres`:** a coleta exibida era a do cenário 8.9, com
    o carimbo `27/09/2026 22:12:07`, lido na tela daquela sessão.
  - **Depois de digitar `postgres`:** o print da busca saiu com o cabeçalho
    cortado, então o horário **não aparece nessa captura**. O registro não
    afirma, por observação, que ele permaneceu `22:12:07`.
  - **O que sustenta que a busca não coleta:** não depende dessa observação.
    A busca é do navegador: o campo não pertence ao formulário e não tem `name`,
    e o script não faz requisições nem usa temporizadores. Isso é coberto por
    `test_busca_filtra_no_navegador_sem_nova_coleta`, e o servidor só coleta num
    `GET /` (`test_get_faz_uma_coleta_e_envia_csp`).
  - **Para fechar a observação** (repetível a qualquer momento, com qualquer
    coleta): abrir o painel, anotar o horário do cabeçalho, digitar `postgres`
    na busca e conferir que o horário continua o mesmo.

## Cenários adversos

| Tarefa | Kubeconfig usado | Título na tela | Stack trace | Listagens tentadas |
|---|---|---|---|---|
| 8.3 | servidor `https://127.0.0.1:1` | O cluster não respondeu (cita servidor e horário) | não | 1 |
| 8.4 | token inválido (HTTP 401) | Credencial recusada ou expirada | não | 1 |
| 8.5 | ServiceAccount de `deploy/lab/sem-eventos.yaml`, contexto `painel`, namespace `nyx-prod` | bloco "Eventos de nyx-prod" com **`sem permissão para listar eventos`**; Pods (3), Deployments e Services com dados (ver "Detalhe do 8.5") | não | — |
| 8.6 | normal, namespace `kube-public` | cada bloco em estado vazio (`estado vazio`), sem erro | não | — |
| 8.7 | sem `current-context` | Nenhum contexto corrente no kubeconfig | não | 0 |
| 8.8 | caminho inexistente | Não foi possível carregar o kubeconfig: arquivo inexistente | não | 0 |
| 8.8 | YAML quebrado | Não foi possível carregar o kubeconfig: arquivo malformado | não | 0 |
| 8.9 | ServiceAccount de `deploy/lab/so-um-namespace.yaml`, contexto `painel` com `namespace: nyx-prod` | seletor com `sem permissão para listar namespaces` (aviso também no bloco Namespaces); `nyx-prod` pré-selecionado; pods, deployments, services e eventos de `nyx-prod` exibidos | não | — |

O aviso de somente leitura estava presente em todas as telas acima.

### Detalhe do 8.5 (permissão negada para um tipo de recurso)

A ServiceAccount `painel-sem-eventos` tem um ClusterRole igual ao de exemplo,
**sem `events`** (`deploy/lab/sem-eventos.yaml`). Com `nyx-prod` selecionado, o
painel mostrou o bloco de eventos negado e os outros blocos com dados.

| Item | Tela do laboratório, 2026-09-27 (transcrição do print) | Reprodução offline (`reproducao-8-5.py`) |
|---|---|---|
| Bloco de eventos | `sem permissão para listar eventos` | `Eventos de nyx-prod` + `sem permissão para listar eventos`, seguido da nota de retenção de eventos |
| Pods | 3 linhas; `nyx-api` em `CrashLoopBackOff`, última terminação `OOMKilled` (exit 137), 188 reinícios | 3 linhas; mesmos estado e motivo, com 162 reinícios (valor da fixture congelada) |
| Deployments | `nyx-api` `0/2` | 2 linhas: `nyx-api` `0/2` e `nyx-postgres` `1/1` |
| Services | `nyx-api` `2 endereços, 0 prontos` | 2 linhas: `nyx-api` `2 endereços, 0 prontos` e `nyx-postgres` `1 endereço, 1 pronto` |
| Erro global, stack trace | nenhum | nenhum |

- **O texto do bloco** é o que o código gera para um 403 de usuário autenticado
  numa listagem de eventos (`sem permissão para listar` + o recurso traduzido
  para `eventos`, em `render.py`). A transcrição da tela e a reprodução coincidem.
- **As contagens** de Deployments (2) e Services (2) vêm da reprodução, que usa
  as mesmas listagens, e coincidem com o filtro `nyx-prod` do 8.2 (3 pods, 2
  deployments, 2 services). A transcrição da tela citou os objetos `nyx-api` e a
  contagem de pods, não as contagens de Deployments e Services.
- **Os reinícios** diferem de propósito: a tela mostra o valor vivo (188), e a
  fixture, o valor de quando foi capturada (162). É o motivo de os testes
  verificarem a fixture congelada e de este registro anotar os valores vivos.
- **A negação no apiserver** é consequência do papel: o ClusterRole de
  `sem-eventos.yaml` lista `namespaces`, `pods`, `services`, `deployments` e
  `endpointslices`, e não `events`. A sessão registrou o `Forbidden` ao listar
  eventos para `system:serviceaccount:painel-cluster:painel-sem-eventos`. Para
  repetir a checagem:

  ```bash
  kubectl auth can-i list events -n nyx-prod \
    --as=system:serviceaccount:painel-cluster:painel-sem-eventos      # no
  kubectl auth can-i list pods -n nyx-prod \
    --as=system:serviceaccount:painel-cluster:painel-sem-eventos      # yes
  ```

A reprodução offline **não substitui** a validação no cluster: ela confere o
texto e as contagens que o código produz, e o cluster vivo é a validação final.

## 8.10 Endereço de escuta

```
netstat -ano | grep :8765
  TCP    127.0.0.1:8765         0.0.0.0:0              LISTENING       17688
```

Conexão a `http://192.168.0.81:8765`, o IP da rede local da máquina, foi
recusada com `ConnectionRefusedError`.

## 8.11 Suíte automatizada

Resultado: `158 passed`. A saída completa está em
[`pytest-2026-09-27.txt`](pytest-2026-09-27.txt).

Entre os testes que passaram:
- `test_somente_leitura.py`: varredura do projeto e seis arquivos plantados
  (escrita, `watch.Watch`, `watch=True`, `kubectl`, `call_api` POST e import);
- `test_rbac.py`;
- testes de escape em `test_render.py`;
- `test_nenhum_termo_de_juizo_de_saude`.

## Origem e limites das evidências

| Evidência | Onde está | Observação |
|---|---|---|
| Tabelas do 8.1, 8.3 a 8.10 | Este registro | Transcritas das telas da sessão de 2026-09-27 |
| Suíte automatizada (8.11) | `pytest-2026-09-27.txt` | 158 testes. Repetida em 2026-11-08, em Linux com Python 3.12.3: 158 passed |
| Texto e contagens do 8.5 | `reproducao-8-5.py` e `reproducao-8-5.txt` | Reprodução offline com o código e as fixtures. A tela do laboratório está transcrita acima |
| **Capturas de tela** dos cenários 8.2, 8.5 e 8.9 | **Não estão no repositório** | Os prints foram tirados na sessão, e as tabelas deste registro são a transcrição deles. Se forem anexados, o lugar previsto é `validacao/evidencias/` |
| Observação do carimbo de hora depois da busca (8.2) | **Em aberto** | Ver o 8.2. O critério é sustentado por teste, e a observação pode ser repetida a qualquer momento |
