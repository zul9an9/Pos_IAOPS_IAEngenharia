# ADR-0007 — Tradução API → tela num módulo puro, testado com fixtures reais

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `design.md` D7; `CURADORIA.md` §3.6. Proposta pelo agente durante o `/opsx:propose` e aceita na revisão da spec |
| **Relacionados** | [ADR-0004](ADR-0004-endpointslice-agregado-por-service.md), [ADR-0006](ADR-0006-erros-classificados-por-bloco.md) |

## Contexto

O enunciado anuncia três armadilhas de dados: (a) **campo ausente não é campo vazio**, (b) **evento é
objeto próprio**, e (c) **"pronto" não é "saudável"**. Se o tratamento delas se espalhar pela
apresentação, cada coluna ganha um lugar diferente para errar. Além disso, o estado do laboratório
**muda**: `orion-prod` foi corrigido no dia da decisão, e `nyx-prod` continua acumulando reinícios
(155 na proposta, 163 e 164 na validação, algumas horas depois).

## Decisão

Um **módulo sem I/O** (`traducao.py`) recebe os objetos da API (o JSON cru) e devolve linhas prontas
para exibir, em texto cru. As três armadilhas vivem **só nele**:

- (a) valores semânticos para campo ausente, inclusive `spec.replicas` ausente → 1, para nunca sair
  `0/None`;
- (b) um evento, uma linha, com `count` e carimbos (com fallback para `eventTime` e `series` quando os
  campos legados faltam);
- (c) só os campos reportados, sem juízo de saúde.

As **fixtures** são capturadas do laboratório com `kubectl get -o json`, **uma operação de leitura**,
e versionadas em `tests/fixtures/`. Os casos: `nyx-prod` (`CrashLoopBackOff`, `OOMKilled`, 155
reinícios, evento `count` 429), `orion-stg` (0/3 sem `readyReplicas`), `nyx-stg` (`endpoints: null`),
`orion-prod` (2 prontos) e o slice de `nyx-prod` (2 endereços, 0 prontos).

O **cluster vivo continua sendo a validação final** (tarefas do grupo 8), mas não o único teste.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| **Tratar a ausência no template HTML** | Espalha `if campo existe` pela apresentação, com um lugar diferente para errar em cada coluna, e é difícil de testar sem renderizar |
| **Testar só contra o cluster vivo** | O estado do laboratório muda, então um critério de aceite que depende de estado mutável **não é reproduzível** |

## Consequências

**Positivas**

- Testes **determinísticos** das três armadilhas de dado, sem depender do cluster.
- A separação de responsabilidades é nítida: a tradução devolve texto cru, e só o renderizador
  escapa e monta HTML.

**Negativas e riscos aceitos**

- **Perde a fidelidade automática ao estado vivo**, compensada pelas tarefas do grupo 8.
- Um critério com número vivo precisa de cuidado: os testes verificam `155` e `429` **contra a fixture
  congelada**, e o registro de validação anota os valores vivos (163 e 164 reinícios, `count` 467 e 466).

## Verificação

- `tests/test_traducao.py` (22 testes): `test_pod_crashloop_nyx_prod`,
  `test_deployment_sem_ready_replicas_orion_stg`, `test_deployment_sem_spec_replicas_nem_ready`,
  `test_evento_repetido_e_uma_linha`, `test_evento_sem_count_e_sem_carimbos_legados`, entre outros.
- `tests/test_fixtures.py`: cada fixture traz o caso real esperado e não contém as senhas do
  laboratório.
- `tests/test_render.py::test_nenhum_termo_de_juizo_de_saude`: renderiza as fixtures e falha se o HTML
  contiver termos de juízo de saúde.
