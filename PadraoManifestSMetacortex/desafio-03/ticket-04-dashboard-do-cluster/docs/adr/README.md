# Registros de decisão de arquitetura (ADRs) — painel_cluster

Cada decisão técnica do Ticket 04 está num documento próprio, no formato
**Contexto → Decisão → Alternativas consideradas → Consequências → Verificação**.

As decisões vieram do `design.md` do change `add-cluster-dashboard` (arquivado em 2026-11-08), onde
estão em forma resumida e numeradas de D1 a D7, e da `CURADORIA.md` §3, que compara cada uma com pelo
menos duas alternativas descartadas. Os ADRs mantêm a numeração do design: **ADR-000N = DN** para N
de 1 a 7. O ADR-0008 (escopo) vem da proposta. Os ADRs foram redigidos em 2026-11-08, sem introduzir
decisão nova.

## Índice

| ADR | Decisão | Status | Origem |
|---|---|---|---|
| [0001](ADR-0001-python-com-html-servido-localmente.md) | Python 3 com HTML servido localmente (descartados Go e TUI) | Aceito | `design.md` D1; `CURADORIA` §3.1 |
| [0002](ADR-0002-cliente-oficial-do-kubernetes.md) | Cliente oficial do Kubernetes (descartados `kubectl` e HTTP direto) | Aceito | D2; §3.2 |
| [0003](ADR-0003-atualizacao-sob-demanda.md) | Atualização sob demanda com carimbo de hora (descartados polling e watch) | Aceito | D3; §3.3 |
| [0004](ADR-0004-endpointslice-agregado-por-service.md) | EndpointSlice agregado por Service (descartados `Endpoints` e inferência pelo selector) | Aceito | D4; §3.5 |
| [0005](ADR-0005-somente-leitura-em-tres-camadas.md) | Garantia de somente leitura em três camadas | Aceito | D5; §3.6 |
| [0006](ADR-0006-erros-classificados-por-bloco.md) | Erros classificados por bloco, com mensagem por categoria | Aceito | D6; §3.6 |
| [0007](ADR-0007-traducao-em-modulo-puro-com-fixtures-reais.md) | Tradução API → tela em módulo puro, testado com fixtures reais | Aceito | D7; §3.6 |
| [0008](ADR-0008-escopo-da-primeira-fatia.md) | Escopo da primeira fatia | Aceito | `proposal.md`; §3.4 |

## Quem tomou cada decisão

Segundo o prompt do `/opsx:propose` e o registro da revisão do change (ver `CURADORIA.md` §2):

- **ADR-0001, 0002 e 0003** (D1 a D3) constavam do prompt como **decisões já tomadas pelo autor**:
  Python com HTML local, cliente oficial e atualização sob demanda.
- **ADR-0004** (D4) constava do prompt como decisão **a tomar**, com viés declarado para
  EndpointSlice, e foi fechada no design.
- **ADR-0008** (escopo) constava do prompt como o escopo da fatia 1.
- **ADR-0005, 0006 e 0007** (D5, D6 e D7) **nasceram do agente** durante o `/opsx:propose` e foram
  aceitas na revisão da spec.

## Como as decisões se relacionam

```
ADR-0001 Python + HTML local ─► ADR-0002 cliente oficial ─► ADR-0005 só leitura em 3 camadas
        │                                │                              ▲
        │                                └──► ADR-0006 erros por bloco  │
        ▼                                                               │
ADR-0003 sob demanda ───────────────────────────────────────────────────┘
        │                    (o teste da camada 2 barra watch)
        ▼
ADR-0004 EndpointSlice ─► ADR-0007 tradução pura + fixtures ◄─ ADR-0008 escopo
```

## Convenções

- **Status:** `Proposto`, `Aceito`, `Substituído por ADR-NNNN` ou `Obsoleto`. Um ADR aceito não é
  reescrito: uma mudança de rumo vira um ADR novo que o substitui.
- **Arquivo:** `ADR-NNNN-assunto-em-minusculas.md`, com numeração sequencial.
- **Verificação:** cada ADR diz onde a decisão é testada ou comprovada (testes em `tests/` e
  evidências em `validacao/`).

## Documentos relacionados

- [`../02-PRD.md`](../02-PRD.md): o que o painel faz e para quem.
- [`../03-TRD.md`](../03-TRD.md): como ele é construído.
- `../../openspec/specs/cluster-dashboard/spec.md`: o contrato normativo.
- [`../../CURADORIA.md`](../../CURADORIA.md): as comparações completas, e o que as revisões corrigiram.
