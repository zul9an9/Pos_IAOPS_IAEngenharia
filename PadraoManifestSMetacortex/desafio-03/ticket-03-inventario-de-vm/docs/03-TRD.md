# TRD — vminv: requisitos e desenho técnico

| | |
|---|---|
| **Produto** | `vminv` (Ticket 03) |
| **Estado** | Implementado (`vminv/`) e coberto por testes unitários e de laboratório (`tests/`) |
| **Fontes** | `design.md` do change `vm-inventory-drift`, `openspec/specs/`, o código em `vminv/` e `tests/` |
| **Consolidado em** | 2026-11-08. Este documento descreve o que existe e remete cada decisão ao seu ADR |
| **Documentos irmãos** | [`02-PRD.md`](02-PRD.md) (o que e para quem) e [`adr/`](adr/README.md) (por que) |

## 1. Objetivo e escopo do documento

Descrever como o `vminv` atende o [PRD](02-PRD.md): componentes, fluxo, interfaces e contratos de
dados, tratamento de erros, garantias de segurança e estratégia de testes. As decisões que
sustentam o desenho estão nos ADRs, e aqui aparecem só pela sua consequência técnica.

## 2. Contexto de execução

A ferramenta roda na máquina de quem opera, nunca como serviço, contra **uma VM por invocação**.
Não há nada instalado no host auditado.

```
 máquina do operador                                        VM auditada
┌──────────────────────────────────────────┐              ┌───────────────────────┐
│ python -m vminv                          │              │                       │
│                                          │   1 sessão   │  sh -s  <── stdin:    │
│  baseline.yaml ─► baseline.py            │   SSH        │  collector.sh         │
│                      │                   │ ───────────► │  (só leitura)         │
│  cli.py ─► ssh_transport.py ─► `ssh` ────┼──────────────┤                       │
│                      │         (do SO)   │ ◄─────────── │  stdout: 1 JSON       │
│                      ▼                   │   JSON cru   │  (fatos lidos/não     │
│               inventory.py               │              │   lidos)              │
│                      │                   │              └───────────────────────┘
│                      ▼                   │
│               compliance.py ◄─ baseline  │   a comparação acontece só aqui
│                      │                   │
│                      ▼                   │
│                report.py ─► stdout / arquivos (JSON, Markdown) ─► exit 0 | 1 | 2
└──────────────────────────────────────────┘
```

## 3. Restrições de projeto

1. **A equipe que mantém a ferramenta é só Python.** Uma segunda linguagem, ou uma dependência com
   SSH embutido, teria custo contínuo para uma CLI pontual e de baixo tráfego ([ADR-0001](adr/ADR-0001-python-somente-biblioteca-padrao.md)).
2. **A chave privada passa por esta ferramenta.** Tudo que aumente a superfície em que a chave é
   manipulada (parsear, manter em memória, passar por uma biblioteca) aumenta o risco sem benefício
   de comportamento, porque o cliente `ssh` do sistema já faz isso com segurança
   ([ADR-0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md)).
3. **Sem privilégio no host.** O que exigiria privilégio é reportado como não lido.
4. **Ambiente de desenvolvimento e validação:** Windows, com um host de laboratório Ubuntu 26.04
   em WSL2. A ferramenta exige Python 3.10+ (desenvolvida em 3.14) e o cliente `ssh` no `PATH`.

## 4. Componentes

