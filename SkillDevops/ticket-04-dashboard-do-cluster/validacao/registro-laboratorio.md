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
- **Confirmação visual (captura das 22:12:07):** com o filtro `nyx-prod` e a
  busca `postgres`, a tela mostra Pods **1 de 3**, Deployments **1 de 2**,
  Services **1 de 2** e Eventos de `nyx-prod` **4 de 20**. A lista encolheu em
  cada bloco e o horário da coleta permaneceu `27/09/2026 22:12:07`.
  [CONFIRMAR: o horário era o mesmo antes de digitar `postgres`.]

## Cenários adversos

| Tarefa | Kubeconfig usado | Título na tela | Stack trace | Listagens tentadas |
|---|---|---|---|---|
| 8.3 | servidor `https://127.0.0.1:1` | O cluster não respondeu (cita servidor e horário) | não | 1 |
| 8.4 | token inválido (HTTP 401) | Credencial recusada ou expirada | não | 1 |
| 8.5 | ServiceAccount de `deploy/lab/sem-eventos.yaml`, contexto `painel`, namespace `nyx-prod` | bloco de eventos com `sem permissão`; pods, deployments e services com dados [CONFIRMAR: texto exato do bloco e contagens] | não | — |
| 8.6 | normal, namespace `kube-public` | cada bloco em estado vazio (`estado vazio`), sem erro | não | — |
| 8.7 | sem `current-context` | Nenhum contexto corrente no kubeconfig | não | 0 |
| 8.8 | caminho inexistente | Não foi possível carregar o kubeconfig: arquivo inexistente | não | 0 |
| 8.8 | YAML quebrado | Não foi possível carregar o kubeconfig: arquivo malformado | não | 0 |
| 8.9 | ServiceAccount de `deploy/lab/so-um-namespace.yaml`, contexto `painel` com `namespace: nyx-prod` | seletor com `sem permissão para listar namespaces` (aviso também no bloco Namespaces); `nyx-prod` pré-selecionado; pods, deployments, services e eventos de `nyx-prod` exibidos | não | — |

O aviso de somente leitura estava presente em todas as telas acima.

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
