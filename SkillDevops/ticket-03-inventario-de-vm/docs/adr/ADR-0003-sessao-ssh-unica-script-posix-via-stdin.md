# ADR-0003 — Sessão SSH única, com um script `sh` POSIX por stdin e uma resposta JSON

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`) |
| **Origem** | `design.md` D3; brainstorm D3 e D4 |
| **Relacionados** | [ADR-0002](ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md), [ADR-0004](ADR-0004-comparacao-local-nunca-no-host.md), [ADR-0006](ADR-0006-nao-verificado-veredito-de-primeira-classe.md) |

## Contexto

O inventário reúne vários fatos do host (SO, kernel, serviços, swap, portas, chaves, login de root,
tempo). Duas propriedades dependem de **como** eles são coletados: o **retrato pontual** exigido
pela spec e a **idempotência** (duas execuções seguidas devem concordar, variando só o instante da
coleta). Além disso, o host alvo pode ter `dash` como `/bin/sh`, e não deve ser exigido nada além
do POSIX.

## Decisão

1. **Uma única sessão SSH.** Todos os itens são coletados por **um único script**, entregue por
   **stdin** a `ssh ... sh -s`, que roda uma vez no host e imprime **um objeto JSON** em stdout. O
   script não é copiado para o host (nada é gravado lá).
2. **Interpretador `sh` (POSIX), não `bash`.** O script não usa bashismos (arrays, `[[ ]]`,
   `<( )`, `${var,,}` etc.).
3. **Cada fato é um envelope explícito.** O que o script consegue ler sai como
   `{"read": true, "value": ...}`, e o que não consegue (privilégio, ferramenta ausente etc.) sai
   como `{"read": false, "reason": "..."}`. Nunca `null` solto nem chave omitida, para que o lado
   local distinga "lido e vazio" de "não lido".
4. **O script só mede e reporta valores crus.** Ele não decide conformidade: a interpretação fica
   fora do host (ADR-0004).

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Uma conexão SSH por fato** | N conexões significam N idas e voltas (lento), e cada uma é uma chance de falha independente. Como o tempo passa entre elas, fatos como "portas em escuta" e "estado do swap" poderiam descrever o host em instantes diferentes, o que quebra o retrato pontual e a checagem de idempotência |
| **Texto bruto analisado no lado local** (em vez de o script emitir JSON) | Mais frágil a mudanças de formato das ferramentas do host (alternativa do brainstorm) |
| **Script em `bash`** | Exigiria `bash` no alvo. O POSIX cobre o necessário |

## Consequências

**Positivas**

- Retrato coerente de um único instante, e um só ponto de falha.
- Idempotência verificável: duas execuções se diferenciam só em `host.coletado_em`.
- Só leitura mais fácil de auditar: um único script, revisado por checklist.

**Negativas e riscos aceitos**

- O custo é um bloco de shell portável, que precisa tratar comando ausente e falta de privilégio
  **sem abortar**. Cada falha de leitura vira um fato não lido com motivo.
- Uma oscilação de rede durante a sessão derruba a coleta inteira (não há retentativa, ver TRD §12).
- Hosts sem systemd ou sem OpenSSH ficam com os campos afetados como não lidos, com motivo.

## Verificação

- `tests/test_transport.py::test_coleta_usa_subprocesso_com_script_por_stdin`.
- `tests/test_coletor.py`: `PosixTest` (sem bashismos), `RevisaoEstaticaSomenteLeituraTest` (tarefa
  3.9, só comandos de leitura) e `SentinelaTest` (fato não lido).
- Laboratório: `run1.json` × `run2.json` (diff campo a campo: só `host.coletado_em`) e o estado do
  host idêntico antes e depois da coleta.
