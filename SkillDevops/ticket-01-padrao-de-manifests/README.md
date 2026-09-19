# Ticket 01 — O padrão do Seraph que ninguém abre

Skill `metacortex-manifests`: empacota o Padrão de Manifests da Metacortex em dois modos,
**escrever** um manifesto novo no padrão e **conferir** um manifesto existente. O que é mecânico
virou script; o que exige ler o projeto virou instrução.

## Mapa da entrega

| Pedido do ticket | Onde está |
|---|---|
| A skill completa (corpo, script, apoio) | `skill/metacortex-manifests/` (e `metacortex-manifests.skill`, empacotada) |
| A origem da skill | seção "Origem" abaixo + `fluxo-de-origem/` |
| Saída real: manifests gerados (fake-shop) | `execucoes/01-escrita-fake-shop/` |
| Saída real: conferência do manifesto barrado (nyx) | `execucoes/02-conferencia-nyx/` |
| A curadoria | `curadoria.md` |
| O padrão usado | `padrao-assumido/` (ver aviso abaixo) |

```
ticket-01-padrao-de-manifests/
├── README.md
├── curadoria.md
├── padrao-assumido/Padrao-de-Manifests-da-Metacortex-ASSUMIDO.md
├── fluxo-de-origem/            # o que foi rodado à mão antes da skill existir
├── skill/metacortex-manifests/
│   ├── SKILL.md
│   ├── scripts/conferir.py
│   ├── scripts/trivyignore
│   ├── references/padrao.md
│   ├── references/decisoes.md
│   └── assets/modelo-app.yaml
├── metacortex-manifests.skill
└── execucoes/
    ├── 01-escrita-fake-shop/   # manifests/orion-prod/, decisoes.md, conferencia-final.md
    └── 02-conferencia-nyx/     # relatorio-conferencia.md, conferencia-script.md, correcao-proposta/
```

> **Aviso sobre o padrão.** O anexo oficial `Desafio 03 - Anexo - Padrao de Manifests da
> Metacortex.md` não estava disponível durante a resolução. O padrão foi reconstruído nos quatro
> blocos descritos no ticket, com IDs estáveis por regra. Trocar pelo oficial significa ajustar
> `references/padrao.md` e o dicionário `REGRAS`/checagens em `conferir.py`; o método, a
> divisão script/instrução e os dois modos não mudam.

## Origem

- **De qual fluxo nasceu.** Da execução manual das duas tarefas do ticket antes de qualquer skill
  existir: ler os projetos kube-news e fake-shop, rodar `trivy config` e `trivy fs --scanners
  secret` no manifesto barrado, sondar o catálogo do Trivy com manifests construídos para isso e
  validar com kubeconform. Esses passos mostraram, com saída real, o que o Trivy cobre e o que
  não cobre, e isso virou o escopo exato do script. Detalhes e saídas em `fluxo-de-origem/`.
- **Por qual caminho.** Fluxo manual → classificação regra por regra (mecânica, contextual, não
  empacotar) → script cobrindo só a lacuna do Trivy → SKILL.md com os dois modos e o checklist de
  leitura → execução da skill nos dois modos → ajustes no script e no modelo a partir do que as
  execuções revelaram (registrados em `curadoria.md` §8) → validação da estrutura
  (`quick_validate`) e empacotamento (`package_skill`).
- **Com qual ferramenta.** Claude (claude.ai, modelo Claude Opus 5) com execução de código num
  container Linux, seguindo o guia `skill-creator` da Anthropic para anatomia da skill
  (frontmatter, `scripts/`, `references/`, `assets/`, carregamento progressivo). Ferramentas
  usadas no fluxo: Trivy 0.74.0, kubeconform 0.8.0, Python 3 + PyYAML, git.

## Instalar e usar

```bash
# Claude Code: skill pessoal ou do projeto
cp -r skill/metacortex-manifests ~/.claude/skills/        # ou .claude/skills/ no repositório
# requisitos na máquina: python3 + pyyaml, trivy
```

Pedidos que disparam: "esse manifesto está no padrão da casa?", "revisa esse deployment antes de
eu subir", "gera os manifests do fake-shop pro orion".

O script também roda sozinho, por exemplo num pipeline:

```bash
python3 skill/metacortex-manifests/scripts/conferir.py manifests/ --json conferencia.json
# código de saída: 0 sem falhas · 1 com falhas · 2 erro de leitura
```

## Resultado das duas execuções

| Execução | Entrada | Resultado |
|---|---|---|
| Escrita | fake-shop, cliente orion, prod | 11 recursos em 5 arquivos; `conferir.py` com **0 falhas** (código de saída 0); kubeconform válido; 9 itens contextuais resolvidos com evidência; 4 achados para o cliente (incluindo cartão e CVV gravados em texto) |
| Conferência | manifesto barrado do nyx | **BARRADO**: 28 falhas, sendo 3 quebras funcionais (nome rejeitado pela API, Service sem endpoints, app não lê `DATABASE_URL`, esta última descoberta só lendo o kube-news); correção proposta com 1 pendência intencional (NetworkPolicy depende do dono do banco) |