| Módulo (`vminv/`) | Responsabilidade | Fronteira que mantém |
|---|---|---|
| `__main__.py` | Ponto de entrada de `python -m vminv` | Só chama `cli.main` |
| `cli.py` | Interpreta os argumentos, orquestra o fluxo, grava saídas e converte falhas em código de saída | **Única** camada que decide o código de saída. Captura `FalhaDeExecucao`, `KeyboardInterrupt` e qualquer outra exceção, sem exibir detalhe interno |
| `ssh_transport.py` | Monta o `argv` do `ssh`, executa o subprocesso, classifica o desfecho em categorias fixas | **Só conhece o caminho da chave** e nunca abre o arquivo. Nunca repassa o stderr do `ssh` cru |
| `collector.sh` | Script POSIX enviado por stdin (`sh -s`). Mede e imprime um único JSON | **Não decide conformidade.** Só comandos de leitura. Nunca recebe o baseline |
| `inventory.py` | Valida e interpreta a resposta JSON do coletor num objeto `Inventario` | Distingue "lido" de "não lido" e levanta `RespostaInvalida` para resposta malformada |
| `baseline.py` | Parser YAML mínimo e `carregar_baseline` (layout, versão, severidades) | Recusa o que não entende. É a única peça de parsing com risco real de correção |
| `compliance.py` | Motor de conformidade: uma entrada por regra, com semântica por tipo | **Roda inteiramente local** e só lê o objeto `Inventario`. Nunca toca o host |
| `report.py` | Monta o relatório e o serializa em JSON e Markdown | Não conhece o caminho nem o conteúdo da chave |
| `errors.py` | Hierarquia de falhas de execução | Toda falha termina em exit 2 com mensagem simples |

Hierarquia de falhas (`errors.py`): `FalhaDeExecucao` é a base, e dela derivam `UsoIncorreto`,
`BaselineInvalido`, `FalhaDeConexao`, `RespostaInvalida` e `SaidaNaoGravavel`.

## 5. Fluxo de execução

Implementado em `cli.executar`:

1. **Valida os argumentos.** Faltam obrigatórios ou `--timeout` < 1 → `UsoIncorreto`.
2. **Lê e valida o baseline, antes de tocar no host.** Um baseline ruim falha sem abrir nenhuma
   conexão ([ADR-0005](adr/ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md)).
3. **Coleta** (`ssh_transport.coletar`): verifica que o arquivo da chave existe (`stat`, sem abrir),
   localiza o `ssh`, monta o `argv` e executa **uma** sessão que recebe o `collector.sh` por stdin
   ([ADR-0003](adr/ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md)).
4. **Interpreta a resposta** (`inventory.interpretar_resposta`) num objeto `Inventario`.
5. **Compara localmente** (`compliance.avaliar`): uma entrada por regra do baseline
   ([ADR-0004](adr/ADR-0004-comparacao-local-nunca-no-host.md)).
6. **Monta o relatório** (`report.montar_relatorio`) e o serializa em JSON e em Markdown **a partir
   do mesmo dado**.
7. **Grava** `--saida-json` e `--saida-markdown`, se pedidos. Falha ao gravar → `SaidaNaoGravavel`.
8. **Escreve o relatório em stdout** (`--formato`, padrão `markdown`) e devolve o código de saída:
   `1` se houver pelo menos um `desvio`, senão `0` ([ADR-0010](adr/ADR-0010-codigos-de-saida-0-1-2.md)).

Em falha de execução **não há relatório**, porque não há inventário.

## 6. Interfaces

### 6.1 Linha de comando

| Argumento | Descrição |
|---|---|
| `--host`, `--usuario`, `--chave`, `--baseline` | Obrigatórios. Um único host por execução |
| `--formato {markdown,json}` | Relatório em stdout. Padrão: `markdown` |
| `--saida-json ARQ`, `--saida-markdown ARQ` | Gravam o relatório em arquivo. Podem ser usados juntos, e geram os dois relatórios numa execução |
| `--aceitar-host-novo` | `StrictHostKeyChecking=accept-new`. Aceita só host **novo**; chave alterada continua recusada |
| `--timeout N` | `ConnectTimeout` do `ssh`, em segundos. Padrão: 10 |

`allow_abbrev` está desligado. Erro de uso vira `UsoIncorreto` (exit 2), nunca a saída padrão do
`argparse`.

### 6.2 Chamada ao cliente `ssh`

```
ssh -i <caminho> -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=<n> \
    -o StrictHostKeyChecking=<yes|accept-new> <usuario>@<host> sh -s
```

O `collector.sh` entra por stdin. Escolhas e seus ADRs:

| Elemento | Motivo | ADR |
|---|---|---|
| `-i <caminho>` | A chave é entregue só como caminho | [0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) |
| `IdentitiesOnly=yes` | Só a chave de `-i` é oferecida, e não as do agente ou as de `~/.ssh/id_*` | [0008](adr/ADR-0008-identitiesonly-yes.md) |
| `BatchMode=yes` | O `ssh` nunca pergunta nada. Host desconhecido vira recusa, não prompt | [0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) |
| `ConnectTimeout` | Evita travar na conexão. Há ainda um teto de **120 s** para a sessão inteira (`TEMPO_MAXIMO_SESSAO`) | [0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) |
| `StrictHostKeyChecking` | `yes` por padrão, `accept-new` só com flag. **Nunca** `no`, e nunca `UserKnownHostsFile=/dev/null` | [0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) |
| `sh -s` | Interpretador POSIX, não `bash` | [0003](adr/ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md) |

Nunca é passado `-v`.

### 6.3 Contrato do coletor (host → ferramenta)

O `collector.sh` imprime **um** objeto JSON. Todo fato é um envelope:

```json
{"read": true,  "value": <valor cru>}
{"read": false, "reason": "<motivo>"}
```

O valor de um fato lido pode ser vazio, zero ou `false`. A sentinela de **não lido** é distinta
disso, e é o que permite ao lado local diferenciar "lido e vazio" de "não lido". Os fatos
(`inventory.FATOS_ESPERADOS`) são: `coletado_em`, `hostname`, `so`, `kernel`, `servicos`, `swap`,
`portas`, `chaves_ssh`, `ssh_login_root` e `ntp`. O formato suportado é a versão 1.

O script faz `LC_ALL=C` e `set -f`, escapa todo valor antes de emitir JSON e redireciona saída
apenas para `/dev/null`. Comando ausente, arquivo ilegível ou falta de permissão vira fato não lido com motivo, nunca
erro: `systemctl`, `ss` e `ssh-keygen` são verificados antes do uso (`command -v`), e os arquivos
lidos são testados com `-r`.

| Fato | Fonte no host |
|---|---|
| SO | `/etc/os-release` |
| Kernel | `uname -r` |
| Serviços e soquetes | `systemctl list-units --type=service,socket --state=active` |
| Swap | `/proc/swaps` |
| Portas, endereço de vínculo e processo dono | `ss -ltnp` |
| Chaves SSH autorizadas | `~/.ssh/authorized_keys` do usuário que conectou, com `ssh-keygen -lf` para o fingerprint |
| Login de root efetivo | `sshd -T`, com o binário localizado por `command -v` ou nos caminhos usuais (exige privilégio) |
| Sincronização de tempo | `systemctl is-active` sobre `systemd-timesyncd`, `chrony`, `chronyd`, `ntp`, `ntpd` e `ntpsec` (exige systemd em execução) |
| Identificação | `hostname` (ou `uname -n`) e o instante da coleta em UTC (`date -u`) |

O `01-brainstorm.md` previa `timedatectl` para a sincronização de tempo; a implementação usa
`systemctl is-active` sobre os mecanismos listados acima, e o brainstorm não foi reescrito.

### 6.4 Baseline (entrada)

Layout oficial, versionado pelo enunciado (não é livre). Ver `baseline.exemplo.yaml`.

| Chave | Conteúdo |
|---|---|
| `versao` | Inteiro. Suportado hoje: `{1}` |
| `aplica_a` | Texto não vazio. Informativo, sem lógica de casamento nesta fatia |
| `esperado` | Grupos `so`, `kernel`, `servicos`, `swap`, `portas_em_escuta`, `chaves_ssh`, `ssh`, `ntp`, cada um com suas regras |
| `severidade` | Listas **invertidas** `critico`, `alto`, `medio`, cada uma com ids de regras |

O **id de uma regra é o caminho pontilhado dentro de `esperado`** (ex.: `so.versao_minima`), e a
ordem das regras é a de aparição em `esperado`. É baseline inválido (exit 2): chave de severidade
fora do conjunto fechado, regra sem severidade, regra em mais de uma lista, id em `severidade` que
não existe em `esperado`, e valor de `versao_minima` que não é sequência numérica. Uma regra
desconhecida da ferramenta continua válida e recebe `nao_verificado`
([ADR-0007](adr/ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md), seção 7.1).

