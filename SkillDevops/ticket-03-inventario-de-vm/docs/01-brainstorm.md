# Ticket 03 — Brainstorm: ferramenta de inventário e deriva de VM

**Estado:** amadurecimento de escopo. Nenhum código escrito.
**Data:** 20/09/2026

Este documento existe para que a spec não seja escrita no escuro e para que as decisões
técnicas fiquem registradas com as alternativas descartadas. Ele é o primeiro passo do arco
brainstorm → documentos de spec → ciclo do OpenSpec → implementação → validação.

---

## 1. O problema, em uma frase

O Roster é uma página mantida à mão que envelheceu, e ninguém sabe responder **quais VMs
estão fora do padrão** nem **quanto isso custa**. A primeira fatia da substituição é uma
ferramenta que roda na máquina de quem opera, entra numa VM por SSH, levanta o retrato real
daquele host e compara com o padrão declarado do parque.

## 2. O que está fechado pelo ticket (não é decisão nossa)

- **Roda na máquina de quem opera**, não no host auditado. Não existe agente nas VMs e
  ninguém vai instalar um. O que existe em toda VM é acesso por chave.
- **Entrada:** endereço da VM, usuário e chave privada.
- **Saída:** inventário + conformidade, nos **dois formatos**, JSON (para o Roster consumir) e
  Markdown (para o plantão ler no terminal às três da manhã).
- **Três vereditos:** `conforme`, `desvio` (com a severidade que o baseline atribui à regra) e
  `nao_verificado`.
- **Código de saída** que sirva num pipeline.
- **Duas invariantes:** a ferramenta **só lê**, e a **chave privada é credencial** — não
  aparece na saída, no log nem em mensagem de erro.
- **Os campos do inventário** e as quatro informações de cada entrada de conformidade (regra,
  esperado, encontrado, veredito) estão especificados no ticket, com exemplos de JSON e de
  Markdown.

## 3. Escopo da primeira fatia

**Dentro:**
- um host por execução;
- as regras do `baseline.yaml` versionado (v1);
- coleta por SSH com usuário comum;
- saída JSON e Markdown a partir do **mesmo dado**;
- comportamento definido para host inalcançável e para dado não coletável.

**Fora, e por quê:**
- **vários hosts em paralelo**: muda o desenho da saída e o tratamento de erro; entra depois,
  e a fatia 1 não deve impedir isso;
- **correção de desvios**: a ferramenta só lê; corrigir é outro projeto (e outra autorização);
- **API ou banco do Roster**: a integração é por JSON em arquivo ou stdout, e o Roster
  consome quando existir;
- **descoberta de hosts**: o endereço vem por parâmetro;
- **baseline versionado no tempo** (migração entre versões): a v1 declara `versao: 1` e a
  ferramenta recusa o que não souber ler;
- **Windows como host auditado**: o baseline é de VM Linux do parque.

## 4. As perguntas que decidem o desenho

### 4.1 O que é "o retrato real" quando a leitura exige privilégio?

O ticket já responde com o terceiro veredito, mas a ferramenta precisa **distinguir três
situações** que se parecem:
1. o dado foi lido e está fora do padrão → `desvio`;
2. o comando existe, mas negou acesso (ex.: `sshd -T` sem root) → `nao_verificado`, com motivo;
3. o comando não existe no host (ex.: sem `ss`, sem `systemctl`) → também `nao_verificado`,
   mas com outro motivo, porque a ação corretiva é diferente.

Confirmado no laboratório: `sshd -T` com usuário comum responde `no hostkeys available --
exiting`. Ou seja, a regra `ssh.login_de_root` nasce `nao_verificado` neste host, o que é
exatamente o caso que o ticket quer ver tratado.

### 4.2 Qual é a diferença entre "porta aberta" e "porta aberta para o mundo"?

O baseline separa `publicas_permitidas: [22]` de `somente_rede_interna: [9100]`. Então a
coleta precisa trazer, por porta, o **endereço de vínculo** e o **processo dono**, e não só o
número. `9100` em `0.0.0.0` e `9100` num endereço interno são conformidades diferentes. O
processo dono, aliás, é outro dado que costuma exigir privilégio.

### 4.3 Como saber se uma chave foi "emitida pela plataforma"?

