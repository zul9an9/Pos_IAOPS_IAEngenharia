# ADR-0008 — `-o IdentitiesOnly=yes` na conexão SSH

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (change `vm-inventory-drift`), tomada **durante a implementação** |
| **Origem** | `design.md` D8 |
| **Relacionados** | [ADR-0002](ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) |

## Contexto

A decisão **nasceu do código** e voltou para o design. Sem `IdentitiesOnly=yes`, o cliente `ssh`
também oferece as identidades do **agente SSH** e as **chaves padrão** do operador (`~/.ssh/id_*`).
Uma autenticação poderia, portanto, ter sucesso com **outra** chave que não a informada em `-i`.

Isso quebra a premissa de que o host é acessado com a chave passada. O efeito mais grave não é
funcional, é de **teste**: o caso "chave rejeitada" passaria por engano, porque uma chave errada em
`-i` ainda autenticaria por outra identidade (um falso positivo). Foi o agente que percebeu, ao
escrever o teste, e reportou como acréscimo fora da lista de tarefas.

## Decisão

Incluir `-o IdentitiesOnly=yes` em **toda** conexão. Só a chave de `-i` é oferecida.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Não passar a opção** (comportamento padrão do cliente) | Permite autenticar com uma identidade diferente da informada, o que invalida o teste de chave rejeitada e a premissa de acesso com a chave passada |

## Consequências

**Positivas**

- A chave usada é a informada, e não outra do agente ou do operador.
- O teste de "chave recusada" passa a ser confiável.

**Negativas e riscos aceitos**

- Um operador que dependa do agente SSH (por exemplo, com chave protegida por senha carregada no
  agente) precisa passar a chave explicitamente em `--chave`. Em `BatchMode`, uma chave protegida
  por senha já é reportada como autenticação recusada.

## Verificação

- `tests/test_transport.py` (linha do `argv`): `IdentitiesOnly=yes` presente (D8).
- `tests/test_laboratorio.py::test_chave_errada_e_rejeitada_mesmo_com_chave_padrao_do_operador`.
