# Desafio 03 (cenário Metacortex)

Quatro tickets do Desafio 03, um por pasta. Os dois primeiros são **skills** do Claude; os dois
últimos são **projetos** conduzidos com especificação (brainstorm → proposta → spec → OpenSpec →
implementação). Cada pasta tem o seu próprio `README.md` com o mapa da entrega e a sua
`curadoria` (ou `CURADORIA.md`).

## Os quatro tickets

| # | Ticket | Tipo | O que foi entregue | Resultado principal |
|---|---|---|---|---|
| 01 | [O padrão do Seraph que ninguém abre](ticket-01-padrao-de-manifests/) | Skill | `metacortex-manifests`: escreve e confere manifests contra o Padrão de Manifests da Metacortex (rev. 2026-07-29), com script que roda o Trivy e confere o que o Trivy não conhece | Manifesto barrado conferido: **BARRADO**, 25 falhas, 3 delas quebras funcionais. Manifests do fake-shop gerados com 1 falha legítima, que pede exceção |
| 02 | [Triagem no cluster](ticket-02-triagem-no-cluster/) | Skill | `metacortex-triagem`: método de triagem somente leitura, com medição de ganho e de roteamento entre as skills | Com × sem skill: **4/4 × 2/4** causas, US$ 0,58 × 1,28, **0 × 8** escritas no cluster. Matriz de roteamento: 10/10 frases após dois ajustes, 0 escritas em 26 sessões |
| 03 | [O Roster que ninguém consegue manter](ticket-03-inventario-de-vm/) | Projeto (OpenSpec) | `vminv`: entra numa VM por SSH com usuário comum, levanta o retrato real do host e o compara, regra a regra, com o `baseline.yaml`. Só lê, e a chave privada nunca aparece em saída, log ou erro | 210 testes; execução real contra host Linux por SSH, com saídas 0 (sem desvio), 1 (desvio) e 2 (falha de execução); change arquivado em 2026-09-20 Documentação em `docs/`: PRD, TRD e 10 ADRs |
| 04 | [Dashboard do cluster](ticket-04-dashboard-do-cluster/) | Projeto (OpenSpec) | `painel_cluster`: painel local e somente leitura (Python + HTML) com namespaces, pods, deployments, services e eventos | Cluster de laboratório subido com manifests gerados pela skill do ticket 01 e diagnosticado com a skill do ticket 02; validação em `validacao/` Documentação em `docs/`: PRD, TRD e 8 ADRs; change arquivado no OpenSpec |

## Agente e modelos usados

| # | Agente / ferramenta | Modelo(s) | Onde está registrado |
|---|---|---|---|
| 01 | Claude no **claude.ai**, com execução de código num container Linux, seguindo o guia `skill-creator` da Anthropic | Claude Opus 5 | [`ticket-01-padrao-de-manifests/README.md`](ticket-01-padrao-de-manifests/README.md), seção "Origem" |
| 02 | Claude no **claude.ai** para conduzir a triagem e escrever a skill; **Claude Code** em sessões limpas para medir roteamento e ganho (`rodar_sessao.py`) | Claude Opus 5 (claude.ai) · Claude Sonnet 5 (sessões do Claude Code) | [`ticket-02-triagem-no-cluster/README.md`](ticket-02-triagem-no-cluster/README.md), seção "Origem da skill", e os transcripts em `medicao-proc/` |
| 03 | **claude.ai** para brainstorm e revisões; **Claude Code** com os comandos `/opsx:*` do OpenSpec para proposta, implementação e arquivamento | Claude (modelo não registrado nos arquivos do repositório) | [`ticket-03-inventario-de-vm/curadoria.md`](ticket-03-inventario-de-vm/curadoria.md), tabela da seção 1 Documentação em `docs/`: PRD, TRD e 10 ADRs |
| 04 | **Claude Code** com os comandos `/opsx:*` do OpenSpec, usando as duas skills dos tickets 01 e 02 | Claude (modelo não registrado nos arquivos do repositório) | [`ticket-04-dashboard-do-cluster/REGISTRO-SKILLS.md`](ticket-04-dashboard-do-cluster/REGISTRO-SKILLS.md) Documentação em `docs/`: PRD, TRD e 8 ADRs; change arquivado no OpenSpec |

Nas 35 sessões do Claude Code medidas no ticket 02, o consumo registrado nos transcripts é quase
todo do Claude Sonnet 5 (cerca de US$ 3,39). O Claude Haiku 4.5 também aparece, com uso mínimo
(cerca de US$ 0,03 no total).

## Como os tickets se encadeiam

- O **ticket 01** produz a skill de manifests, e o **ticket 02** produz a skill de triagem. A
  matriz de roteamento do ticket 02 testa as duas juntas, e um dos ajustes dela voltou para a
  `description` da skill do ticket 01.
- O **ticket 04** usa as duas: os manifests do laboratório (`orion-prod`, `helio-prod`) saíram
  da skill de manifests, e a skill de triagem achou a causa de cada falha ao subi-los. Os
  achados voltaram para `references/decisoes.md` da skill do ticket 01.
- Os tickets **03 e 04** seguem o mesmo arco com OpenSpec e têm uma curadoria cada, sobre o que
  as revisões corrigiram e o que o agente entendeu diferente do que foi escrito.

## Estrutura

```
desafio-03/
├── README.md                                 # este arquivo
├── ticket-01-padrao-de-manifests/            # skill metacortex-manifests
├── ticket-02-triagem-no-cluster/             # skill metacortex-triagem + medição
│   └── relato-desafio-03-tickets-01-02.pdf   # relato do trabalho nos tickets 01 e 02
├── ticket-03-inventario-de-vm/               # vminv (OpenSpec)
└── ticket-04-dashboard-do-cluster/           # painel_cluster (OpenSpec)
```