A pista disponível é a **identificação** de cada chave autorizada: o comentário e a impressão
digital. No laboratório, a chave tem o comentário `platform@metacortex-platform`, que é o que
o baseline espera. Isso é uma convenção, não uma garantia criptográfica, e a spec deve dizer
isso com todas as letras: a ferramenta reporta a identificação encontrada; quem decide se a
emissão é legítima é a plataforma.

### 4.4 Serviço ou soquete?

O baseline proíbe `telnet.socket` e `rpcbind.socket`, que são **unidades de soquete**, não
serviços. A coleta precisa distinguir os tipos, senão a regra de proibidos nunca dispara.

### 4.5 O que significa "duas execuções seguidas devolvem o mesmo veredito"?

É a prova de que a ferramenta só lê. A comparação tem de ignorar o instante da coleta, e
apenas ele. Isso sugere que o **carimbo de tempo fique isolado** num único campo, e que a
validação compare o resto byte a byte.

## 5. Decisões técnicas (com as alternativas descartadas)

| # | Decisão | Escolha | Alternativas descartadas |
|---|---|---|---|
| **D1** | Linguagem | **Python 3, só biblioteca padrão** | `paramiko`: mais controle sobre a conexão, mas vira dependência e um `pip install` na máquina de quem opera. **Go**: binário único, ótimo para distribuir, mas adiciona uma linguagem e um passo de compilação para um time de infraestrutura que já vive em Python e shell. **Shell puro**: começa simples e degrada rápido na formatação do JSON e no tratamento de erro. |
| **D2** | Como falar com o host | **subprocesso do cliente `ssh` do sistema** | Biblioteca SSH: controle fino de exceções e da chave, ao custo da dependência. Com o cliente do sistema, a ferramenta herda `known_hosts`, agente e configuração corporativa, e **a chave privada nunca passa pelo nosso processo**: vai como caminho no `-i`. Custo: é preciso separar o stderr do cliente do erro do comando remoto e fixar `BatchMode=yes` e `ConnectTimeout`, para não travar pedindo senha. |
| **D3** | Estratégia de coleta | **um script de shell enviado por stdin, numa única conexão** | Um comando por dado: mapeamento trivial, porém N conexões (ou N execuções), mais lento e sujeito a retrato inconsistente no tempo. O script único dá um retrato coerente e um só ponto de falha; o custo é um bloco de shell portável, que precisa tratar comando ausente e falta de privilégio sem abortar. |
| **D4** | Formato de retorno do script remoto | **JSON impresso no stdout, montado pelo próprio script** | Texto bruto analisado no lado local: mais frágil a mudanças de formato das ferramentas. O script remoto emite um JSON com valores crus e marcações de "não pude ler"; a **interpretação** (comparar com o baseline, atribuir severidade) fica toda no lado local, que é onde vive o padrão. |
| **D5** | Onde mora a comparação | **no lado local, dirigida pelo `baseline.yaml`** | Comparar no host: exigiria enviar o baseline para a VM e confiar no que o host devolve já julgado. Manter a comparação local mantém a VM como fonte de fatos e a plataforma como fonte do padrão. |
| **D6** | Leitura do YAML | **um parser mínimo próprio, ou `pyyaml` se já estiver presente** | Exigir `pyyaml` contraria a D1. O baseline v1 é um subconjunto simples de YAML (mapas, listas, escalares), e a ferramenta recusa o que não souber ler, em vez de adivinhar. |
| **D7** | Códigos de saída | **0** sem desvios; **1** com desvios; **2** falha de execução (host inalcançável, chave recusada, baseline inválido, uso incorreto) | Usar só 0 e 1: some a diferença entre "auditei e está fora do padrão" e "não consegui auditar", que num pipeline significam ações opostas. `nao_verificado` **não** muda o código de saída por si só, mas aparece no resumo, na saída e (a decidir na spec) pode virar um código próprio se o time quiser bloquear auditoria incompleta. |
| **D8** | Segredo da chave | **nunca lida pelo processo**: só o caminho é repassado ao `ssh` | Ler a chave para passá-la a uma biblioteca aumenta a chance de vazamento em log e em traceback. Como reforço: a ferramenta não imprime a linha de comando completa, e trata exceções para não emitir `stack trace` cru. |

Decisões que ficam **para a spec**, não para o brainstorm:
- nomes exatos dos campos do JSON (o ticket já dá o formato, e ele é para seguir);
- texto e ordem das seções do Markdown;
- como o motivo do `nao_verificado` é redigido;
- nomes dos parâmetros de linha de comando.