### 6.5 Relatório JSON (contrato com o Roster)

```
{ "host":         { endereco, hostname, coletado_em },
  "inventario":   { so: {distribuicao, versao}, kernel: {versao},
                    servicos: [{nome, tipo, estado}], swap: {habilitado, tamanho},
                    portas_em_escuta: [{porta, bind, processo}],
                    chaves_ssh: [{identificacao}], ssh: {login_de_root},
                    ntp: {sincronizado, mecanismo} },
  "conformidade": [ {regra, esperado, encontrado, veredito, severidade?, motivo?} ],
  "resumo":       { conforme, desvio, nao_verificado,
                    por_severidade: {critico, alto, medio} } }
```

Convenções de projeção do inventário:

- `servicos[].nome` é o nome da unidade **sem** sufixo, com `tipo` (`service`/`socket`) separado, e
  `estado` é o estado ativo do systemd.
- `swap.tamanho` é em **bytes** (inteiro). Swap desabilitado é `habilitado: false, tamanho: 0`
  (lido), diferente de `null`.
- `chaves_ssh[].identificacao` é o comentário da chave, ou o fingerprint quando não há comentário.
  **O material da chave nunca aparece.**
- `ssh.login_de_root` é booleano ([ADR-0009](adr/ADR-0009-prohibit-password-conta-como-root-habilitado.md)). O valor efetivo cru do `sshd` aparece em `encontrado` da regra.
- `ntp.mecanismo` é `"nenhum"` quando não há mecanismo ativo. Nunca `null`, que significa "não lido".
- **Campo não lido é `null`**, nunca `[]`, `0`, `false` nem `""`. Fatos em forma de objeto mantêm o
  objeto com folhas `null` (ex.: `swap: {habilitado: null, tamanho: null}`, para o Roster acessar o
  caminho sem erro). Fatos em forma de lista viram `null`.
- Em `conformidade`, `severidade` aparece **só em `desvio`**, e `motivo` **só em `nao_verificado`**
  (com `encontrado: null`). `resumo.por_severidade` conta apenas desvios.
- **Isolamento do tempo:** o instante da coleta fica num único campo (`host.coletado_em`), e é só
  ele que varia entre duas execuções.

### 6.6 Relatório Markdown (para o plantão)

```
# Inventário — <hostname> (<endereco>)
Coletado em <data> · baseline v<versao>

## Desvios        tabela Severidade | Regra | Esperado | Encontrado
                  ordem crítico > alto > médio; dentro do mesmo nível, a ordem do baseline
## Não verificado tabela Regra | Motivo
## Conforme       nomes das regras separados por " · "
```

Mostra primeiro o que exige ação. O inventário completo fica no JSON.

### 6.7 Códigos de saída e destino das saídas

| Código | Significado |
|---|---|
| `0` | Nenhum desvio (regras `conforme` ou `nao_verificado`) |
| `1` | Pelo menos um `desvio` |
| `2` | Falha de execução: host inalcançável ou desconhecido, chave recusada, baseline inválido, uso incorreto, resposta inválida, arquivo de saída não gravável |

O relatório vai para **stdout**; erros e diagnóstico vão **só para stderr**, então o stdout contém
apenas o relatório e serve em pipe.

## 7. Motor de conformidade

Para cada regra do baseline há **uma** entrada. A comparação é determinística: mesmo inventário e
mesmo baseline dão o mesmo veredito e a mesma severidade.

**Origens de `nao_verificado`** ([ADR-0006](adr/ADR-0006-nao-verificado-veredito-de-primeira-classe.md)), ambas com motivo explícito e nenhuma resultando em `conforme`:

1. o fato foi coletado, mas marcado como **não lido** (ex.: falta de privilégio);
2. a regra referencia um fato que a **coleta não produz**.

**Semântica por tipo de regra** ([ADR-0007](adr/ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md), seção 7.2):

