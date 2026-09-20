# Curadoria — Ticket 03

O ticket pede duas coisas nesta seção: **onde o documento precisou ser corrigido durante a
implementação** e **o que o agente entendeu diferente do que foi escrito**. As duas têm
resposta longa, porque o arco foi percorrido de verdade e cada correção deixou rastro.

## 1. O caminho, e quem fez o quê

| Etapa | Quem | Artefato |
|---|---|---|
| Brainstorm | conversa no claude.ai | `docs/01-brainstorm.md` |
| Proposta, design, specs e tarefas | Claude Code, com `/opsx:propose` | `openspec/changes/.../` |
| **Revisão 1** (antes de qualquer código) | conversa no claude.ai | 10 correções, aplicadas com `/opsx:update` |
| Implementação | Claude Code, com `/opsx:apply` | `vminv/`, `tests/` |
| **Revisão 2** (contra o enunciado) | conversa no claude.ai | 7 correções, aplicadas com `/opsx:update` + `/opsx:apply` |
| Validação no laboratório | Claude Code e operador | `laboratorio/` |
| Arquivamento | Claude Code, com `/opsx:archive` | `openspec/specs/` e `changes/archive/` |

Nenhuma linha de código foi escrita antes do brainstorm e das specs. Foram 47 tarefas e 210
testes.

## 2. O que a primeira revisão pegou, antes de existir código

A proposta gerada estava boa, e ainda assim tinha **três lacunas de contrato** que o
implementador teria preenchido sozinho:

1. **A semântica de comparação por tipo de regra não existia.** A spec dizia "encontrado igual
   ao esperado", e quase nenhuma regra do baseline é igualdade simples: `servicos.ativos` é
   "todos presentes", `servicos.proibidos` é "nenhum presente", `versao_minima` é comparação
   numérica, e `portas_em_escuta` tem duas semânticas diferentes, uma para porta pública e
   outra para porta que só pode estar em endereço interno. Sem isso, cada regra viraria uma
   decisão silenciosa no meio do código.
2. **Não havia validação do campo `versao` do baseline.** Um baseline de versão futura seria
   interpretado "na esperança".
3. **Não havia regra para o caso "o baseline pede um fato que a coleta não produz".** O
   veredito correto é `nao_verificado`, e o risco era sair `conforme`.

E mais quatro ambiguidades: `bash -s` no design contra "POSIX" nas tarefas, `StrictHostKeyChecking`
citado sem política, "the key's path contents" misturando caminho e conteúdo da chave, e
nenhuma definição de onde as saídas seriam escritas. Havia ainda mistura de idioma: a proposta
em português, o resto em inglês.

## 3. O que o agente entendeu diferente do que foi escrito

Esta é a parte que o ticket cobra, e são casos distintos entre si.

**a) Inventou o layout do `baseline.yaml`.** Nenhum artefato definia o formato do arquivo, e o
agente criou um mapeamento `regras: { <id>: {esperado, severidade} }` com severidades livres
(`alta`, `critica`, `media`, `baixa`). O enunciado do ticket versiona esse arquivo e usa outro
formato: uma árvore `esperado`, com as severidades atribuídas **por nível**, em listas
invertidas (`critico`, `alto`, `medio`). O agente **sinalizou a escolha** ao entregar, em vez
de escondê-la, e a correção ficou restrita a `carregar_baseline`, como ele mesmo previra. Causa
raiz: o formato estava no enunciado e não foi transcrito para a spec, e o agente só enxerga a
spec.

**b) Inventou o formato das duas saídas.** Mesma causa. O JSON saiu sem `host` e sem `resumo`,
e o Markdown abria com um resumo e uma tabela única com todas as regras. O enunciado fixa um
Markdown escrito para o plantão: **Desvios primeiro**, depois Não verificado, depois Conforme
em uma linha. A diferença não é cosmética: o formato original obrigava a procurar o problema no
meio do inventário inteiro.

**c) Tratou o host do laboratório como Ubuntu 24.04**, porque foi o que o prompt dizia. A
máquina reporta **26.04**. O agente usou o valor real nos testes e deixou o documento como
estava; a correção foi explícita, porque documento que contradiz a realidade é dívida.

**d) Trouxe decisões que ninguém pediu, e estavam certas:** sem política de retentativa (o
plantão roda de novo), sem saída parcial durante a coleta, e sem camada de abstração de
transporte, já que existe um só. Ficaram registradas como não-objetivos no design.

## 4. Onde o documento precisou ser corrigido durante a implementação

Duas decisões nasceram do código e voltaram para o design:

