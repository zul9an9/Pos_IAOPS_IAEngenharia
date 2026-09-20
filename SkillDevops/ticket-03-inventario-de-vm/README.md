# Ticket 03 — O Roster que ninguém consegue manter

Ferramenta `vminv`: roda na máquina de quem opera, entra numa VM por SSH com usuário comum,
levanta o retrato real do host e o compara, regra a regra, com o `baseline.yaml` do parque,
apontando cada desvio e sua gravidade. **Só lê**, e a **chave privada nunca aparece** em
saída, log ou erro.

## Mapa da entrega

| Pedido do ticket | Onde está |
|---|---|
| Documentos de especificação produzidos | `docs/01-brainstorm.md` e `openspec/changes/archive/2026-09-20-vm-inventory-drift/` (proposal, design, specs) |
| Artefatos do ciclo do OpenSpec (proposta, tarefas, specs, arquivado) | `openspec/` — `changes/archive/…` com o change fechado e `specs/` com as duas capacidades promovidas |
| O código | `vminv/` (Python 3, só stdlib) e `tests/` (210 testes) |
| Evidência de execução real contra host Linux por SSH | `laboratorio/` |
| Curadoria | `curadoria.md` |

```
ticket-03-inventario-de-vm/
├── README.md · curadoria.md
├── docs/01-brainstorm.md          # primeiro artefato: escopo, decisões, riscos, aceite
├── docs/README-ferramenta.md      # uso, argumentos, códigos de saída
├── openspec/
│   ├── changes/archive/2026-09-20-vm-inventory-drift/  # proposal, design (D1–D9), tasks (47), specs
│   └── specs/{inventory-collection,baseline-compliance}/spec.md
├── vminv/                         # cli, ssh_transport, collector.sh (POSIX), inventory,
│                                  # baseline (parser YAML mínimo), compliance, report, errors
├── tests/                         # um arquivo por área + test_laboratorio.py (host real)
├── baseline.exemplo.yaml          # o baseline do enunciado, v1
└── laboratorio/                   # relatórios e evidências das execuções reais
```

## Como rodar

```bash
python -m vminv --host <ip> --usuario <user> --chave <caminho> --baseline baseline.exemplo.yaml \
  --saida-json relatorio.json --saida-markdown relatorio.md
# 0 = sem desvio · 1 = com desvio · 2 = falha de execução
```

Sem dependências: Python 3.10+ e o cliente `ssh` do sistema. Detalhes em
`docs/README-ferramenta.md`.

## Evidência de execução (host real, por SSH)

Host: Ubuntu 26.04 em WSL2, `orpheu@172.29.2.241:22`, usuário comum, chave ed25519
`platform@metacortex-platform`. Arquivos em `laboratorio/`.

| Critério de aceite | Evidência | Resultado |
|---|---|---|
| Host conforme sai sem desvio | `relatorio-reduzido.*`, `evidencias-aceite.txt` §1 | "Nenhum desvio", **exit 0** |
| Desvios classificados pela severidade do baseline | `relatorio-baseline-oficial.*` | **exit 1**, 2 críticos e 1 alto: swap habilitado, `9100` fora da rede interna, `containerd`/`node_exporter` ausentes |
| Regra não verificável, distinta de conforme | idem | `ssh.login_de_root` → `nao_verificado`, motivo: `sshd -T` falha sem privilégio |
| Host inalcançável e chave recusada | `evidencias-aceite.txt` §4 e §4b | **exit 2**, mensagem em linguagem simples, sem stack trace |
| Execução repetida devolve o mesmo retrato | `run1.json` × `run2.json`, `evidencias-aceite.txt` §5 | diff campo a campo: só `host.coletado_em` muda |
| Só leitura | tarefa 3.9 | unidades systemd ativas, `/proc/swaps`, `ss -ltn` e `authorized_keys` idênticos antes e depois |

Resumo do JSON oficial: `{"conforme": 7, "desvio": 3, "nao_verificado": 1,
"por_severidade": {"critico": 2, "alto": 1, "medio": 0}}`.

## Como o arco foi percorrido

1. **Brainstorm** (`docs/01-brainstorm.md`): escopo, o que fica de fora, decisões com
   alternativas, riscos e critérios de aceite. Nenhum código.
2. **`/opsx:propose`**: proposta, design, duas specs e 43 tarefas.
3. **Revisão 1, antes de qualquer código**: 10 correções, entre elas as três lacunas de
   contrato que o implementador preencheria sozinho (semântica de comparação por tipo de regra,
   validação do `versao` do baseline e regra sem fato coletado).
4. **`/opsx:apply`**: implementação e testes.
5. **Revisão 2, contra o enunciado**: layout do baseline, conjunto fechado de severidades,
   formato do JSON e do Markdown, e a execução com o baseline oficial (que é o que prova o
   segundo critério de aceite).
6. **Validação** no laboratório e **`/opsx:archive`**.

O que as revisões encontraram e o que o agente entendeu diferente está em `curadoria.md`.