| Regra | Conforme quando | Desvio quando (o que aparece em `encontrado`) |
|---|---|---|
| `servicos.ativos` | Todas as unidades listadas estão presentes e ativas. Nome sem sufixo é `.service`; `.socket` exige o sufixo | Alguma ausente ou inativa (lista as ausentes) |
| `servicos.proibidos` | Nenhuma das listadas está ativa | Alguma presente (lista as proibidas presentes) |
| `so.distribuicao` | Igual à esperada, sem diferenciar caixa | Diferente (a distribuição reportada) |
| `so.versao_minima`, `kernel.versao_minima` | Versão numericamente ≥ à mínima, por componente (`6.10` > `6.9`). No kernel só o prefixo numérico conta (`5.15.0-101-generic` → `5.15.0`) | Versão numericamente inferior. Versão do host ilegível → `nao_verificado` |
| `portas_em_escuta.publicas_permitidas` | Toda porta vinculada a endereço público está na lista | Há porta pública fora da lista (lista as portas e endereços) |
| `portas_em_escuta.somente_rede_interna` | A porta existe e **todas** as suas vinculações são a endereço interno | Alguma vinculação a endereço público, mesmo que também haja uma interna, **ou a porta não existe** |
| `swap.habilitado`, `ntp.sincronizado` | O booleano encontrado é igual ao esperado | Booleano diferente |
| `ssh.login_de_root` | Só o valor efetivo `no` é `false`. Qualquer outro (`yes`, `prohibit-password`, `forced-commands-only`) é `true` | O booleano não bate com o esperado |
| `chaves_ssh.emitidas_por` | Toda chave tem identificação cujo trecho após o último `@` é o emissor declarado. Conjunto sem chave também é conforme | Alguma chave sem identificação ou com emissor diferente (lista cada ofensora, sem o material) |

**Endereço interno** é loopback (`127.0.0.0/8`, `::1`), RFC1918 (`10/8`, `172.16/12`,
`192.168/16`), link-local (`169.254/16`, `fe80::/10`) ou ULA (`fc00::/7`). `0.0.0.0`, `::`, `*` e
qualquer outro endereço são públicos.

## 8. Tratamento de erros

### 8.1 Classificação do desfecho do `ssh`

`ssh_transport.classificar` usa o **status de saída primeiro** (255 é falha de conexão ou
autenticação do próprio `ssh`) e trata o texto do stderr só como apoio para subcategorias, porque
ele varia entre versões e locales do OpenSSH.

| Desfecho | Como é reconhecido | Mensagem ao operador (resumo) |
|---|---|---|
| Sucesso | status `0` | (segue o fluxo) |
| Host desconhecido | `255` + "host key verification failed" | chave do host desconhecida; recusada pela política padrão; use `--aceitar-host-novo` se aceitar o risco |
| Host alterado | `255` + "identification has changed" ou "offending" | chave do host alterada; recusada por segurança (possível troca ou interceptação) |
| Autenticação | `255` + "permission denied" ou "no supported authentication" | o host rejeitou a autenticação: chave recusada, protegida por senha ou sem permissão |
| Inalcançável | `255` sem texto reconhecido | não foi possível conectar: inalcançável, sem resposta no tempo limite, ou conexão recusada |
| Outra | qualquer status diferente de `0` e `255` | falha por motivo não classificado, com o código do `ssh` |

O texto do stderr do `ssh` **nunca** é repassado cru. A categoria "outra" existe para que um caso
não reconhecido ainda saia com exit 2 e uma mensagem decente, em vez de quebrar.

### 8.2 Outras falhas

| Situação | Tratamento |
|---|---|
| Arquivo da chave não existe | `FalhaDeExecucao` citando o **caminho** informado, sem conectar |
| `ssh` ausente do `PATH`, ou não executável | `FalhaDeExecucao` |
| Sessão passa de 120 s | `FalhaDeConexao`, e o processo é interrompido |
| Resposta do coletor malformada ou truncada | `RespostaInvalida` |
| Baseline ilegível ou inválido | `BaselineInvalido`, antes de qualquer conexão |
| Arquivo de saída não gravável | `SaidaNaoGravavel` |
| `Ctrl+C` | "execução interrompida pelo operador", exit 2 |
| Exceção inesperada | "falha inesperada da ferramenta (sem detalhes exibidos por segurança)", exit 2. **Nunca** stack trace |

