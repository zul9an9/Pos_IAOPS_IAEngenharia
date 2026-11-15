# Registros de decisão de arquitetura (ADRs) — vminv

Cada decisão técnica do Ticket 03 está num documento próprio, no formato
**Contexto → Decisão → Alternativas consideradas → Consequências → Verificação**.

As decisões vieram do `design.md` do change `vm-inventory-drift` (arquivado em 2026-09-20), onde
estão em forma resumida e numeradas de D1 a D9. Os ADRs mantêm essa numeração: **ADR-000N = DN**
para N de 1 a 9. O ADR-0010 vem do brainstorm. Os ADRs foram redigidos em 2026-11-08, sem introduzir
decisão nova.

## Índice

| ADR | Decisão | Status | Origem |
|---|---|---|---|
| [0001](ADR-0001-python-somente-biblioteca-padrao.md) | Python 3, somente biblioteca padrão | Aceito | `design.md` D1 |
| [0002](ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) | Cliente `ssh` do sistema via subprocesso, chave passada só como caminho | Aceito | D2 |
| [0003](ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md) | Sessão SSH única, script `sh` POSIX por stdin, uma resposta JSON | Aceito | D3 |
| [0004](ADR-0004-comparacao-local-nunca-no-host.md) | A comparação acontece localmente, nunca no host | Aceito | D4 |
| [0005](ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md) | Parser YAML mínimo e validação da versão do baseline | Aceito | D5 |
| [0006](ADR-0006-nao-verificado-veredito-de-primeira-classe.md) | `nao_verificado` como veredito de primeira classe | Aceito | D6 |
| [0007](ADR-0007-contrato-de-dados-baseline-comparacao-e-saidas.md) | Layout do baseline, comparação por tipo de regra e formato das saídas | Aceito | D7 |
| [0008](ADR-0008-identitiesonly-yes.md) | `-o IdentitiesOnly=yes` na conexão SSH | Aceito (nasceu na implementação) | D8 |
| [0009](ADR-0009-prohibit-password-conta-como-root-habilitado.md) | `prohibit-password` conta como root habilitado | Aceito (nasceu na implementação) | D9 |
| [0010](ADR-0010-codigos-de-saida-0-1-2.md) | Códigos de saída 0, 1 e 2 | Aceito | brainstorm D7; proposta e spec |

## Como as decisões se relacionam

```
ADR-0001 só stdlib ──► ADR-0002 ssh do sistema, chave só como caminho ──► ADR-0008 IdentitiesOnly
                                    │
                                    ▼
                       ADR-0003 sessão única, script POSIX
                                    │
                                    ▼
                       ADR-0004 comparação local ──► ADR-0007 contrato de dados ──► ADR-0009 login de root
                                    │                          │
ADR-0005 parser YAML mínimo ────────┴──────────────────────────┤
ADR-0006 nao_verificado ───────────────────────────────────────┴──► ADR-0010 códigos de saída
```

## Mapa para a numeração do brainstorm

O `docs/01-brainstorm.md` §5 numera as decisões de D1 a D8 numa ordem diferente da do
`design.md`. Para quem lê os dois:

| Brainstorm | Tema | ADR |
|---|---|---|
| D1 | Linguagem | [0001](ADR-0001-python-somente-biblioteca-padrao.md) |
| D2 | Como falar com o host | [0002](ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) |
| D3 | Estratégia de coleta | [0003](ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md) |
| D4 | Formato de retorno do script remoto | [0003](ADR-0003-sessao-ssh-unica-script-posix-via-stdin.md) |
| D5 | Onde mora a comparação | [0004](ADR-0004-comparacao-local-nunca-no-host.md) |
| D6 | Leitura do YAML | [0005](ADR-0005-parser-yaml-minimo-e-versao-do-baseline.md) |
| D7 | Códigos de saída | [0010](ADR-0010-codigos-de-saida-0-1-2.md) |
| D8 | Segredo da chave | [0002](ADR-0002-cliente-ssh-do-sistema-chave-so-caminho.md) |

## Convenções

- **Status:** `Proposto`, `Aceito`, `Substituído por ADR-NNNN` ou `Obsoleto`. Um ADR aceito não é
  reescrito: uma mudança de rumo vira um ADR novo que o substitui.
- **Arquivo:** `ADR-NNNN-assunto-em-minusculas.md`, com numeração sequencial.
- **Verificação:** cada ADR diz onde a decisão é testada ou comprovada (testes em `tests/`,
  evidências em `laboratorio/`).

## Documentos relacionados

- [`../02-PRD.md`](../02-PRD.md): o que a ferramenta faz e para quem.
- [`../03-TRD.md`](../03-TRD.md): como ela é construída.
- `../../openspec/specs/`: o contrato normativo.
- `../../curadoria.md`: o que as revisões corrigiram e o que o agente entendeu diferente.
