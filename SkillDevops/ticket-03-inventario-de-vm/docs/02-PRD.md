# PRD — vminv: inventário de uma VM e desvio em relação ao baseline

| | |
|---|---|
| **Produto** | `vminv`, ferramenta de linha de comando do Ticket 03 (cenário Metacortex) |
| **Fatia** | 1 (um host por execução) |
| **Estado** | Implementado e validado em laboratório; change `vm-inventory-drift` arquivado em 2026-09-20 |
| **Fontes** | `openspec/changes/archive/2026-09-20-vm-inventory-drift/` (`proposal.md`, `design.md`), `openspec/specs/`, `docs/01-brainstorm.md` e `laboratorio/` |
| **Consolidado em** | 2026-11-08, a partir das fontes acima. Nenhuma decisão nova foi introduzida neste documento |
| **Documentos irmãos** | [`03-TRD.md`](03-TRD.md) (como é construído) e [`adr/`](adr/README.md) (por que cada decisão técnica foi tomada) |

## 1. Resumo

O parque de VMs não tem uma forma barata de responder "este host está como deveria estar?". O
`vminv` entra em **uma** VM por SSH, levanta o retrato real da máquina e o compara, regra a
regra, com o `baseline.yaml` do parque. Para cada regra, ele aponta se o host está conforme, em
desvio (com a gravidade que o baseline atribui) ou se a regra não pôde ser verificada. O
relatório sai em JSON, para o Roster consumir, e em Markdown, para o plantão ler no terminal.

A ferramenta **só lê**, não exige privilégio no host e trata a chave privada como credencial.

## 2. Problema

O Roster é uma página mantida à mão que envelheceu. Ninguém sabe responder **quais VMs estão fora
do padrão** nem **quanto isso custa**. Cada desvio de configuração (swap habilitado, porta exposta
sem necessidade, login de root liberado, chave SSH esquecida) só é descoberto quando já virou
incidente.

Restrições do contexto, fixadas pelo ticket e não negociáveis:

- Não existe agente nas VMs e ninguém vai instalar um. O que existe em toda VM é acesso por chave.
- A ferramenta roda na máquina de quem opera, nunca no host auditado.
- A chave privada é uma credencial de cliente/produção.

## 3. Objetivos e não objetivos

### 3.1 Objetivos

1. Responder, por host e por regra, se o parque está conforme o baseline, com a severidade de cada
   desvio.
2. Funcionar **sem privilégio** no host, dizendo com honestidade o que não conseguiu verificar.
3. Produzir uma saída útil para duas audiências: máquina (JSON) e pessoa de plantão (Markdown).
4. Ter um código de saída que sirva num pipeline e que nunca confunda "não consegui auditar" com
   "auditei e está conforme".
5. Garantir, de forma verificável, as duas invariantes: **só leitura** e **chave privada nunca
   exposta**.

### 3.2 Não objetivos da fatia 1

| Fora de escopo | Motivo |
|---|---|
| Vários hosts por execução | Muda o desenho da saída e do tratamento de erro. Entra depois, e a fatia 1 não deve impedir isso |
| Correção automática de desvios | A ferramenta só lê. Corrigir é outro projeto e outra autorização |
| API ou banco do Roster | A integração é por JSON em arquivo ou stdout; o Roster consome quando existir |
| Descoberta de hosts | O endereço vem por parâmetro |
| Baseline versionado no tempo (migração entre versões) | A v1 declara `versao: 1` e a ferramenta recusa o que não souber ler |
| Windows como host auditado | O baseline é de VM Linux do parque |
| Retentativa de conexão, saída parcial durante a coleta e transportes plugáveis | Ver `design.md` (não objetivos de design) e o [TRD §12](03-TRD.md) |

## 4. Quem usa e como

| Quem | Como usa a ferramenta | O que precisa dela |
|---|---|---|
| **Plantão** | Roda no terminal, às três da manhã, contra uma VM suspeita | Um Markdown que mostre primeiro o que exige ação (desvios, por gravidade), depois o que não foi verificado, depois o que está conforme |
| **Pipeline / automação** | Roda como etapa e lê o código de saída | `0`, `1` e `2` com significados que levam a ações opostas |
| **Roster** (consumidor futuro) | Lê o JSON de arquivo ou stdout | Um formato estável, com `host`, `inventario`, `conformidade` e `resumo`, definido pelo enunciado |
| **Plataforma** (dona do baseline) | Mantém o `baseline.yaml` | Que um baseline malformado ou de versão desconhecida falhe de forma ruidosa, nunca produza vereditos silenciosamente errados |