## 9. Segurança e garantias

**Chave privada** ([ADR-0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md), [ADR-0008](adr/ADR-0008-identitiesonly-yes.md))

- A ferramenta só conhece o **caminho**. Pode fazer `stat` nele, mas nunca o abre.
- O **conteúdo** nunca aparece em stdout, stderr, arquivo ou mensagem de erro.
- O **caminho** pode aparecer em mensagens de erro no stderr da própria ferramenta (é dado digitado
  pelo operador e serve ao diagnóstico), mas **não** nos relatórios JSON e Markdown, que circulam
  fora da máquina do operador.
- O stderr do `ssh` é reescrito em categorias fixas, e a chave nunca entra no espaço de
  endereçamento da ferramenta, o que torna estruturalmente mais difícil vazá-la numa exceção.

**Somente leitura** (camadas)

1. O coletor é `sh` POSIX sem comando que escreva, instale ou mude estado, com revisão estática
   por checklist (tarefa 3.9).
2. O estado do host (unidades systemd ativas, `/proc/swaps`, `ss -ltn`, `authorized_keys`) foi
   comparado antes e depois da coleta, sem diferença.
3. A comparação roda localmente, e um teste com dublê de transporte **falha** se a etapa de
   conformidade tentar falar com o host ([ADR-0004](adr/ADR-0004-comparacao-local-nunca-no-host.md)).
4. Duas execuções seguidas: o diff campo a campo do JSON acusa **apenas** `host.coletado_em`.

**Chave do host:** `known_hosts` padrão do operador sempre respeitado. Host desconhecido é recusado
por padrão, e chave **alterada** é recusada mesmo com `--aceitar-host-novo`.

## 10. Parser YAML do baseline

O parser aceita só o subconjunto de que o layout oficial precisa: mapeamentos em bloco, listas em
bloco, escalares, comentários e *flow style de uma linha* (`[a, b]` e `{chave: valor, outra:
[x, y]}`, com o mapeamento em linha só de escalares ou de listas de escalares).

Recusa, com erro de "construção não suportada" que nomeia a construção e a linha: âncoras e
aliases, multi-documento, tags complexas, mapeamento em linha aninhado, mapeamento dentro de lista
e flow multilinha. **Booleanos são somente `true` e `false`**: `yes`, `no`, `on`, `off`, `y` e `n`
são rejeitados, porque a tipagem implícita do YAML (`no` → `False`) transformaria um desvio real em
falso `conforme` ([ADR-0005](adr/ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md)).

Versão do baseline: ausente, não inteira ou fora de `{1}` é falha de execução, com mensagem que
distingue **ausente**, **desconhecida** e **futura** (maior que a suportada).

## 11. Estratégia de testes

Suíte em `tests/`, executada com `python -m unittest discover` e **sem dependências**. Um arquivo por área:

| Arquivo | O que garante |
|---|---|
| `tests/test_transport.py` | O `argv` (opções obrigatórias, chave só como caminho, sem flags proibidas, `IdentitiesOnly`), nenhuma biblioteca SSH importada pelo pacote, classificação (status antes do texto), política de `StrictHostKeyChecking`, timeout |
| `tests/test_vazamento.py` | O conteúdo da chave não aparece em nenhuma saída capturada, em todos os caminhos de falha. O caminho só aparece no stderr. A ferramenta nunca abre o arquivo da chave |
| `tests/test_coletor.py` | O `collector.sh` e o formato dos fatos, lidos e não lidos |
| `tests/test_baseline.py` | O parser: construções recusadas (âncora, etc.) e a validação de versão (ausente, futura) |
| `tests/test_compliance.py` | A semântica por tipo de regra, incluindo versão numérica, portas públicas e internas, e `prohibit-password` |
| `tests/test_inventory_report.py` | Interpretação do inventário e formatos dos relatórios |
| `tests/test_cli.py` | Fluxo completo com dublê do transporte, e códigos de saída |
| `tests/test_laboratorio.py` | Contra o host real, incluindo "chave errada é rejeitada mesmo com a chave padrão do operador" |
| `tests/helpers.py` | Apoio compartilhado |

