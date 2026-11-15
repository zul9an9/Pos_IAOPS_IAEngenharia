# ADR-0004 — EndpointSlice agregado por Service

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `design.md` D4; `CURADORIA.md` §3.5. O prompt do `/opsx:propose` pedia para decidir entre `Endpoints` e EndpointSlice, "com viés para EndpointSlice por durabilidade", e a escolha foi fechada no design |
| **Relacionados** | [ADR-0007](ADR-0007-traducao-em-modulo-puro-com-fixtures-reais.md) |

## Contexto

O painel precisa dizer se um Service **tem endpoint**. Duas coisas pesam:

- `Endpoints` está **depreciado desde a 1.33**, e o laboratório já roda a 1.37, então construir
  sobre ele dá ao painel um prazo de validade curto. `EndpointSlice` é a API estável.
- Um caso real encontrado no laboratório: **`nyx-prod/nyx-api` tem 2 endereços, ambos com
  `ready: false`.** Um resumo booleano "tem endpoint: sim" afirmaria algo que a API não afirma, a
  armadilha "pronto não é saudável".

## Decisão

Listar os EndpointSlices e **agrupá-los pelo rótulo `kubernetes.io/service-name`**, porque um Service
pode ter vários slices. O resumo conta **endereços únicos** e, separadamente, os que têm
`conditions.ready: true` (`ready` ausente conta como pronto, como a API define). A tela tem **três
saídas**:

- `sem endpoint`;
- `N endereços, M prontos`;
- `ExternalName (<alvo>)`.

## Alternativas consideradas

| Alternativa | O que se ganha | Por que foi rejeitada |
|---|---|---|
| **`Endpoints`** | Um objeto por Service, mais simples | Base com prazo de validade: funciona hoje, mas está em depreciação, e é a base errada para uma fatia que será estendida. Além disso, `Endpoints` sem endereço simplesmente **não traz `subsets`**: a mesma armadilha de ausência, com vida útil menor |
| **Inferir pelo `selector` do Service** | Não precisa ler outro objeto | Reimplementa o controlador de endpoints (readiness, terminating, portas nomeadas, Services sem selector) e pode divergir do que o plano de controle publica. É o mesmo tipo de erro que "juízo inventado" proíbe. No caso `nyx-stg` (selector `app=nyx-api` e pods `app=nyxapi`), o slice publicado diz exatamente `endpoints: null` |

## Consequências

**Positivas**

- API durável e fiel ao que o plano de controle publica.
- Distingue os três estados, e **pegou o caso real** `nyx-prod/nyx-api` (2 endereços, 0 prontos).

**Negativas e riscos aceitos**

- **Mais código:** um Service pode ter vários slices, então é preciso agrupar e contar endereços
  únicos. Há ainda a permissão de leitura em `endpointslices`, um recurso a mais no RBAC.
- Se os EndpointSlices forem negados, a coluna de endpoint mostra
  `sem permissão para ler endpointslices` e o resto do bloco de Services continua.

## Verificação

- `tests/test_traducao.py`: `test_service_sem_endpoint_nyx_stg`,
  `test_service_com_enderecos_prontos_orion_prod`, `test_service_com_enderecos_nenhum_pronto_nyx_prod`,
  `test_enderecos_em_varios_slices_sem_duplicar`, `test_service_sem_slice_algum`,
  `test_service_external_name`, `test_ready_ausente_conta_como_pronto_conforme_a_api`.
- `tests/test_coleta.py::test_endpointslices_negados_viram_aviso_na_coluna`.
- Laboratório (8.1): `nyx-stg/nyx-api` `sem endpoint`; `orion-fake-shop` `2 endereços, 2 prontos`;
  `nyx-prod/nyx-api` `2 endereços, 0 prontos`.
