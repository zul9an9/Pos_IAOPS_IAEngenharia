# ADR-0006 — Erros classificados por bloco, com mensagem por categoria

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `design.md` D6; `CURADORIA.md` §3.6. Proposta pelo agente durante o `/opsx:propose`; o tratamento do seletor de namespace foi acrescentado na revisão da spec |
| **Relacionados** | [ADR-0002](ADR-0002-cliente-oficial-do-kubernetes.md), [ADR-0003](ADR-0003-atualizacao-sob-demanda.md) |

## Contexto

O ticket exige cenários adversos **sem stack trace**, e um deles é "permissão negada para **um** tipo
de recurso, enquanto os outros continuam acessíveis: o bloco daquele tipo mostra `sem permissão` e o
resto da tela funciona". Uma credencial restrita também é o caso mais provável de quem usa o painel
no dia a dia.

## Decisão

Cada listagem da coleta é executada e **classificada isoladamente**. O resultado de um bloco é
"dados", "vazio" ou um erro classificado. Nenhuma exceção chega ao HTML: o renderizador recebe só a
categoria e campos já pensados para exibição.

| Origem | Categoria | Onde aparece |
|---|---|---|
| Kubeconfig inexistente, ilegível, YAML inválido, ou contexto apontando para cluster ou usuário ausente (antes de qualquer chamada; cita caminho e tipo, nunca o conteúdo) | `kubeconfig-invalido` | Tela inteira |
| Kubeconfig sem `current-context` (antes de qualquer chamada) | `sem-contexto` | Tela inteira |
| Conexão recusada, DNS, TLS de servidor, `timeout` (3 s de conexão, 10 s de leitura, sem retentativas) | `nao-respondeu` | Tela inteira |
| HTTP 401; falha de plugin `exec`; certificado de cliente expirado; HTTP 403 cujo sujeito é `system:anonymous` | `credencial` | Tela inteira |
| HTTP 403 de usuário autenticado | `sem-permissao` | **Só o bloco** |
| Lista vazia com HTTP 200 | `vazio` | Só o bloco |
| Qualquer outra exceção | `inesperado` (mensagem genérica, detalhe só no log local) | Só o bloco |

Quando todas as listagens caem em `nao-respondeu` ou `credencial`, a tela inteira mostra essa
mensagem. `nao-respondeu` e `credencial` têm **textos diferentes**.

**Caso especial, a listagem de namespaces.** O 403 nela **não** vira bloco de erro: o seletor passa a
dizer `sem permissão para listar namespaces`, com um campo de digitação pré-preenchido com o
`namespace` do contexto corrente quando existir. Com esse namespace, a coleta usa só as listagens por
namespace. Isso atende a credencial restrita a um namespace, que de outro modo teria 403 também em
todas as listagens de "todos os namespaces". O nome digitado é validado como rótulo DNS-1123 antes de
qualquer chamada.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Deixar a exceção propagar até o servidor HTTP** | Produz stack trace ou página 500 genérica, exatamente o que a spec proíbe |
| **Uma tela de erro global para qualquer falha** | Um 403 em eventos esconderia pods e deployments, violando "o resto da tela funciona" |

## Consequências

**Positivas**

- "O resto da tela funciona" quando só um recurso é negado.
- Mensagens distintas para cada categoria, e o detalhe técnico vai só para o log do processo.
- Uma credencial restrita a um namespace continua útil.

**Negativas e riscos aceitos**

- Perde a simplicidade de um único tratamento de erro: há uma classificação a manter.
- **O 403 anônimo pode ser confundido com falta de permissão.** Com `anonymous-auth` ligado, uma
  credencial inválida pode virar 403 `system:anonymous` em vez de 401. Mitigação: esse caso é
  classificado como `credencial`.

## Verificação

- `tests/test_coleta.py`: `test_classificacao`, `test_erro_de_cluster_na_primeira_chamada_vira_global`,
  `test_eventos_negados_e_o_resto_funciona`, `test_namespaces_negados_usa_namespace_do_contexto`,
  `test_namespaces_negados_sem_namespace_no_contexto_nao_quebra`.
- `tests/test_render.py`: `test_nao_respondeu_e_credencial_tem_textos_distintos`,
  `test_sem_contexto_e_kubeconfig_invalido_tem_textos_distintos`, `test_sem_permissao_so_no_bloco_negado`,
  `test_nenhuma_tela_mostra_stack_trace`.
- Laboratório: cenários 8.3 a 8.9 (cada um com mensagem própria, sem stack trace). O 8.5 e o 8.9
  usaram ServiceAccounts de laboratório (`deploy/lab/`).