## 5. Escopo da fatia 1

**Entrada:** endereço da VM, usuário SSH comum, caminho da chave privada e caminho do
`baseline.yaml`.

**Inventário coletado** (uma conexão, sem privilégio): identificação (endereço de conexão,
hostname reportado, instante da coleta), sistema operacional (distribuição e versão), kernel,
serviços ativos (distinguindo `.service` de `.socket`, com o estado), swap (habilitado e
tamanho), portas em escuta (endereço de vínculo e processo dono), chaves SSH autorizadas do
usuário que conectou (com identificação), configuração efetiva de login de root no SSH e
sincronização de tempo (mecanismo e estado).

**Regras do baseline v1 que a ferramenta sabe avaliar:** `so.distribuicao`, `so.versao_minima`,
`kernel.versao_minima`, `servicos.ativos`, `servicos.proibidos`, `swap.habilitado`,
`portas_em_escuta.publicas_permitidas`, `portas_em_escuta.somente_rede_interna`,
`chaves_ssh.emitidas_por`, `ssh.login_de_root` e `ntp.sincronizado`. Uma regra desconhecida recebe
`nao_verificado`, nunca `conforme`.

## 6. Requisitos funcionais

A coluna "Spec" aponta o requisito normativo em `openspec/specs/`.

| ID | Requisito | Spec |
|---|---|---|
| RF-01 | Cada execução trata **um único host** | inventory-collection: *Um Único Host por Execução* |
| RF-02 | A conexão usa o cliente `ssh` do sistema, com a chave informada só como caminho | inventory-collection: *Conexão SSH pelo Cliente do Sistema* |
| RF-03 | A verificação da chave do host é explícita: host desconhecido é recusado por padrão, e `--aceitar-host-novo` aceita só hosts **novos**, nunca chave alterada | inventory-collection: *Verificação da Chave do Host* |
| RF-04 | A coleta é feita por um script POSIX numa única sessão e devolve os fatos do inventário | inventory-collection: *Coleta por Script em Conexão Única* e os requisitos de dados (identificação, SO e kernel, serviços, swap, portas, chaves, login de root, tempo) |
| RF-05 | Todo fato que a coleta não conseguiu ler é marcado como **não lido** (`null` no inventário, com o motivo na entrada de conformidade), distinto de "lido e vazio" | inventory-collection: *Marcação de Campo Não Lido* |
| RF-06 | O baseline é lido por um parser mínimo que **recusa** toda construção que não sabe interpretar | baseline-compliance: *Parser Mínimo de Baseline* |
| RF-07 | O campo `versao` do baseline é validado antes de qualquer regra; versão ausente, desconhecida ou futura é falha de execução | baseline-compliance: *Validação da Versão do Baseline* |
| RF-08 | O layout do baseline é o do enunciado (`versao`, `aplica_a`, `esperado`, `severidade`), e a severidade é um conjunto fechado (`critico`, `alto`, `medio`) | baseline-compliance: *Layout do Baseline*, *Severidades Fechadas* |
| RF-09 | Cada regra do baseline gera **uma** entrada de conformidade com regra, esperado, encontrado e veredito | baseline-compliance: *Uma Entrada de Conformidade por Regra do Baseline* |
| RF-10 | Há três vereditos: `conforme`, `desvio` (com a severidade da regra) e `nao_verificado` (com motivo) | baseline-compliance: *Modelo de Três Vereditos* |
| RF-11 | A comparação segue a semântica de cada tipo de regra, nunca igualdade textual genérica | baseline-compliance: *Semântica de Comparação por Tipo de Regra* |
| RF-12 | Regra que referencia um fato que a coleta não produz é `nao_verificado` | baseline-compliance: *Regra sem Fato Coletado é nao_verificado* |
| RF-13 | O relatório sai em JSON (formato do Roster) e em Markdown (para o plantão), em stdout ou em arquivo | baseline-compliance: *Saída de Relatório em JSON*, *em Markdown*, *Destino das Saídas* |
| RF-14 | O código de saída é `0` (sem desvio), `1` (com desvio) ou `2` (falha de execução) | baseline-compliance: *Contrato do Código de Saída do Processo* |
| RF-15 | Toda falha de execução tem mensagem em linguagem simples, sem stack trace | baseline-compliance: *Mensagem de Falha de Execução*; inventory-collection: *Reporte de Falha de Conexão com o Host* |

