# ADR-0003 — Atualização sob demanda, com carimbo de hora da coleta

| | |
|---|---|
| **Status** | Aceito |
| **Data da decisão** | 2026-09-27 (change `add-cluster-dashboard`) |
| **Origem** | `design.md` D3; `CURADORIA.md` §3.3. Constava do prompt do `/opsx:propose` como decisão já tomada pelo autor (D3) |
| **Relacionados** | [ADR-0005](ADR-0005-somente-leitura-em-tres-camadas.md), [ADR-0006](ADR-0006-erros-classificados-por-bloco.md) |

## Contexto

Durante um chamado, a pessoa precisa de **um retrato estável para ler**, não de uma tela que se
rearranja enquanto ela lê. O propósito do painel é encurtar os dez primeiros minutos: abre, vê o
retrato e age, sem carga contínua no apiserver.

## Decisão

A coleta é **sob demanda**. Cada coleta é um conjunto **finito** de chamadas `list`, pedido
explicitamente, e o **carimbo de hora** da coleta aparece em toda tela, o que torna auditável "de
quando é isto".

São gatilhos de coleta: **abrir o painel**, **clicar em Atualizar** e **trocar o namespace** (porque
os eventos dependem do namespace). Um namespace digitado manualmente, quando a listagem de namespaces
é negada, é gatilho como qualquer troca, depois de validado como rótulo DNS-1123.

**A busca por nome não é gatilho:** ela filtra a coleta atual no navegador. Cada listagem é
independente, para que a falha de uma não derrube as outras (ADR-0006).

## Alternativas consideradas

| Alternativa | O que se ganha | Por que foi rejeitada |
|---|---|---|
| **Polling em intervalo fixo** | A tela se atualiza sozinha | Carga contínua no apiserver sem benefício numa sessão curta de triagem, e a tela se rearranja enquanto se lê. Ainda precisaria de carimbo para responder "isto é atual?", então não ganha nada sobre o sob demanda |
| **Watch** | Menor atraso entre o cluster e a tela | Uma conexão longa tende a **ficar obsoleta em silêncio justamente quando cluster ou rede estão ruins**, que é a situação sob diagnóstico. Também exige manter estado reconciliado em memória: mais código e mais pontos de erro do tipo "ausente significa o quê", numa fatia que exclui histórico |

## Consequências

**Positivas**

- Um retrato estável, com carga mínima no apiserver, e cada coleta é auditável pelo carimbo.
- Nenhum estado reconciliado em memória.

**Negativas e riscos aceitos**

- **A tela pode ficar aberta e desatualizada.** Mitigação: o carimbo fica sempre visível no
  cabeçalho e não há temporizador escondido que desfaça a decisão. Exige um clique em **Atualizar**.

## Verificação

- `tests/test_somente_leitura.py::test_projeto_nao_tem_escrita_nem_watch`: o scanner barra
  `watch.Watch` e o argumento `watch=True`, **para a decisão não regredir**.
- `tests/test_servidor.py::test_get_faz_uma_coleta_e_envia_csp`.
- `tests/test_render.py::test_busca_filtra_no_navegador_sem_nova_coleta`: o campo de busca não tem
  `name` e o script não faz requisições nem usa temporizadores.
- Laboratório (tarefa 8.2): a busca reduz a lista sem nova coleta.
