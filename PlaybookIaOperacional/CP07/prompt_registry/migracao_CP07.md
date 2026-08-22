# Migração CP01–CP06 → prompt-registry (CP07)

Registro das decisões tomadas ao migrar os prompts do playbook da Aegis para o
formato do template [`prompt-registry`](https://github.com/fabricioveronez/prompt-registry).

## O que foi migrado

Oito prompts, todos na categoria `devops/` (casam com o escopo dela:
observabilidade, SRE, incidentes e segurança operacional):

| Origem | Pasta | Framework/técnica |
|--------|-------|-------------------|
| CP01 | `devops/triagem-de-pods/` | RISE |
| CP02 | `devops/nota-de-triagem-de-alerta/` | few-shot |
| CP03 | `devops/analise-de-causa-raiz/` | chain-of-thought dirigido |
| CP04 | `devops/decisao-de-backpressure/` | matriz de decisão |
| CP05 | `devops/migracao-lote-evento-1-diagnostico/` | prompt chaining (elo 1) |
| CP05 | `devops/migracao-lote-evento-2-plano/` | prompt chaining (elo 2) |
| CP05 | `devops/migracao-lote-evento-3-detalhamento/` | prompt chaining (elo 3) |
| CP06 | `devops/correcao-de-networkpolicy/` | meta-prompting + verificação/refino |

As pastas são nomeadas pelo **resultado**, não pela técnica (ex.: `triagem-de-pods`,
não `chain-of-thought`), conforme a convenção do template.

## Decisões de julgamento

1. **CP05 virou três pastas, não uma.** O CP05 é uma *cadeia* de três prompts,
   e o template define "um prompt por pasta" com um único bloco `inputs` no
   frontmatter — três conjuntos de parâmetros distintos não cabem num só. Cada
   elo virou um prompt válido e autocontido; o encadeamento é feito por
   parâmetro (`{{diagnostico}}` recebe a saída do elo 1, `{{plano}}` a do elo 2),
   que é exatamente como a cadeia já era acoplada. O prefixo numérico
   (`-1-`, `-2-`, `-3-`) preserva a ordem da cadeia na árvore de pastas.

2. **CP06 teve os placeholders normalizados para minúsculo.** O original usava
   `{{MANIFESTO_PERMISSIVO}}` etc.; foram convertidos para `snake_case`
   (`{{manifesto_permissivo}}`, `{{padrao_seguranca}}`, `{{mapa_servicos}}`,
   `{{provedor}}`) para seguir a convenção `{{nome_variavel}}` do registry e
   manter o campo `inputs` uniforme com os demais prompts.

## Versionamento

- Todo prompt nasce em `versao: 1.0.0` no frontmatter.
- Um commit semântico por prompt, escopo na categoria
  (`feat(devops): adiciona prompt de ...`), mais um `docs(devops)` para os
  índices — daqui pra frente, cada evolução passa por commit semântico e bump
  de `versao`.

## Invariantes garantidos na migração

- Frontmatter **idêntico** entre `prompt.md` e `README.md` de cada prompt.
- Todo placeholder `{{...}}` do corpo aparece em `inputs`, e vice-versa.
- Índices atualizados no `README.md` da categoria e no `README.md` raiz.