## 7. Requisitos não funcionais e invariantes

| ID | Requisito | Como é garantido (resumo) |
|---|---|---|
| RNF-01 | **Só leitura no host.** Nenhum comando de escrita, instalação ou correção. O único rastro tolerado é o registro de login da própria sessão SSH | Coletor só com comandos de leitura, revisado por checklist (tarefa 3.9); estado do host comparado antes e depois; comparação feita localmente ([ADR-0003](adr/ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md), [ADR-0004](adr/ADR-0004-comparacao-local-nunca-no-host.md)) |
| RNF-02 | **A chave privada é credencial.** O conteúdo nunca aparece em stdout, stderr, arquivo de saída ou mensagem de erro, em nenhum caminho de falha | A ferramenta nunca abre o arquivo da chave, só passa o caminho ao `ssh` ([ADR-0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md)); teste que procura o conteúdo da chave em toda saída capturada |
| RNF-03 | **Idempotência.** Duas execuções seguidas contra o mesmo host dão o mesmo veredito por regra; só o instante da coleta varia | Sessão única ([ADR-0003](adr/ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md)); diff campo a campo de `run1.json` × `run2.json` |
| RNF-04 | **Nunca um falso conforme.** O que não foi lido com certeza é `nao_verificado`, e falha de execução nunca parece conformidade | [ADR-0006](adr/ADR-0006-nao-verificado-veredito-de-primeira-classe.md), [ADR-0010](adr/ADR-0010-codigos-de-saida-0-1-2.md) |
| RNF-05 | **Sem privilégio e sem dependências.** Python 3.10+ (só biblioteca padrão) e o cliente `ssh` do sistema | [ADR-0001](adr/ADR-0001-python-somente-biblioteca-padrao.md) |
| RNF-06 | **stdout limpo.** Só o relatório vai para stdout, e erros vão só para stderr, para que o stdout sirva em pipe | [ADR-0007](adr/ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md), seção 7.3 |
| RNF-07 | **Portabilidade do coletor.** `sh` POSIX, sem recursos exclusivos de `bash`, porque o `/bin/sh` do alvo pode ser `dash` | [ADR-0003](adr/ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md) |
| RNF-08 | **Falha ruidosa em baseline inválido**, nomeando a construção não suportada e a linha, em vez de um erro genérico | [ADR-0005](adr/ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md) |

## 8. Critérios de aceite

Os cinco critérios do ticket, como foram verificados. Os arquivos estão em `laboratorio/`.

| # | Critério | Evidência | Resultado |
|---|---|---|---|
| 1 | **Host conforme sai sem desvio.** Contra o host do laboratório, com um baseline reduzido que só tem regras que ele cumpre, a ferramenta sai com `0` e todas as entradas são `conforme` | `relatorio-reduzido.*`, `evidencias-aceite.txt` §1 | "Nenhum desvio", exit 0 |
| 2 | **Lacuna de privilégio é honesta.** `ssh.login_de_root` é `nao_verificado`, com motivo, e nunca `conforme` nem `desvio` | `relatorio-baseline-oficial.*` | `nao_verificado`: `sshd -T` falha sem privilégio |
| 3 | **Execução repetida devolve o mesmo retrato.** Duas execuções concordam em todos os vereditos | `run1.json` × `run2.json`, `evidencias-aceite.txt` §5 | Diff campo a campo: só `host.coletado_em` muda |
| 4 | **Falha de execução nunca parece conformidade.** Host inalcançável, host desconhecido, chave recusada e baseline inválido saem com `2` e mensagem clara | `evidencias-aceite.txt` §4 e §4b | exit 2, mensagem em linguagem simples, sem stack trace |
| 5 | **Desvios reais com a severidade do baseline.** Com o baseline oficial do enunciado, sai com `1`, cada desvio carrega a severidade que o baseline declara e `resumo.por_severidade` bate com os desvios | `relatorio-baseline-oficial.*` | exit 1: 2 críticos e 1 alto (swap habilitado, porta `9100` fora da rede interna, `containerd` e `node_exporter` ausentes) |

O resumo do JSON oficial é `{"conforme": 7, "desvio": 3, "nao_verificado": 1, "por_severidade":
{"critico": 2, "alto": 1, "medio": 0}}`. Para provar conformidade real, o critério 1 exige que **todas**
as entradas sejam `conforme`, e não apenas a ausência de `desvio`.

## 9. Premissas e dependências

