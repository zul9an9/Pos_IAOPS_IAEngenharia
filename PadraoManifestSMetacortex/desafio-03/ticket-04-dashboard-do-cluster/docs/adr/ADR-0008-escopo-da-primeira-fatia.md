# ADR-0008 — Escopo da primeira fatia

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `proposal.md` (What Changes e Fora de escopo); `CURADORIA.md` §3.4. O escopo da fatia 1 constava do prompt do `/opsx:propose` |
| **Relacionados** | [ADR-0003](ADR-0003-atualizacao-sob-demanda.md), [ADR-0004](ADR-0004-endpointslice-agregado-por-service.md) |

> A comparação de alternativas deste ADR foi redigida a partir de `proposal.md` e `design.md`, como
> diz a própria `CURADORIA.md` §3.4. Se o raciocínio na época foi outro, este é o ADR a corrigir.

## Contexto

O enunciado diz que o objetivo do painel é **encurtar os primeiros dez minutos de um chamado**, não
substituir o terminal. O laboratório tem três chamados de naturezas diferentes (container, imagem e
Service sem endpoint) que o quadro precisa tornar visíveis.

## Decisão

A fatia 1 entrega: **namespaces, pods, deployments, services com endpoint, eventos do namespace,
filtro por namespace, busca por nome e os seis cenários adversos.**

**Fora de escopo:** logs, métricas de consumo, histórico, multicluster (troca de contexto) e **qualquer
escrita no cluster**.

## Alternativas consideradas

| Alternativa | O que se ganha | Por que foi rejeitada |
|---|---|---|
| **Só pods** | Mais rápido de entregar | O Chamado 3 (Service sem endpoint) ficaria invisível, e é o caso que o enunciado destaca |
| **Incluir logs e métricas** | Mais perto de substituir o terminal | Aumenta a permissão exigida (logs e métricas são outros recursos), estica o RBAC mínimo e a superfície a testar. O objetivo é encurtar os dez minutos, não substituir o terminal |
| **Troca de contexto na tela (multicluster)** | Conveniência de olhar vários clusters | Fora do escopo do ticket e amplia o risco de olhar (ou, no futuro, agir) no cluster errado. Quem quer outro cluster troca o contexto por fora |

## Consequências

**Positivas**

- Cobre o quadro dos "primeiros dez minutos" e os três chamados do laboratório.
- Superfície pequena, verificável e **sem escrita**.

**Negativas e riscos aceitos**

- Sem logs nem métricas: para a causa de um `CrashLoopBackOff` ainda é preciso o terminal (o
  `--previous` do `kubectl logs`).
- Quem quer outro cluster precisa trocar o contexto fora do painel e clicar em **Atualizar**.
- Não há limite superior de exibição numa coleta grande (PRD, Q1).

## Verificação

- `tests/test_render.py::test_nao_existe_seletor_de_contexto`.
- `tests/test_coleta.py::test_coleta_todos_os_namespaces_faz_exatamente_estas_chamadas` e
  `test_coleta_de_um_namespace_faz_exatamente_estas_chamadas`: só as listagens previstas.
- Laboratório (8.1): os três casos (`nyx-prod`, `orion-stg` e `nyx-stg`) aparecem na tela.
