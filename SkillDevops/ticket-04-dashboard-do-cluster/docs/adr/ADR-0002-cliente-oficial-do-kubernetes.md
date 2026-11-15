# ADR-0002 — Cliente oficial do Kubernetes, isolado numa camada de acesso

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `design.md` D2; `CURADORIA.md` §3.2. Constava do prompt do `/opsx:propose` como decisão já tomada pelo autor (D2) |
| **Relacionados** | [ADR-0001](ADR-0001-python-com-html-servido-localmente.md), [ADR-0005](ADR-0005-somente-leitura-em-tres-camadas.md) |

## Contexto

Autenticar a partir de um kubeconfig não é só "um token". Envolve certificado de cliente, bearer
token, CA do servidor, OIDC e plugins `exec` (comuns em clusters gerenciados). Errar nessa parte é
pior do que a dependência: é o código mais sensível e mais fácil de errar do projeto. Esta decisão
aparece **em contraste** com o Ticket 03, que ficou só na biblioteca padrão.

## Decisão

Usar o **cliente oficial `kubernetes` para Python**, **isolado num único módulo** (`acesso.py`), que
é o **único** a importar o cliente e o único ponto de contato com o cluster. A versão é fixada em
`requirements.txt` (`kubernetes==36.0.3`).

## Alternativas consideradas

| Alternativa | O que se ganha | Por que foi rejeitada |
|---|---|---|
| **`kubectl` como subprocesso** | Nenhuma biblioteca de cliente para manter | Exige o binário instalado, trata a saída como contrato não oficial, cria um processo por chamada e dificulta agregar EndpointSlices por Service. **E é o pior caso para o invariante:** um subprocesso aceita qualquer verbo, inclusive escrita, e escapa da camada única de acesso. Por isso o teste de só leitura barra `kubectl` como subprocesso |
| **HTTP direto no apiserver** | A menor dependência possível | Obriga a reimplementar a autenticação de kubeconfig (certificados, plugins `exec`, validação de CA), exatamente o código sensível e fácil de errar que esta decisão evita |

## Consequências

**Positivas**

- Autenticação idêntica à do `kubectl`: certificado de cliente, token, CA, OIDC e plugins `exec`.
- Tipagem e paginação prontas.
- A tradução das exceções do cliente em categorias de erro (ADR-0006) fica no mesmo módulo, e nenhum
  outro precisa conhecer os tipos de exceção do `kubernetes`.

**Negativas e riscos aceitos**

- **Uma dependência pesada**, atrelada à compatibilidade com a versão do Python. Mitigação: versão
  fixada e instalação validada na tarefa 1.1. Se houvesse incompatibilidade com o Python 3.14, o plano
  era usar o 3.12 ou 3.13.
- O painel passa a depender de `kubernetes` e de `PyYAML` (para ler o kubeconfig).

## Verificação

- `tests/test_somente_leitura.py`: o scanner barra `import kubernetes` fora da camada de acesso e
  `subprocess` invocando `kubectl`; `test_camada_de_acesso_exporta_so_listagens`.
- `tests/test_kubeconfig.py`: `test_usa_somente_o_contexto_corrente` e `test_nao_grava_no_kubeconfig`
  (o cliente é carregado com `persist_config=False`).
