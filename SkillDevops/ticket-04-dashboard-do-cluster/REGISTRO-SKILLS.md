# Registro das duas skills durante o Ticket 04

O enunciado pede quatro observações: quais skills dispararam sozinhas, quais
foram chamadas na mão, quais apareceram onde não deviam e o que precisou ser
reexplicado ao agente mesmo com as duas instaladas. Este registro separa o que
está comprovado nos arquivos do projeto do que só você pode confirmar.

## O que está comprovado nos artefatos

**As duas skills trabalharam juntas, em ciclo, sobre o cluster de laboratório.**
O Ticket 04 exigia subir pelo menos dois dos três projetos com os manifests do
Ticket 01. Os manifests em `manifests-lab/` (`orion-prod` para o fake-shop e
`helio-prod` para o encontros-tech) foram gerados pela `metacortex-manifests`.
Ao subir no cluster, três deles quebraram, e a `metacortex-triagem` foi o que
achou a causa de cada um. Os comentários "Correção pós-triagem" nos próprios
YAMLs registram isso:

| Onde | Sintoma | Causa achada pela triagem | O que mudou |
|---|---|---|---|
| fake-shop (`orion-prod`) | `Init:CreateContainerConfigError` | `runAsNonRoot: true` sem `runAsUser`; a imagem roda com usuário não numérico (`app`), e o kubelet não consegue provar que ele não é root | Usado o UID real da imagem, 10001:10001, que coincide com o default do padrão |
| fake-shop (`orion-prod`) | `CrashLoopBackOff` no initContainer `db-migrate` | `Read-only file system` em `/tmp/metrics`: o `flask db upgrade` importa o módulo do app, que escreve no diretório de métricas já no import | Mesmos `emptyDir` do container principal montados também no initContainer |
| encontros-tech (`helio-prod`) | `ImagePullBackOff` | O digest fixado resolvia para um índice OCI só com `linux/arm64`; o nó do kind é `amd64` | Trocada a tag por uma multi-arquitetura (`d2538f3`) que já roda como usuário não-root |

**O aprendizado voltou para a skill de manifests.** Os dois primeiros achados
viraram conteúdo permanente: `references/decisoes.md` ganhou a situação 4
(diretórios graváveis, "vale por container, não por aplicação"), citando o
`db-migrate` como "achado real em cluster, no Ticket 04", e o checklist de
leitura do `SKILL.md` ganhou a mesma observação. Os arquivos foram alterados em
2026-09-27, enquanto o `SKILL.md` da `metacortex-triagem` continua o de
2026-09-20: a triagem não precisou mudar, a de manifests aprendeu.

**Lacunas visíveis:**

- O terceiro achado (imagem só `arm64`) **não aparece** em `decisoes.md` nem no
  checklist. Uma regra "confira as arquiteturas do índice da imagem antes de
  fixar o digest" ainda não entrou na skill. *Isso é um achado que a skill
  ainda deve, e vale como item da curadoria.*
- O comentário do `fake-shop-app.yaml` cita `decisoes.md #5`, mas o arquivo
  tem quatro situações, e o assunto (`PROMETHEUS_MULTIPROC_DIR`) está na 4. O
  número ficou desatualizado depois que o conteúdo foi reorganizado.
- O `conferir.py` acusa `MC-ID-05` no laboratório pelo prefixo do registry
  (`registry.metacortex.io` ausente). É uma falha esperada e documentada no
  comentário, mas mostra que o script não distingue "laboratório" de "produção".

## O que só você pode preencher

- **Quais dispararam sozinhas:** [PREENCHER: por exemplo, ao pedir para
  investigar `orion-prod`, a triagem carregou sem você chamar?]
- **Quais você chamou na mão:** [PREENCHER]
- **Quais apareceram onde não deviam:** [PREENCHER: por exemplo, a
  `metacortex-manifests` carregando ao escrever o YAML de RBAC em
  `deploy/rbac/`, ou a `metacortex-triagem` ao abrir o painel. Se não houve
  nenhum caso, diga isso; é um resultado válido.]
- **O que você reexplicou repetidamente:** [PREENCHER: 2 ou 3 itens.
  Pergunta guia: o que você precisou repetir ao agente durante o ciclo do
  OpenSpec que nenhuma das duas skills sabe? Por exemplo, "só lê, nunca
  escreve" valia para o projeto inteiro, mas a skill de triagem só cobre isso
  para o uso do cluster pelo MCP, e não para o código do painel.]

## Uma observação para a curadoria

As duas skills foram feitas para operar o cluster (uma escreve manifests, a
outra lê o cluster). O painel é uma terceira coisa: código de aplicação
que mora ao lado delas. Nenhuma das duas cobre "desenvolver um projeto com
spec". O ciclo do OpenSpec (`.claude/skills/openspec-*` e `.claude/commands/opsx/`)
é que guiou essa parte. Isso é resultado, e não falha: a descrição de cada
skill acertou ao não reclamar esse território.