**D8 — `-o IdentitiesOnly=yes`.** Sem isso, o cliente `ssh` também oferece as chaves do agente
e as chaves padrão do operador, então uma conexão poderia autenticar com **outra** chave que
não a passada em `-i`. O efeito mais grave não é funcional, é de **teste**: o caso "chave
recusada" passaria por engano, porque a chave errada autenticaria por outra identidade. Foi o
agente que percebeu, ao escrever o teste, e reportou como acréscimo fora da lista.

**D9 — `prohibit-password` conta como root habilitado.** Rodando o coletor como root no
laboratório, o `sshd -T` devolve `prohibit-password`, que ainda permite login de root por
chave. Tratar isso como `false` esconderia um desvio real. Só o valor efetivo `no` é `false`.

Essa é a diferença entre spec e implementação que o arco existe para expor: nenhuma das duas se
descobre lendo requisito, e as duas mudam o veredito da ferramenta.

## 5. O que o laboratório em WSL ensinou

O host não é uma VM do parque, e isso apareceu no resultado:
- o **kernel é o do WSL** (`6.18.33.2-microsoft-standard-WSL2`), e passa na regra de versão
  mínima por um motivo que não tem a ver com a política da distribuição;
- o **swap vem do host Windows**, e vira desvio crítico legítimo;
- `containerd` e `node_exporter` não existem, o que dá o desvio alto;
- a instância do WSL **encerra quando não há sessão aberta**, e leva o sshd junto. Durante os
  testes, uma janela `wsl -d Ubuntu` fica aberta representando a "VM ligada".

Nada disso invalida a validação: são desvios reais de um host real, e a ferramenta os reportou
com a severidade que o baseline declara.

## 6. Como as duas invariantes foram garantidas

**Só leitura**, em camadas:
- o coletor é um script `sh` POSIX sem nenhum comando que escreva, instale ou mude estado, com
  revisão estática listada em tarefa;
- o estado do host (unidades systemd ativas, `/proc/swaps`, `ss -ltn`, `authorized_keys`) foi
  comparado antes e depois da coleta, sem diferença;
- a comparação com o baseline roda no lado local, e um teste com dublê de transporte **falha**
  se a etapa de conformidade tentar falar com o host;
- duas execuções seguidas: o diff campo a campo do JSON acusa **apenas** `host.coletado_em`.

**A chave é credencial:**
- a ferramenta nunca abre o arquivo da chave; passa só o caminho no `-i` (pode fazer `stat`,
  para dizer "arquivo não encontrado" com clareza);
- nunca passa `-v` ao cliente `ssh`, e nunca repassa o stderr dele cru: as falhas são
  reclassificadas em categorias fixas;
- um teste procura o conteúdo da chave em toda saída capturada, em todos os caminhos de falha;
- `IdentitiesOnly=yes` garante que a chave usada é a informada, e não outra do agente.

## 7. Decisões abertas, e por que foram decididas assim

| Decisão | Escolha | Principal alternativa descartada |
|---|---|---|
| Linguagem | Python 3, só stdlib | Go (segunda linguagem e passo de build para um time de infra); paramiko (dependência num caminho de credencial, e a chave passaria a ser lida pelo nosso processo) |
| Transporte | subprocesso do `ssh` do sistema | biblioteca SSH em processo: mais controle, porém a chave cruza para o nosso espaço de memória e pode vazar em mensagem de exceção |
| Coleta | um script POSIX por stdin, numa conexão | um comando por dado: N conexões, mais lento, e o retrato deixa de ser de um único instante, o que quebraria a prova de idempotência |
| Comparação | local | no host: exigiria enviar o baseline para a VM (escrita) ou uma segunda passagem |
| Parser YAML | mínimo e próprio, que recusa o que não conhece | PyYAML: quebra o limite de "só stdlib" e, pior, interpreta construções que ninguém validou (a tipagem implícita do YAML transforma `no` em `False`), que é como um desvio real vira falso conforme |
| `nao_verificado` | veredito de primeira classe | falhar a execução inteira (inutiliza a coleta sem privilégio) ou ler o arquivo de configuração e reportar como conforme (não é o mesmo fato que a configuração efetiva, por causa de `Include`, `Match` e defaults) |

## 8. O que ficou para depois

- **Vários hosts por execução**: muda o desenho da saída e do tratamento de erro.
- **Correção de desvios**: é outro projeto, e outra autorização.
- **Integração com o Roster**: o JSON já sai no formato que ele consumiria.
- **Hosts sem systemd ou sem OpenSSH**: hoje os campos afetados saem como não lidos, com
  motivo, em vez de quebrar a coleta.
