# ADR-0007 — Contrato de dados: layout do baseline, comparação por tipo de regra e formato das saídas

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`) |
| **Origem** | `design.md` D7 |
| **Relacionados** | [ADR-0004](ADR-0004-comparacao-local-nunca-no-host.md), [ADR-0005](ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md), [ADR-0006](ADR-0006-nao-verificado-veredito-de-primeira-classe.md), [ADR-0009](ADR-0009-prohibit-password-conta-como-root-habilitado.md) |

Este ADR reúne três decisões que formam um único contrato de dados. Elas são numeradas para poder
ser citadas separadamente (7.1, 7.2 e 7.3).

## Contexto

Três fatos moldam a decisão. O **layout do `baseline.yaml` e o formato das duas saídas são do
enunciado do ticket** (versionados, não livres), e a primeira implementação os reinventou porque
nenhum artefato os trazia (ver `curadoria.md` §3). Quase nenhuma regra do baseline é igualdade
simples. E o JSON é um **contrato externo** com o Roster, enquanto o Markdown é lido pelo plantão no
terminal.

## Decisão

### 7.1 Layout do baseline e severidades fechadas

- Layout oficial: `versao`, `aplica_a` (obrigatório, texto não vazio; informativo, **sem lógica de
  casamento** nesta fatia), `esperado` (grupos `so`, `kernel`, `servicos`, `swap`,
  `portas_em_escuta`, `chaves_ssh`, `ssh`, `ntp`) e `severidade`, em listas **invertidas**
  (`critico`, `alto`, `medio`), cada uma com ids de regras.
- O **id de uma regra é o caminho pontilhado dentro de `esperado`** (ex.: `so.versao_minima`), e a
  ordem das regras é a de aparição em `esperado`.
- **Severidade é um conjunto fechado** (`critico`, `alto`, `medio`). É baseline inválido (exit 2):
  chave de severidade fora do conjunto, regra de `esperado` sem severidade, regra em mais de uma
  lista, e id em `severidade` que não existe em `esperado` (um erro de digitação deixaria a regra
  real sem severidade e a severidade solta sem regra).
- Regra de `esperado` **desconhecida da ferramenta** continua válida e recebe `nao_verificado`
  (ADR-0006), desde que tenha severidade.

### 7.2 Comparação por tipo de regra, não por igualdade textual

Cada regra conhecida tem **semântica própria**, definida no contrato em
`specs/baseline-compliance`: distribuição por igualdade sem diferenciar caixa, lista presente ou
ausente, versão mínima numérica, portas por endereço público ou interno, booleano e emissor de
chave. A tabela completa está no [TRD §7](../03-TRD.md).

- **Versões são comparadas por componente numérico** (`6.10` > `6.9`), nunca como texto.
- **"Endereço interno"** é loopback, RFC1918 (`10/8`, `172.16/12`, `192.168/16`), link-local e ULA
  `fc00::/7`. `0.0.0.0`, `::`, `*` e qualquer outro endereço são públicos.
- `ssh.login_de_root`: ver ADR-0009.

### 7.3 Formato das saídas e destino

- **JSON** (contrato com o Roster): `host`, `inventario`, `conformidade`, `resumo` (formato
  completo no [TRD §6.5](../03-TRD.md)). Convenções:
  - **campo não lido é `null`** no inventário, nunca `[]`, `0`, `false` nem `""`. Fatos em forma
    de objeto mantêm o objeto com folhas `null`, e os de forma de lista viram `null`. O **motivo**
    viaja na entrada de `conformidade` (`encontrado: null` + `motivo`);
  - `servicos[].nome` sem o sufixo, com `tipo` separado; `swap.tamanho` em bytes (swap desabilitado
    é `habilitado: false, tamanho: 0`, lido, diferente de `null`); `chaves_ssh[].identificacao` é o
    comentário ou o fingerprint, e **o material da chave nunca aparece**; `ntp.mecanismo` é
    `"nenhum"` quando não há mecanismo ativo;
  - em `conformidade`, `severidade` só em `desvio` e `motivo` só em `nao_verificado`;
    `resumo.por_severidade` conta apenas desvios.
- **Markdown** (para o plantão), que mostra **primeiro o que exige ação**: título
  `# Inventário — <hostname> (<endereco>)`, linha `Coletado em <data> · baseline v<versao>`,
  `## Desvios` (tabela Severidade | Regra | Esperado | Encontrado, ordenada crítico > alto > médio,
  mantendo a ordem do baseline dentro do mesmo nível), `## Não verificado` (tabela Regra | Motivo) e
  `## Conforme` (nomes separados por ` · `). O inventário completo fica no JSON.
- **Destino:** o relatório vai para **stdout** por padrão; `--formato {markdown,json}` escolhe qual
  (padrão `markdown`); `--saida-json ARQ` e `--saida-markdown ARQ` gravam em arquivo (as duas juntas
  geram os dois relatórios numa execução). **Mensagens de erro e diagnóstico vão só para stderr**,
  de modo que o stdout contém apenas o relatório e serve em pipe. Falha ao gravar um arquivo de
  saída é falha de execução (exit 2). Em falha de execução não há relatório, porque não há
  inventário.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Comparar tudo por igualdade textual** | Quase nenhuma regra é igualdade simples: `servicos.ativos` é "todos presentes", `servicos.proibidos` é "nenhum presente", `versao_minima` é numérica e `portas_em_escuta` tem duas semânticas. Sem a definição por tipo, cada regra viraria uma decisão silenciosa no meio do código (lacuna pega na Revisão 1) |
| **Layout próprio do baseline** (`regras: {<id>: {esperado, severidade}}`, severidades livres) | Foi o que a primeira implementação fez, e contradiz o enunciado, que versiona o arquivo e atribui a severidade **por nível**. Corrigido na Revisão 2 |
| **Markdown com resumo e uma tabela única com todas as regras** | Também a primeira versão. Obrigava a procurar o problema no meio do inventário inteiro, quando o plantão precisa ver os desvios primeiro |
| **Estender o JSON com o motivo no `inventario`** | O formato é contrato externo do Roster e não é estendido nesta fatia |

## Consequências

**Positivas**

- Cada regra tem um veredito defensável e testável, e o relatório diz o que causou o desvio.
- O plantão lê primeiro o que exige ação, e o Roster recebe um formato estável.
- Um erro de digitação no baseline é pego como baseline inválido, em vez de gerar uma regra sem
  severidade.

**Negativas e riscos aceitos**

- O formato do JSON é **contrato externo**: qualquer mudança é uma negociação com o Roster.
- Um fato não lido que nenhuma regra do baseline referencia aparece como `null` **sem motivo** no
  `inventario`. O baseline oficial referencia todos os fatos coletados, então o motivo sempre
  aparece em `conformidade`.
- `aplica_a` é só informativo nesta fatia: nada impede rodar um baseline contra um host que ele não
  descreve.

## Verificação

- `tests/test_compliance.py` (tarefas 6.5 a 6.9, por tipo de regra), `tests/test_baseline.py`
  (layout e severidades), `tests/test_inventory_report.py` (formatos) e `tests/test_cli.py`
  (`DestinoDasSaidasTest`, tarefa 7.3).
- Laboratório: `relatorio-baseline-oficial.json` com `resumo.por_severidade` batendo com os desvios.
