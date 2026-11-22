# Registro das duas skills durante o Ticket 04

O enunciado pede quatro observações: quais skills dispararam sozinhas, quais
foram chamadas na mão, quais apareceram onde não deviam e o que precisou ser
reexplicado ao agente mesmo com as duas instaladas. Este registro separa o que
está comprovado nos arquivos do projeto do que vem do relato das sessões.

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

## O que o relato das sessões mostra

**Fonte e limite.** Esta seção vem dos relatos finais do agente nos três pedidos de
laboratório, que terminavam com "diga quais skills dispararam" e foram
acompanhados na conversa de 2026-09-27. As sessões do Claude Code **não estão no
repositório**: o que segue é relato, e não transcript. Onde não houve relato, o
registro diz **não observado**, e isso não é o mesmo que "não ocorreu".

O ambiente tinha 8 skills: as 6 do OpenSpec e as 2 da Metacortex.

| Pedido ao agente | Skill que disparou | Como | O que mais o relato registra |
|---|---|---|---|
| Gerar manifests de `fake-shop` (`orion-prod`) e `encontros-tech` (`helio-prod`) "no padrão da casa", sem aplicar | `metacortex-manifests` | Sozinha, pelo reconhecimento do pedido | Nenhuma skill do OpenSpec entrou, e a de triagem ficou quieta mesmo com o cluster à mão. O agente não incluiu o objeto Namespace (quem cria é o Construct) e mandou criá-los à parte |
| Triagem de `orion-prod` (`Init:CreateContainerConfigError`) e `helio-prod` (`ImagePullBackOff`), sem corrigir | `metacortex-triagem` | Sozinha | A de manifests ficou quieta. O agente apontou que o ajuste de manifesto passaria pela outra skill, **sem chamá-la**. As causas estão no quadro acima |
| Corrigir os dois manifests com base nas causas | Uma só skill | Pelo pedido | A nota final diz que a triagem **não foi reinvocada**, porque as causas já estavam apuradas |

**Quais dispararam sozinhas.** Em cada um dos três pedidos disparou **uma** skill,
a que o pedido descrevia, sem que o nome dela fosse citado. A transição entre as
duas **não acontece sozinha**: a triagem apontou que a correção passaria pela
skill de manifests e parou, e a correção foi pedida num prompt novo. Para o
registro, isso é um resultado bom: o agente não sai corrigindo por iniciativa
própria.

**Quais foram chamadas na mão.** **Nenhuma das duas skills da Metacortex** foi
invocada pelo nome: os prompts descrevem a tarefa em linguagem natural. O que o
autor invocou explicitamente foram os comandos do OpenSpec: `/opsx:propose` (gerou
a change), `/opsx:update` (os cinco ajustes de spec antes da implementação) e
`/opsx:apply` (a implementação).

**Quais apareceram onde não deviam.**

- **Disparo fora do território: nenhum nos três pedidos de laboratório.** A
  triagem não carregou ao gerar manifests, as skills do OpenSpec não entraram no
  pedido de manifests, e a de manifests não carregou na triagem.
- **Excesso de conteúdo, não de disparo:** a `metacortex-manifests` incluiu
  **NetworkPolicies**, que o padrão oficial do Seraph não exige e que o Ticket 01
  tinha deixado de fora por isso. Não é erro (melhoram a postura), mas é a skill
  indo além do padrão.
- **Não observado:** a fase de implementação do painel (`/opsx:apply`, incluindo os
  YAMLs de `deploy/rbac/` e `deploy/lab/`). Nos prompts registrados, o relato de
  skills foi pedido só nos três pedidos de laboratório. Quem tiver o histórico
  dessas sessões pode acrescentar se a `metacortex-manifests` carregou ao escrever
  o RBAC, ou a de triagem ao abrir o painel.

**O que foi reexplicado repetidamente.** Itens que aparecem em mais de um prompt e
que nenhuma das duas skills sabe:

1. **"Escrita no cluster é do operador."** "Não aplique nada: eu aplico" nos
   pedidos de manifests e de correção, e "Não corrija nada no cluster" na
   triagem. A `metacortex-manifests` não tem `kubectl` entre as ferramentas
   permitidas (`allowed-tools` do `SKILL.md`), então aqui a regra era de
   processo e não técnica, mas foi preciso repeti-la a cada pedido.
2. **A adaptação de laboratório.** O registry `registry.metacortex.io` não existe
   neste laboratório, e foi preciso dizer, nos pedidos de manifests e de
   correção, para usar imagens públicas equivalentes e registrar a adaptação em
   comentário no topo de cada arquivo. O `conferir.py` acusa o prefixo do
   registry (`MC-ID-05`) por não distinguir laboratório de produção.
3. **O ciclo de planejamento.** "Não implemente nada: só proposta, design, specs
   e tarefas" apareceu em todo prompt de planejamento (`/opsx:propose` e
   `/opsx:update`), e "mantenha tudo em português" foi preciso dizer de novo,
   porque a change anterior do projeto tinha saído em inglês.
4. **O shell de quem opera.** As instruções do agente vinham em sintaxe de bash
   (continuação de linha com `\`, e o `deploy/lab/README.md` assume Git Bash),
   e o autor trabalha em PowerShell. Cada bloco precisou ser traduzido, e os
   `kubectl create secret` viraram uma linha só.

## Uma observação para a curadoria

As duas skills foram feitas para operar o cluster (uma escreve manifests, a
outra lê o cluster). O painel é uma terceira coisa: código de aplicação
que mora ao lado delas. Nenhuma das duas cobre "desenvolver um projeto com
spec". O ciclo do OpenSpec (`.claude/skills/openspec-*` e `.claude/commands/opsx/`)
é que guiou essa parte. Isso é resultado, e não falha: a descrição de cada
skill acertou ao não reclamar esse território.
