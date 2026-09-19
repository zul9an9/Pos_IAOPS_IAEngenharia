# Conferência — nyx-api.yaml (nyx-prod)

**Pedido:** "Esse manifesto do nyx está no padrão da casa? O Seraph barrou." (`manifest-barrado/`)
**Padrão:** rev. 2026-07-29 · **Projeto lido:** KubeDev/kube-news @ `aab9356`
**Saída mecânica:** `conferencia-script.md`: 25 falhas, 2 avisos, 6 itens a revisar, código de
saída 1.

**Veredito: BARRADO.** Sem direito a exceção: há violação de regra *proibida* (3.1 e 3.3).

## Bloqueia a subida (quebra funcional, não só desvio de padrão)

1. **O nome `NyxAPI` é rejeitado pela API** (1.1). O Kubernetes exige nome minúsculo; o
   Deployment nem é criado. O Trivy e o kubeconform aceitam esse nome (evidência em
   `../../fluxo-de-origem/`); só a regra própria do script pega.
2. **O Service fica sem endpoint** (1.4). O selector é `app: nyx-api`, mas os pods têm
   `app: nyxapi`. É o caso descrito no próprio padrão, "o erro mais comum do parque".
3. **A aplicação não enxerga o banco** (3.3, resolvido lendo o projeto). O manifesto entrega
   `DATABASE_URL`, mas o kube-news **não lê essa variável**. Ele lê `DB_HOST`, `DB_PORT`,
   `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` e `DB_SSL_REQUIRE` (`src/models/post.js:8-13`) e,
   sem elas, conecta em `localhost:5432` com a senha default `Pg#123`. O pod sobe, as probes
   passam (nenhuma toca o banco) e toda página que lê notícias falha.

> **O exemplo "certo" da regra 3.3 também quebraria o nyx.** Trocar o valor literal por
> `DATABASE_URL` via `secretKeyRef`, exatamente como o padrão ilustra, remove a senha do Git mas
> não conserta nada: o kube-news continua sem ler a variável. A variante de controle em
> `variante-exemplo-do-padrao/` passa na conferência mecânica com **0 falhas e código de saída
> 0**. Só a leitura do código detecta o problema. É por isso que a conferência abre o projeto.

## Falhas do padrão

Detalhe completo em `conferencia-script.md`.

| Regra | Severidade | Achado | Fonte |
|---|---|---|---|
| 1.1 | obrigatório | `NyxAPI` fora de kebab-case | script |
| 1.3 | obrigatório | nenhum dos 4 rótulos no Deployment, no template e no Service; o `app:` curto não substitui | script |
| 1.4 | obrigatório | selector do Service não casa com os pods | script |
| 2.1 | obrigatório | sem requests e limits de CPU e memória | trivy (KSV-0011/15/16/18) |
| 2.2 | obrigatório | sem readinessProbe e sem livenessProbe | script |
| 2.3 | obrigatório | `replicas: 1` em prod | script |
| 2.4 | obrigatório | sem strategy (padrão do Kubernetes 25%/25%, que reduz capacidade no rollout) | script |
| 3.1 | **proibido** | imagem `:latest` | trivy (KSV-0013) |
| 3.2 | obrigatório | securityContext ausente: root, escalonamento, FS gravável, capabilities, UID | trivy (8 checks) |
| 3.3 | **proibido** | `usuario:senha` em texto no `DATABASE_URL` (linha 25) | script |
| 3.4 | obrigatório | token de service account montado (obrigatório desde 2026-07-29) | script |
| 1.5 | recomendado | sem `metacortex.io/owner` | script (aviso) |
| 3.5 | recomendado | ServiceAccount `default` | script (aviso) |

Checks do Trivy fora do padrão, só informativos: KSV-0021 (GID) e KSV-0030/0104 (seccomp).

## Achados lendo o projeto

| Item do script | Resolução com evidência |
|---|---|
| 2.2: destino das probes | `/ready` existe (`src/system-life.js:11`) e vira readiness. `/health` existe (`system-life.js:22`) e não toca o banco (responde hostname; só falha via `/unhealth`, `system-life.js:43`), então vira liveness. São endpoints distintos e nenhum checa banco, o que atende a 2.2. Porta 8080 confirmada (`src/server.js:81`). **Ressalva:** como o `/ready` também não consulta o banco, o pod continua "pronto" com o banco fora. |
| 3.3: variáveis | Ver o item 3 dos bloqueios. Na correção, `DB_USERNAME` e `DB_PASSWORD` vêm do Secret `nyx-db`. Host, porta e banco saíram da URL original (`pg.nyx-prod.svc:5432/nyx`). |
| 3.2: onde escreve | O código não escreve em disco (Express, EJS, estáticos só leitura). `emptyDir` em `/tmp` por precaução do runtime Node. |
| 2.6: SIGTERM | **O kube-news não trata SIGTERM** (nenhum `process.on('SIGTERM')` em `src/`), então requisições em andamento são cortadas no rollout. Se o processo Node rodar como PID 1 sem init, o sinal é ignorado e todo encerramento espera os 30s até o SIGKILL. O Dockerfile não está no repositório, então isso precisa ser confirmado na imagem. Grace period mantido em 30s, com recomendação ao cliente. |
| 3.4: fala com a API? | Não: nenhum cliente Kubernetes nas dependências (`src/package.json`). O token pode ficar desmontado. |
| 2.1: limites | Sem consumo observado. Valores iniciais, a recalibrar por 1,5x a 2x do regime. |

Achado extra, fora das regras: `sequelize.sync({ alter: true })` roda no boot
(`src/models/post.js:59`) sem `await`. Com as 2 réplicas que a 2.3 exige, são dois `ALTER TABLE`
concorrentes a cada rollout. Não se corrige no manifesto, porque não existe comando separado de
migração.

## Correção proposta

`correcao-proposta/nyx-api.yaml`, com ServiceAccount, Deployment, Service e PDB, cada mudança
comentada com a regra. Resultado em `correcao-conferencia.md`: **0 falhas, 0 avisos**, código de
saída 0, kubeconform válido (4 recursos). O rótulo `app: nyx-api` foi mantido por compatibilidade,
como a 1.3 permite.

Antes do apply:

```bash
kubectl -n nyx-prod create secret generic nyx-db \
  --from-literal=username=nyx --from-literal=password='<senha rotacionada>'
kubectl -n nyx-prod label secret nyx-db app.kubernetes.io/name=nyx-db \
  app.kubernetes.io/instance=nyx-prod app.kubernetes.io/part-of=nyx app.kubernetes.io/managed-by=platform
```

A senha `s3nh4-do-banco` **vazou** num manifesto que circulou em revisão e precisa ser rotacionada.

## Recomendações ao cliente nyx (fora do manifesto)

1. Tratar SIGTERM, parando de aceitar conexões e drenando, e garantir init (`tini`/`--init`)
   se o Node for PID 1.
2. Fazer o `/ready` consultar o banco.
3. Tirar o `sequelize.sync({ alter: true })` do boot e passar a usar migrações versionadas.
4. Remover o default de senha `Pg#123` do código (`src/models/post.js:10`).

## Não verificado

- Se a tag `1.0.0` existe em `registry.metacortex.io/nyx/api`: foi assumida.
- Se a imagem roda com UID 10001 e FS somente leitura: só subindo no cluster.
- Quem é o PID 1 na imagem: não há Dockerfile no repositório.