Os testes do laboratório só rodam com `VMINV_LAB_HOST`, `VMINV_LAB_USER` e `VMINV_LAB_KEY`
definidos; sem elas, são ignorados.

## 12. Não objetivos de design

1. **Sem retentativa nem backoff.** Uma tentativa com `ConnectTimeout` basta na fatia 1, e o
   plantão reexecuta manualmente.
2. **Sem saída parcial ou em streaming.** O relatório só existe depois que a sessão única termina
   ou falha.
3. **Sem camada de abstração de transporte.** Existe um único transporte (o subprocesso do `ssh`
   do sistema), e nenhum segundo é previsto.

O parâmetro `executor` de `ssh_transport.coletar` existe para os testes injetarem um dublê do
subprocesso, e não como ponto de extensão para outros transportes.

## 13. Riscos técnicos e mitigações

| Risco | Mitigação |
|---|---|
| Classificar stderr e códigos do `ssh` é frágil entre versões e locales do OpenSSH | Status de saída primeiro, texto só como apoio, e uma categoria de fallback sempre disponível |
| Um parser YAML escrito à mão suporta uma gramática menor que a real, e rejeita um baseline legítimo | Falha ruidosa, nomeando a construção e a linha |
| Sem retentativa, uma oscilação de rede vira exit 2 | Aceito na fatia 1. `ConnectTimeout` curto torna a nova tentativa barata |
| Distinguir `service` de `socket` e calcular o SSH efetivo dependem de systemd e OpenSSH no host | Host sem a ferramenta reporta os campos afetados como não lidos, com motivo, sem quebrar a coleta |
| `nao_verificado` não gera exit 1, então um baseline todo não verificável sai com `0` | Aceito na fatia 1. O veredito e o motivo aparecem em cada entrada, e o critério de aceite exige `conforme` em todas |
| A coleta de chaves cobre só o `authorized_keys` do usuário que conectou | O escopo é declarado na spec e no relatório |
| O JSON do Roster não tem campo de motivo no `inventario` | Contrato externo, não estendido nesta fatia. O motivo sempre aparece em `conformidade` |

## 14. Implantação e operação

Projeto greenfield, sem versão anterior nem migração. A implantação é instalar o Python 3 (já
presumido presente) e o código-fonte na máquina do operador. **Nada é instalado no servidor.**
Não há `requirements.txt`.

## 15. Rastreabilidade das decisões

| ADR | Decisão | `design.md` |
|---|---|---|
| [0001](adr/ADR-0001-python-somente-biblioteca-padrao.md) | Python 3, somente biblioteca padrão | D1 |
| [0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) | Cliente `ssh` do sistema via subprocesso, chave só como caminho | D2 |
| [0003](adr/ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md) | Sessão SSH única, script `sh` POSIX por stdin, uma resposta JSON | D3 |
| [0004](adr/ADR-0004-comparacao-local-nunca-no-host.md) | A comparação acontece localmente, nunca no host | D4 |
| [0005](adr/ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md) | Parser YAML mínimo e validação da versão do baseline | D5 |
| [0006](adr/ADR-0006-nao-verificado-veredito-de-primeira-classe.md) | `nao_verificado` como veredito de primeira classe | D6 |
| [0007](adr/ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md) | Layout do baseline, comparação por tipo de regra e formato das saídas | D7 |
| [0008](adr/ADR-0008-identitiesonly-yes.md) | `-o IdentitiesOnly=yes` | D8 |
| [0009](adr/ADR-0009-prohibit-password-conta-como-root-habilitado.md) | `prohibit-password` conta como root habilitado | D9 |
| [0010](adr/ADR-0010-codigos-de-saida-0-1-2.md) | Códigos de saída 0, 1 e 2 | brainstorm D7 |
