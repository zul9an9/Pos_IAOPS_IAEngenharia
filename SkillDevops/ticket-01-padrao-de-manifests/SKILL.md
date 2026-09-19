---
name: metacortex-manifests
description: >-
  Escreve e confere manifests YAML de Kubernetes contra o Padrão de Manifests da Metacortex
  (rótulos, seletores, probes, requests/limits, réplicas e rollout em prod, securityContext,
  segredos, service account, registry interno). Use sempre que alguém pedir para criar, gerar,
  revisar, validar ou corrigir um manifesto, Deployment, StatefulSet, Service ou YAML "no padrão
  da casa", ou perguntar se um manifesto passa na revisão do Seraph — mesmo sem citar o padrão.
  NÃO use para diagnosticar pods, services ou deployments que já estão rodando no cluster (isso
  é triagem), nem para explicar conceitos de Kubernetes.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(python3 *conferir.py*), Bash(trivy config*), Bash(git clone*)
---

# Manifests no padrão da Metacortex

O padrão (wiki de Plataforma, revisão 2026-07-29) tem regras de dois tipos, e esta skill trata
cada tipo de um jeito:

- **Mecânicas.** São iguais para qualquer manifesto. Quem confere é o `scripts/conferir.py`:
  ele roda o `trivy config`, a mesma varredura que Segurança & Compliance roda no pipeline, e
  confere sozinho o que o Trivy não conhece. Não confira essas regras de olho; rode o script.
- **Contextuais.** Só se resolvem lendo a aplicação. Resolva abrindo o projeto. O script lista
  essas regras na seção "Revisar lendo o projeto".

O texto das regras, a severidade e o mapa Trivy→regra estão em `references/padrao.md`. Leia
quando precisar citar uma regra ou explicar um veredito.

## Severidade e exceção

O padrão tem três severidades, e o veredito depende delas:

- **Obrigatório:** barra. A exceção só vale com aprovação escrita de Segurança & Compliance no
  PR, com prazo de validade.
- **Proibido:** barra. Não existe exceção para workload de cliente.
- **Recomendado:** vira aviso. A exceção precisa só de justificativa no PR.

O script não enxerga PR. Quando uma falha obrigatória for legítima (ex.: banco single-instance),
diga no relatório que ela **depende de exceção aprovada** e o que se ganha e se perde. Nunca
contorne uma regra para o script passar.

## Limites

- Não aplique nada no cluster. A skill produz e confere arquivos.
- Não invente endpoint, porta ou variável. Se não estiver no código, não existe: declare a
  lacuna.
- Nunca escreva valor de credencial em manifesto, comentário ou ConfigMap. Referencie o Secret e
  diga como criá-lo fora do Git.
- Não inclua o objeto Namespace: quem cria é o Construct.

## Modo conferência (uso mais frequente)

1. Rode `python3 <skill>/scripts/conferir.py <arquivo-ou-pasta> --json /tmp/conferencia.json`.
   O código de saída 1 indica falha. Sem o Trivy instalado, as regras 2.1, 3.2 e 3.6 aparecem
   como "não verificado". Diga isso e não trate esse resultado como conforme.
2. Localize o projeto da aplicação: o repositório local ou um `git clone` da URL informada. Sem o
   projeto, as pendências contextuais ficam em aberto, e o relatório diz isso.
3. Resolva cada item de "Revisar lendo o projeto" com o **checklist de leitura** abaixo,
   comparando o que o manifesto entrega com o que o código espera. Seguir um exemplo do padrão
   não garante que a aplicação funcione (ex.: `DATABASE_URL` só serve se o código ler
   `DATABASE_URL`).
4. Entregue o relatório no formato da seção "Saída".

## Modo escrita

1. Leia o projeto com o **checklist de leitura** antes de escrever qualquer YAML.
2. Se a leitura esbarrar em algo sem resposta óbvia, leia `references/decisoes.md` e registre a
   opção escolhida. São quatro casos: aplicação sem endpoint de saúde, migração no start, banco
   junto da aplicação, diretórios graváveis.
3. Parta de `assets/modelo-app.yaml` e preencha cada `<...>` com o que saiu do projeto.
   Rótulos: `name` = componente, `instance` = namespace, `part-of` = produto do cliente,
   `managed-by` = `platform`.
4. Rode o `conferir.py` na pasta gerada e corrija até zerar as falhas, exceto as que dependem de
   exceção declarada. Todo item "revisar" precisa estar respondido no relatório de decisões.
5. Entregue os manifests, a saída final do script e as decisões.

## Checklist de leitura do projeto

Procure no código: entrypoint, Dockerfile, manifesto de dependências, rotas, configuração de
banco. O README ajuda, mas não basta.

| Pergunta | Onde costuma estar | Regra |
|---|---|---|
| Em que porta o processo escuta? | `listen(...)`, `--bind`, `EXPOSE` | 1.4 (targetPort) |
| Quais endpoints de saúde existem? Algum toca o banco? | rotas `/health`, `/ready`, `/healthz` e seus handlers | 2.2 |
| A inicialização é lenta (migração, sync de esquema, warmup)? | entrypoint, `db upgrade`, `sync()` | 2.2 (startupProbe) |
| Quais variáveis de ambiente o código lê, com que nomes e que defaults? | `process.env.*`, `os.getenv` | 3.3 |
| Quais variáveis são sensíveis? | senha, token, chave, `secret_key` | 3.3 |
| Onde o processo escreve em disco? | `/tmp`, diretório de métricas, cache, uploads | 3.2 |
| A aplicação trata SIGTERM? Quanto tempo leva para drenar? Quem é o PID 1? | handlers de sinal, servidor (gunicorn drena; Node puro não), Dockerfile | 2.6 |
| A aplicação fala com o apiserver? | cliente Kubernetes nas dependências | 3.4 |
| Há consumo observado para calibrar limites? | métricas; senão, declarar como valor inicial | 2.1 |

Um default perigoso também é achado. Se o código cai em `localhost` quando a variável falta, uma
variável com nome errado não quebra o deploy, só o runtime.

## Saída

```
# Conferência — <arquivo> (<namespace>)
Veredito: BARRADO | PRONTO PARA PR | PRONTO PARA PR COM PEDIDO DE EXCEÇÃO (regra X)
## Bloqueia a subida (quebra funcional, não só desvio de padrão)
## Falhas do padrão (regra, severidade, achado, fonte)
## Achados lendo o projeto (cada "revisar" resolvido, com arquivo:linha)
## Correção proposta (YAML ou diff) / Exceções necessárias
## Recomendações ao cliente (o que não se corrige no manifesto)
## Não verificado (e por quê)
```

Separe o que **quebra de fato** do que é desvio de padrão. Nome rejeitado pela API, Service sem
endpoint e variável que a aplicação não lê derrubam o cliente, por isso vêm primeiro.
