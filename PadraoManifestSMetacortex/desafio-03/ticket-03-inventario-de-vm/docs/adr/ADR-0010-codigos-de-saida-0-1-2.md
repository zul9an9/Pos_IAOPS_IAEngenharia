# ADR-0010 — Códigos de saída: 0 (sem desvio), 1 (com desvio), 2 (falha de execução)

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-20 (brainstorm, formalizada na proposta e na spec) |
| **Origem** | Brainstorm D7 (`docs/01-brainstorm.md`); `proposal.md`; spec `baseline-compliance`: *Contrato do Código de Saída do Processo*. Não é uma decisão numerada do `design.md`, e entra aqui porque o brainstorm previa registrá-la como ADR |
| **Relacionados** | [ADR-0006](ADR-0006-nao-verificado-veredito-de-primeira-classe.md), [ADR-0007](ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md) |

## Contexto

O ticket exige um **código de saída que sirva num pipeline**. Num pipeline, "auditei e o host está
fora do padrão" e "não consegui auditar" levam a **ações opostas**: a primeira pede correção do
host, e a segunda pede ver por que a auditoria não rodou. Confundir as duas é o caminho para um
falso conforme.

## Decisão

| Código | Significado |
|---|---|
| `0` | Nenhum desvio (regras `conforme` ou `nao_verificado`) |
| `1` | Pelo menos um `desvio` |
| `2` | **Falha de execução**: host inalcançável, host desconhecido, chave recusada, baseline inválido, uso incorreto, resposta inválida do coletor, arquivo de saída não gravável |

- **Falha de execução nunca é confundida com host conforme.** Nesse caso não há relatório, porque
  não há inventário, e a mensagem vai só para o stderr, em linguagem simples e sem stack trace.
- **`nao_verificado` não muda o código de saída por si só.** Ele aparece no resumo e em cada
  entrada do relatório, com o motivo.
- Toda falha inesperada, inclusive exceção não prevista, também sai com `2`, sem detalhes internos.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Só `0` e `1`** | Some a diferença entre "auditei e está fora do padrão" e "não consegui auditar", que num pipeline significam ações opostas |
| **Código próprio para `nao_verificado`** (por exemplo, `3`) | Deixada em aberto no brainstorm, para o caso de o time querer bloquear auditoria incompleta. Não adotada na fatia 1 |

## Consequências

**Positivas**

- O pipeline distingue os três desfechos sem ler o relatório.
- O contrato é pequeno e estável, e o stdout limpo (só o relatório) permite usar a saída em pipe.

**Negativas e riscos aceitos**

- Um baseline cheio de regras `nao_verificado` sai com `0` sem ter verificado quase nada. Aceito
  na fatia 1 (ver ADR-0006). **Decisão a rever** se o time quiser bloquear auditoria incompleta
  (PRD, questão Q1).

## Verificação

- `tests/test_cli.py::CodigosDeSaidaTest` (tarefa 8.1) e `MensagensDeFalhaTest` (tarefa 8.2).
- Laboratório: exit `0` com o baseline reduzido, exit `1` com o baseline oficial e exit `2` para host
  inalcançável e chave recusada (`evidencias-aceite.txt`).
