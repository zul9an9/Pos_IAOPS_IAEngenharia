# vminv — inventário de uma VM e conformidade com o baseline

Ferramenta de linha de comando (Python 3, **somente biblioteca padrão**) que entra em **uma** VM por SSH,
levanta o retrato real da máquina e o compara, regra a regra, com o `baseline.yaml` do parque.
É **só-leitura** no host e não exige privilégio: o que exigiria privilégio sai como `nao_verificado`.

## Requisitos

- Python 3.10+ (desenvolvido em 3.14) e o cliente `ssh` do sistema no `PATH`.
- Nenhuma dependência externa (não há `requirements.txt`).

## Uso

```
python -m vminv --host 172.29.2.241 --usuario orpheu --chave ~/.ssh/metacortex --baseline baseline.exemplo.yaml
```

| Argumento | Descrição |
|---|---|
| `--host`, `--usuario`, `--chave`, `--baseline` | obrigatórios; um único host por execução |
| `--formato {markdown,json}` | relatório enviado ao stdout (padrão: `markdown`) |
| `--saida-json ARQ`, `--saida-markdown ARQ` | gravam também o relatório em arquivo (podem ser usadas juntas) |
| `--aceitar-host-novo` | aceita a chave de um host **ainda desconhecido** (`StrictHostKeyChecking=accept-new`); chave alterada continua recusada |
| `--timeout N` | `ConnectTimeout` do ssh, em segundos (padrão: 10) |

Por padrão a chave do host precisa constar no `known_hosts` do operador; host desconhecido é recusado (exit 2).
Só o **caminho** da chave é usado (`-i`): a ferramenta nunca abre o arquivo, e o conteúdo da chave nunca aparece
em saída, arquivo ou mensagem de erro. Mensagens de erro vão só para o stderr.

## Códigos de saída

| Código | Significado |
|---|---|
| `0` | nenhum desvio (regras `conforme` ou `nao_verificado`) |
| `1` | pelo menos um `desvio` |
| `2` | falha de execução: host inalcançável ou desconhecido, chave recusada, baseline inválido, uso incorreto, arquivo de saída não gravável |

## Baseline (layout oficial)

Veja `baseline.exemplo.yaml`. Chaves de raiz: `versao` (suportada: `1`), `aplica_a`, `esperado` e `severidade`.
O id da regra é o caminho pontilhado dentro de `esperado` (ex.: `portas_em_escuta.somente_rede_interna`); a
severidade vem das listas invertidas `critico`, `alto`, `medio` (conjunto fechado; regra sem severidade é baseline
inválido). Booleanos são somente `true`/`false`. O parser YAML é mínimo e recusa o que não entende.

Regras conhecidas: `so.distribuicao`, `so.versao_minima`, `kernel.versao_minima`, `servicos.ativos`,
`servicos.proibidos`, `swap.habilitado`, `portas_em_escuta.publicas_permitidas`,
`portas_em_escuta.somente_rede_interna`, `chaves_ssh.emitidas_por`, `ssh.login_de_root`, `ntp.sincronizado`.
Regra desconhecida (fato que a coleta não produz) recebe `nao_verificado`, nunca `conforme`.

## Relatórios

- **JSON** (formato consumido pelo Roster): `host`, `inventario`, `conformidade`, `resumo`. Campo não lido no
  inventário é `null`; o motivo vai na entrada de `conformidade`.
- **Markdown** (para o plantão): `Desvios` (ordenados crítico > alto > médio), `Não verificado` e `Conforme`.

## Testes

```
python -m unittest discover
```

Os testes do laboratório só rodam com as variáveis abaixo definidas (caso contrário são ignorados):

```
VMINV_LAB_HOST=172.29.2.241  VMINV_LAB_USER=orpheu  VMINV_LAB_KEY=~/.ssh/metacortex
```

## Conteúdo do diretório

| Caminho | O que é |
|---|---|
| `vminv/` | código da ferramenta (`collector.sh` é o script POSIX enviado ao host por `sh -s`) |
| `tests/` | testes unitários e de laboratório |
| `baseline.exemplo.yaml` | baseline oficial do enunciado |
| `laboratorio/` | baseline reduzido e relatórios (JSON e Markdown) gerados contra o host de laboratório |
| `openspec/` | planejamento: proposta, design, tarefas e specs (`openspec/specs/`), change arquivada em `openspec/changes/archive/` |
