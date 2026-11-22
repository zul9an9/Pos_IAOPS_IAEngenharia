# ADR-0009 — `PermitRootLogin prohibit-password` conta como root habilitado

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`), tomada **durante a implementação** |
| **Origem** | `design.md` D9 |
| **Relacionados** | [ADR-0006](ADR-0006-nao-verificado-veredito-de-primeira-classe.md), [ADR-0007](ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md) |

## Contexto

`sshd -T` devolve, para `PermitRootLogin`, um destes valores efetivos: `yes`, `no`,
`prohibit-password` (antigo `without-password`) ou `forced-commands-only`. A regra
`ssh.login_de_root` do baseline é **booleana**, então é preciso decidir como os quatro valores se
mapeiam em `true` e `false`.

Rodando o coletor **como root** no WSL do laboratório, o `sshd -T` devolve `prohibit-password`,
que ainda **permite login de root por chave**. Essa é a diferença entre spec e implementação que o
arco existe para expor: só aparece rodando contra um host real, e muda o veredito.

## Decisão

Para `ssh.login_de_root`, **só o valor efetivo `no` é `false`; qualquer outro é `true`**, inclusive
`prohibit-password`. Consequência: com o baseline pedindo `login_de_root: false` e o host
reportando `prohibit-password`, o veredito é **`desvio`**. O valor efetivo cru do `sshd` aparece em
`encontrado` da regra.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Tratar `prohibit-password` como `false`** | Esconderia um desvio real: root continua acessível por chave. Seria um falso conforme |

## Consequências

**Positivas**

- A regra não deixa passar uma exposição real de root.
- O valor efetivo cru fica registrado em `encontrado`, e quem lê o relatório vê **qual** valor
  causou o desvio.

**Negativas e riscos aceitos**

- Um parque que usa `prohibit-password` de propósito (acesso de root só por chave) verá esse host
  como desvio da regra `login_de_root: false`. Para aceitar esse estado, o baseline teria de mudar
  a expectativa, e não a ferramenta.
- Só se aplica quando o fato foi **lido**. Sem privilégio, a regra continua `nao_verificado`
  (ADR-0006), e é o caso do laboratório com usuário comum.

## Verificação

- `tests/test_compliance.py`: mapeamento `{"no": False, "yes": True, "prohibit-password": True,
  "forced-commands-only": True}` e o caso `prohibit-password` com esperado `false`, que resulta em
  `desvio` e `valor_efetivo` preservado.
- `tests/test_inventory_report.py` (conversão do valor efetivo em booleano) e
  `tests/test_coletor.py::LoginRootComPrivilegioTest` (ramo com privilégio).
