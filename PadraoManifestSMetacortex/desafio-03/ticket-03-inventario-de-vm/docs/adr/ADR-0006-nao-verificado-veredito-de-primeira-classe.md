# ADR-0006 — `nao_verificado` como veredito de primeira classe

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`) |
| **Origem** | `design.md` D6; brainstorm §4.1 |
| **Relacionados** | [ADR-0003](ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md), [ADR-0007](ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md), [ADR-0010](ADR-0010-codigos-de-saida-0-1-2.md) |

## Contexto

A fatia 1 sempre coleta com **usuário comum (não root)**. Algumas regras do baseline são
sabidamente inverificáveis nesse modo. O caso típico é a política efetiva de login de root no SSH,
que exige `sshd -T` (ou uma configuração legível só por root). No laboratório, `sshd -T` com
usuário comum responde `no hostkeys available -- exiting`, então `ssh.login_de_root` nasce
inverificável. Esse é exatamente o caso que o ticket quer ver tratado.

O risco central é o **falso conforme**: pior que falhar é dizer que está tudo bem.

## Decisão

O motor de conformidade trata "não foi possível verificar" como um **veredito distinto e sempre
honesto**, `nao_verificado`, **com motivo declarado**, e não como caminho de erro. Há **duas
origens**, ambas com motivo explícito e **nenhuma resultando em `conforme`**:

1. o fato foi coletado, mas marcado como **não lido** (por exemplo, falta de privilégio);
2. a regra do baseline referencia um fato que a **coleta simplesmente não produz** (regra que a
   ferramenta não sabe avaliar, ou fato fora do inventário da fatia 1).

O motivo diferencia as situações que se parecem: o dado lido e fora do padrão (`desvio`), o comando
que existe mas negou acesso, e o comando que não existe no host. A ação corretiva de cada uma é
diferente.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Falhar a execução inteira quando qualquer regra não puder ser verificada** | Uma fonte comum de regras inverificáveis (privilégio limitado) tornaria a ferramenta inutilizável para o seu uso principal, a varredura sem privilégio |
| **Leitura estática de melhor esforço** (por exemplo, `grep` em `sshd_config`) reportada como `conforme` ou `desvio` | A leitura de um arquivo de configuração **não é o mesmo fato** que a configuração efetiva do daemon: arquivos `Include` de drop-in, múltiplos blocos `Match` e defaults compilados podem mudar o valor efetivo. Poderia ler `PermitRootLogin no` num arquivo enquanto o `sshd -T` reporta outra coisa. Reportar isso como `conforme` seria uma afirmação falsa, o que a proposta proíbe explicitamente |

## Consequências

**Positivas**

- A ferramenta continua útil sem privilégio, e a lacuna aparece em cada relatório, com motivo.
- Um fato que ninguém leu nunca vira `conforme`.

**Negativas e riscos aceitos**

- **`nao_verificado` não gera exit 1** (ADR-0010). Um baseline cheio de regras não verificáveis pode
  sair com exit 0 sem ter verificado quase nada. Aceito na fatia 1: o veredito e o motivo aparecem
  em cada entrada, e o critério de aceite 1 exige, no laboratório, que **todas** as entradas sejam
  `conforme`, e não apenas a ausência de `desvio`. Se o time quiser bloquear auditoria incompleta,
  é uma mudança futura (PRD, questão Q1).
- O JSON do Roster não tem campo de motivo para um fato não lido no `inventario`. O motivo viaja na
  entrada de `conformidade` (`encontrado: null` + `motivo`).

## Verificação

- Laboratório: `ssh.login_de_root` sai `nao_verificado`, com motivo (`sshd -T` falha sem
  privilégio), em `relatorio-baseline-oficial.*`.
- `tests/test_compliance.py`: `TresVereditosTest` e os casos de regra sem fato coletado.