- Python 3.10+ e o cliente `ssh` do sistema no `PATH` da máquina de quem opera.
- O parque alvo é Linux com systemd e OpenSSH. Um host sem alguma dessas ferramentas reporta os
  campos afetados como não lidos, com motivo.
- A chave do host precisa estar no `known_hosts` do operador antes da primeira execução, porque a
  política padrão recusa host desconhecido.
- Ambiente de validação: Ubuntu 26.04 em WSL2, acessível em `orpheu@172.29.2.241:22`, com usuário
  comum e chave ed25519 (`platform@metacortex-platform`). O host reporta 26.04 (o brainstorm
  citava 24.04, e a correção está na `curadoria.md`).
- O laboratório **não é uma VM do parque**: o kernel é o do WSL, o swap vem do host Windows e a
  instância encerra quando não há sessão aberta, levando o `sshd` junto. Isso foi registrado na
  evidência, e nada disso invalida a validação.

## 10. Riscos de produto

| Risco | Mitigação |
|---|---|
| **Falso conforme**, o pior defeito possível numa ferramenta de auditoria | `nao_verificado` é o veredito para tudo que não foi lido com certeza ([ADR-0006](adr/ADR-0006-nao-verificado-veredito-de-primeira-classe.md)) |
| **Vazamento da chave** | A chave nunca entra no processo, e há teste automatizado que procura o conteúdo em toda saída ([ADR-0002](adr/ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md)) |
| **Baseline cheio de regras não verificáveis sai com `0` sem ter verificado quase nada**, porque `nao_verificado` não gera `1` | Aceito na fatia 1: o veredito e o motivo aparecem em cada entrada, e o critério de aceite 1 exige `conforme` em todas as entradas. Ver questão aberta Q1 |
| **Parser YAML próprio rejeita um baseline legítimo, mas incomum** | Falha ruidosa e específica, nomeando a construção e a linha ([ADR-0005](adr/ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md)) |
| **Uma oscilação de rede vira falha completa (`2`)**, porque não há retentativa | Aceito na fatia 1: o operador reexecuta, e o `ConnectTimeout` é curto para a nova tentativa ser barata |
| **A regra de chaves cobre só o `authorized_keys` do usuário que conectou** | O escopo é declarado na spec e no relatório |
| **A convenção "emitida pela plataforma" não é garantia criptográfica**: é o comentário da chave | A ferramenta reporta a identificação encontrada; quem decide se a emissão é legítima é a plataforma |
| **Escopo crescendo** (multi-host, correção, integração com o Roster) | A fatia 1 entrega um host e sai |

## 11. Questões em aberto

| # | Questão | Estado |
|---|---|---|
| Q1 | `nao_verificado` deve ter um código de saída próprio, para o time bloquear uma auditoria incompleta? | Hoje `nao_verificado` não muda o código de saída. O brainstorm deixou a porta aberta, e a fatia 1 aceitou o comportamento atual |
| Q2 | O JSON do Roster não tem campo para o motivo de um fato não lido no `inventario`. Se o Roster precisar dele, é mudança de contrato | O formato é contrato externo e não foi estendido. O baseline oficial referencia todos os fatos coletados, e o motivo sempre aparece em `conformidade` |
| Q3 | Orientação de autoria do baseline, documentando o subconjunto de YAML suportado | Fora do escopo desta mudança. O parser já nomeia a construção recusada e a linha |

## 12. Evolução prevista

Fora da fatia 1: vários hosts por execução (muda a saída e o
tratamento de erro), integração com o Roster (o JSON já sai no formato que ele consumiria), e
suporte a hosts sem systemd ou sem OpenSSH (hoje os campos saem como não lidos, com motivo).
Correção de desvios não faz parte desta linha: é outro projeto, com outra autorização.

## 13. Rastreabilidade

| Pergunta | Documento |
|---|---|
| Como a ferramenta é construída? | [`03-TRD.md`](03-TRD.md) |
| Por que cada decisão técnica foi tomada? | [`adr/README.md`](adr/README.md) |
| Qual era o escopo antes da spec? | [`01-brainstorm.md`](01-brainstorm.md) |
| Qual é o contrato normativo? | `openspec/specs/inventory-collection/spec.md` e `openspec/specs/baseline-compliance/spec.md` |
| O que as revisões corrigiram e o que o agente entendeu diferente? | `../curadoria.md` |
| Como se usa? | [`README-ferramenta.md`](README-ferramenta.md) |
