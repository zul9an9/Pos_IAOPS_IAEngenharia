# Ticket 01 — O padrão do Seraph que ninguém abre

A skill `metacortex-manifests` empacota o **Padrão de Manifests da Metacortex (rev. 2026-07-29)**
em dois modos: **escrever** um manifesto novo já no padrão e **conferir** um manifesto existente.
O que é mecânico virou script, que roda o Trivy e confere o que o Trivy não conhece. O que exige
ler o projeto virou instrução.

## Mapa da entrega

| Pedido do ticket | Onde está |
|---|---|
| A skill completa (corpo, script, apoio) | `skill/metacortex-manifests/` e `metacortex-manifests.skill` (empacotada) |
| A origem da skill | seção "Origem" abaixo e `fluxo-de-origem/` |
| Saída real: manifests gerados (fake-shop) | `execucoes/01-escrita-fake-shop/` |
| Saída real: conferência do manifesto barrado (nyx) | `execucoes/02-conferencia-nyx/` |
| A curadoria (linha script/instrução, corpo × apoio, o que não entrou, permissões) | `curadoria.md` |
| O padrão usado | `padrao-oficial/` |

```
ticket-01-padrao-de-manifests/
├── README.md
├── curadoria.md
├── padrao-oficial/Padrao-de-Manifests-da-Metacortex.md
├── fluxo-de-origem/                 # o que foi rodado antes (e depois) da skill existir
├── skill/metacortex-manifests/
│   ├── SKILL.md
│   ├── scripts/conferir.py          # Trivy + regras da casa; código de saída para pipeline
│   ├── scripts/trivyignore          # 1 supressão justificada (KSV-0125)
│   ├── references/padrao.md         # regras, severidade, forma de conferência, mapa KSV
│   ├── references/decisoes.md       # sem health, migração, banco junto, diretórios graváveis
│   └── assets/modelo-app.yaml
├── metacortex-manifests.skill
└── execucoes/
    ├── 01-escrita-fake-shop/        # manifests/orion-prod/, decisoes.md, conferencia-final.md
    └── 02-conferencia-nyx/          # relatorio-conferencia.md, correcao-proposta/, variante-exemplo-do-padrao/
```

## Origem

- **De qual fluxo nasceu.** Da execução manual das duas tarefas antes de a skill existir:
  - ler o código do kube-news e do fake-shop;
  - rodar `trivy config` e `trivy fs --scanners secret` no manifesto barrado;
  - sondar o catálogo do Trivy com manifests construídos para isso;
  - validar com kubeconform.

  Essas saídas reais mostraram o que o Trivy cobre e o que não cobre, e isso virou o escopo
  exato do script.
- **Por qual caminho.**
  1. Fluxo manual.
  2. Classificação regra por regra (mecânica, contextual, não empacotar).
  3. Script cobrindo só a lacuna do Trivy.
  4. SKILL.md com os dois modos e o checklist de leitura.
  5. Execução nos dois modos.
  6. Ajustes.
  7. **Revisão completa quando o padrão oficial chegou**: a v1 tinha sido feita contra uma
     reconstrução, porque o anexo ainda não estava disponível (ver `curadoria.md` §7).
  8. Nova execução nos dois modos.
  9. Validação da estrutura e empacotamento.
- **Com qual ferramenta.** Claude (claude.ai, Claude Opus 5) com execução de código num container
  Linux, seguindo o guia `skill-creator` da Anthropic para a anatomia da skill (frontmatter,
  `scripts/`, `references/`, `assets/`, carregamento progressivo). No fluxo também foram usados
  Trivy 0.74.0, kubeconform 0.8.0, Python 3 com PyYAML e git.

## Instalar e usar

```bash
cp -r skill/metacortex-manifests ~/.claude/skills/     # ou .claude/skills/ no repositório
# requisitos: python3 + pyyaml, trivy
```

Pedidos que disparam a skill: "esse manifesto está no padrão da casa?", "revisa esse deployment
antes de eu subir", "gera os manifests do fake-shop pro orion".

O script roda também sozinho, por exemplo num pipeline:

```bash
python3 skill/metacortex-manifests/scripts/conferir.py manifests/ --json conferencia.json
# 0 = nenhuma falha · 1 = falha (obrigatório/proibido) · 2 = erro de leitura
```

## Resultado das duas execuções

| Execução | Entrada | Resultado |
|---|---|---|
| Escrita | fake-shop, cliente orion, prod | 7 objetos em 3 arquivos, mais o `SECRET.md`. Conferência: **1 falha**, a regra 2.3 no Postgres single-instance. Não é contornável sem dividir o banco, então segue como **pedido de exceção** a S&C, com opções e custos. 0 avisos. 12 itens contextuais resolvidos com evidência. Trivy cru: só o falso positivo de registry. kubeconform válido. Achado grave para o cliente: cartão e CVV gravados em texto. |
| Conferência | manifesto barrado do nyx | **BARRADO**, sem direito a exceção (violação de regras *proibidas*): 25 falhas e 2 avisos. Três delas derrubam o cliente: o nome é rejeitado pela API, o Service fica sem endpoint e o app não lê `DATABASE_URL`. A última só aparece lendo o kube-news, e o **exemplo "certo" do próprio padrão passaria na conferência mecânica e continuaria quebrado**. A correção proposta sai com 0 falhas e 0 avisos. |