## 6. Mapa: regra do baseline → o que coletar → risco

| Regra | Coleta | Risco/observação |
|---|---|---|
| `so.distribuicao`, `so.versao_minima` | `/etc/os-release` | comparação de versão precisa ser numérica, não textual (`22.04` × `9.04`) |
| `kernel.versao_minima` | `uname -r` | o valor traz sufixos (`6.18.33.2-microsoft-standard-WSL2`); só a parte numérica compara |
| `servicos.ativos` / `proibidos` | `systemctl list-units --type=service,socket` | distinguir `.service` de `.socket`; host sem systemd → `nao_verificado` |
| `swap.habilitado` | `/proc/swaps` (e tamanho, opcional) | no WSL o swap vem do host; é um desvio legítimo a reportar |
| `portas_em_escuta` | `ss -ltnp` | o processo dono só aparece com privilégio → a porta é lida, o dono pode faltar |
| `chaves_ssh` | `~/.ssh/authorized_keys` + `ssh-keygen -lf` | só as chaves do usuário da coleta; chaves de outros usuários exigem privilégio |
| `ssh.login_de_root` (efetivo) | `sshd -T` | **exige root**: confirmado que falha com usuário comum → `nao_verificado` |
| `ntp.sincronizado` | `timedatectl` | reporta também o mecanismo; sem systemd, cai para `nao_verificado` |
| `identificação` | endereço usado, `hostname`, instante da coleta | endereço da conexão e hostname reportado são campos **diferentes** de propósito |

## 7. Riscos

1. **Portabilidade do script remoto.** O que funciona no Ubuntu 24.04 pode não existir em
   outra imagem. Mitigação: testar a existência de cada comando antes de usar e cair em
   `nao_verificado` com motivo, nunca em erro.
2. **Falso conforme.** É o pior defeito possível numa ferramenta de auditoria: pior que falhar
   é dizer que está tudo bem. Mitigação: `nao_verificado` é o padrão de qualquer dado que não
   tenha sido lido com certeza.
3. **Vazamento da chave.** Mitigação: D8, mais um teste automatizado que procura o conteúdo da
   chave em toda a saída.
4. **O laboratório é WSL.** Kernel do WSL, swap do host e systemd recém-habilitado. Não
   representa uma VM do parque em tudo. Mitigação: registrar isso na evidência e, onde o
   comportamento do WSL mascarar uma regra, dizer qual.
5. **Escopo crescendo.** Multi-host, correção e integração com o Roster são convites. A fatia 1
   entrega um host e sai.

## 8. Critérios de aceite (do ticket, para a spec detalhar)

1. host conforme sai **sem desvio**;
2. host com desvios sai com **cada um classificado pela severidade** do baseline;
3. regra não verificável aparece como tal, **distinta de conforme**;
4. host inalcançável (endereço errado, chave recusada, SSH fora do ar) **falha com mensagem
   que diz o que ocorreu**, sem stack trace cru e sem ser confundido com host conforme;
5. execução repetida devolve **o mesmo retrato**, mudando apenas o instante da coleta.

Cada um deles vira um caso de validação com evidência: saída real, código de retorno e, no
caso 5, a comparação entre duas execuções.

## 9. Ambiente do laboratório

| Item | Valor |
|---|---|
| Host auditado | Ubuntu 24.04 no WSL2, systemd habilitado (`systemd=true` em `/etc/wsl.conf`) |
| Kernel | `6.18.33.2-microsoft-standard-WSL2` |
| Acesso | `orpheu@172.29.2.241:22`, chave ed25519 `platform@metacortex-platform` |
| Onde a ferramenta roda | Windows, com o cliente `ssh` do sistema |
| Particularidade | a instância do WSL encerra quando não há sessão aberta, e leva o sshd junto; durante os testes, uma janela `wsl -d Ubuntu` fica aberta |
| Desvios já esperados | serviços ausentes (containerd, node_exporter, chrony), swap do WSL, `ssh.login_de_root` não verificável |

## 10. Próximo passo

Escrever os **documentos de spec**:
- **spec de comportamento**: interface de linha de comando, contrato das duas saídas, os três
  vereditos, os códigos de saída e os cinco critérios de aceite em forma verificável;
- **spec de decisões (ADR)**: as decisões D1 a D8 acima, no formato contexto → decisão →
  consequências;

e só então abrir a proposta no ciclo do OpenSpec.
