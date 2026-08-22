# Catálogo de prompts

Coleção de prompts em Markdown organizados por categoria/área de domínio. Cada prompt vive em sua própria pasta, contendo o arquivo `prompt.md` (texto puro, pronto para copiar e colar) e um `README.md` com metadados, variáveis e exemplos de uso.

Este repositório faz parte do material dos projetos da pós-graduação em AIOps e Inteligência Artificial com Engenharia Cloud: [pos.veronez.io/pos-aiops](https://pos.veronez.io/pos-aiops/).

Convenções de estrutura, nomenclatura e manutenção estão em [`CLAUDE.md`](./CLAUDE.md).

## Como usar

1. Navegar até a categoria de interesse.
2. Abrir o `README.md` do prompt para entender objetivo, variáveis esperadas e limitações.
3. Copiar o conteúdo do `prompt.md` e substituir os placeholders `{{nome_variavel}}` pelos valores desejados.

## Adicionando um prompt

Use o slash command [`/catalogar`](./.claude/commands/catalogar.md) passando o texto do prompt como argumento. Ele analisa, propõe organização (categoria, slug, frontmatter) e, após sua aprovação, escreve os arquivos e atualiza os índices — sem commitar. Convenções completas em [`CLAUDE.md`](./CLAUDE.md).

## Categorias

### [Desenvolvimento](./desenvolvimento/)

Escrita, revisão e refatoração de código, design de APIs e arquitetura, debugging, testes e documentação técnica.

_Nenhum prompt cadastrado ainda._

### [DevOps](./devops/)

Pipelines de CI/CD, containers, orquestração, infraestrutura como código, observabilidade, SRE e segurança operacional.

- [triagem-de-pods](./devops/triagem-de-pods/) — Cruza get/describe/logs de um snapshot do Kubernetes e devolve causa provável e ação por pod problemático.
- [nota-de-triagem-de-alerta](./devops/nota-de-triagem-de-alerta/) — Converte um alerta cru do Sentinel em nota de triagem padronizada de cinco campos para o plantão.
- [analise-de-causa-raiz](./devops/analise-de-causa-raiz/) — Cruza config, métricas e logs de uma janela para separar causa-raiz de sintomas e propor ação proporcional.
- [decisao-de-backpressure](./devops/decisao-de-backpressure/) — Compara estratégias de backpressure contra cada restrição de negócio e engenharia antes de recomendar, expondo o trade-off aceito.
- [migracao-lote-evento-1-diagnostico](./devops/migracao-lote-evento-1-diagnostico/) — Primeiro elo da cadeia: diagnostica pontos frágeis, consumidores por sensibilidade, riscos e pré-condições de um pipeline em lote.
- [migracao-lote-evento-2-plano](./devops/migracao-lote-evento-2-plano/) — Segundo elo da cadeia: transforma o diagnóstico em uma sequência de passos reversíveis, com critério de sucesso e gatilho de rollback por passo.
- [migracao-lote-evento-3-detalhamento](./devops/migracao-lote-evento-3-detalhamento/) — Terceiro elo da cadeia: detalha um passo do plano em ações concretas, métricas de sucesso/rollback e informações a solicitar ao time.
- [correcao-de-networkpolicy](./devops/correcao-de-networkpolicy/) — Recebe um manifesto de NetworkPolicy permissivo e produz a versão default-deny corrigida, com loop de verificação e refino conduzido.

### [Produtividade](./produtividade/)

Organização pessoal, gestão de tempo e tarefas, rotina, hábitos, foco e decisões sobre fluxo de trabalho individual.

_Nenhum prompt cadastrado ainda._

### [Finanças](./financas/)

Orçamento, investimentos, planejamento financeiro, impostos e apoio a decisões financeiras.

_Nenhum prompt cadastrado ainda._

### [Criação de Conteúdo](./criacao-conteudo/)

Roteiros, artigos, posts para redes sociais, material didático e copy de divulgação.

_Nenhum prompt cadastrado ainda._

<!--
Ao adicionar um prompt, substituir "Nenhum prompt cadastrado ainda" pela lista:

- [nome-do-prompt](./<slug-da-categoria>/<slug-do-prompt>/) — o que o prompt faz, em uma linha.
-->

## Contribuindo

Antes de adicionar ou alterar um prompt, revisar [`CLAUDE.md`](./CLAUDE.md) — a seção **Manutenção da documentação** lista todos os arquivos que precisam ser atualizados junto com a mudança (este índice incluso).
