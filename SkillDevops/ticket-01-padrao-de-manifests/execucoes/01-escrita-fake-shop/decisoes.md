# Execução 1 — Modo escrita: fake-shop (cliente orion, ambiente prod)

**Pedido:** "Gera os manifests do fake-shop (https://github.com/KubeDev/fake-shop) para o
cliente orion em prod, no padrão da casa."

**Projeto lido:** KubeDev/fake-shop @ `a3fa74f` (2026-07-19).
**Padrão aplicado:** Padrão de Manifests da Metacortex, rev. 2026-07-29.

**Saída:** `manifests/orion-prod/`, com 7 objetos em 3 arquivos e o `SECRET.md`.
- Conferência em `conferencia-final.md`: **1 falha, que exige exceção**, 0 avisos, 12 itens
  contextuais, todos resolvidos abaixo.
- Trivy e kubeconform em `trivy-e-kubeconform-cru.txt`: só o KSV-0125 (falso positivo de
  registry) e schema válido.

**Veredito da skill: PRONTO PARA PR COM PEDIDO DE EXCEÇÃO** (regra 2.3, Postgres). Detalhe
em D4.

## 1. Checklist de leitura do projeto

| Pergunta | Resposta no código | Evidência |
|---|---|---|
| Porta | 5000 (gunicorn `--bind 0.0.0.0:5000`) | `src/entrypoint.sh:3` |
| Endpoints de saúde | **nenhum**; existe `/metrics` (Prometheus), servido pelo app, sem acesso ao banco | `src/index.py:18-19` |
| Rotas que tocam o banco | `/` e `/shop` (`Product.query.all()`) | `src/index.py:131, 252-254` |
| Inicialização lenta | **sim**: `flask db upgrade` antes do gunicorn | `src/entrypoint.sh:2` |
| O entrypoint para em erro? | **não**, porque não há `set -e`: migração com falha é ignorada | `src/entrypoint.sh:1-3` |
| Variáveis lidas | `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT` (defaults `localhost`/`Pg1234`), `FLASK_APP`, `PROMETHEUS_MULTIPROC_DIR` | `src/index.py:22-26`, `README.md` |
| Sensíveis | `DB_USER`, `DB_PASSWORD` | idem |
| Onde escreve em disco | `PROMETHEUS_MULTIPROC_DIR` (precisa **existir**, porque o exporter é instanciado no import); `/tmp` (heartbeat dos workers do gunicorn) | `src/index.py:18` |
| Trata SIGTERM? | sim, é o gunicorn: encerramento gracioso dos workers com `graceful_timeout` padrão de 30s | `src/requirements.txt` (gunicorn 21) |
| Fala com o apiserver? | não, nenhum cliente Kubernetes nas dependências | `src/requirements.txt` |
| Hardcoded que deveria ser segredo | `app.secret_key = 'supersecretkey'` | `src/index.py:16` |

## 2. Decisões

**D1. Probes sem endpoint de saúde (2.2).** O padrão exige probes "em endpoints que a aplicação de
fato expõe" e proíbe readiness e liveness no mesmo endpoint que checa banco.
- `startupProbe` e `livenessProbe` em `/metrics`: existe e não toca o banco.
- `readinessProbe` em `/`: toca o banco e tira o pod do Service se o banco cair, sem reiniciar
  ninguém. Readiness e liveness ficam em endpoints distintos, e só a readiness depende do banco.
- Descartados:
  - `tcpSocket`, que não prova nada sobre a aplicação;
  - `/contact` como readiness, que seria uma liveness disfarçada;
  - inventar um `/health`, que não existe e faria a probe falhar para sempre.

**D2. Migração no start.** O padrão não tem regra de migração, mas ela esbarra na 2.2: a
aplicação só está pronta depois de migrar. A decisão foi tirar a migração do entrypoint e
colocá-la num `initContainer`; o container principal sobrescreve o `command` com o mesmo
gunicorn do entrypoint. Com isso, uma migração que falha impede o pod de ficar pronto, em vez
de passar despercebida. A corrida entre duas réplicas é resolvida pela tabela de versão do
alembic (quem perde reinicia e encontra o esquema atualizado). Um Job de migração foi
descartado por exigir ordenação no pipeline. A `startupProbe` dá 2 minutos para o boot.

**D3. Credencial (3.3).** Usuário e senha vêm do Secret `orion-fake-shop-db`, que não é versionado
e cujo comando de criação, com os 4 rótulos da 1.3, está no `SECRET.md`. Host, porta e nome do
banco ficam em `value`, porque não são sensíveis. As variáveis seguem os **nomes que o código lê**,
e não o exemplo de `DATABASE_URL` do padrão, que o fake-shop também não lê.

**D4. Banco junto e a regra 2.3.** O fake-shop "entrega o par aplicação e banco" (Ticket 04),
então o Postgres entra como StatefulSet com PVC e Service headless. Como a regra 2.3 é obrigatória
em prod, `replicas: 1` **barra**. Opções:

| Opção | Ganho | Custo |
|---|---|---|
| **Exceção à 2.3 no PR**, aprovada por S&C com prazo (escolhida) | caminho previsto no padrão; entrega agora | risco de indisponibilidade em drain/deploy do banco, aceito formalmente e com data para acabar |
| Postgres com replicação (operador, ex.: CloudNativePG) | cumpre a 2.3 de verdade | um operador novo no parque é decisão de plataforma, não de um manifesto |
| Banco gerenciado fora do cluster | remove o banco do escopo da regra | depende de oferta da Metacortex que não está descrita |
| `replicas: 2` "para passar" | nenhum | **dois bancos independentes**: dados divergentes. Descartado. |

Demais escolhas do banco:
- `runAsUser`/`fsGroup` 10001 (3.2), porque a imagem oficial aceita usuário arbitrário;
- `PGDATA` em subdiretório do PVC;
- `emptyDir` em `/var/run/postgresql` e `/tmp`;
- `terminationGracePeriodSeconds: 60` (2.6), porque o SIGTERM no Postgres é *smart shutdown*
  (espera sessões), e um SIGKILL aos 30s força recuperação de crash no boot seguinte.

**D5. Diretórios graváveis (3.2).** `emptyDir` em `/tmp` e `/tmp/metrics` também no
initContainer. Sem isso, a migração quebra no import do `index.py`.

**D6. Imagem (3.1, 3.7).** O repositório não tem Dockerfile. Foi assumida a publicação pelo Loom de
`registry.metacortex.io/orion/fake-shop:1.0.0` e o espelho de `postgres:16.4-alpine`. A skill
confere o registry e a ausência de `:latest`, mas **não** se a tag existe, que é assunto de triagem
(Ticket 02, Chamado 2).

**D7. Recursos (2.1).** Todos os containers declaram requests e limits de CPU e memória:

| Container | requests (CPU / memória) | limits (CPU / memória) |
|---|---|---|
| web | 100m / 128Mi | 500m / 256Mi |
| migrate | 50m / 96Mi | 500m / 192Mi |
| postgres | 100m / 256Mi | 500m / 512Mi |

A regra de bolso manda o limite de memória ficar entre 1,5x e 2x o **consumo observado**, e não
há consumo observado. Por isso os limites são 2x o request, como valor inicial declarado, a ser
recalibrado com métrica do Ticket 04. Cortar sem medir é o que causa o Chamado 1 do Ticket 02.

**D8. Rollout em prod (2.4, 2.5).** `RollingUpdate` com `maxUnavailable: 0` e `maxSurge: 1`, e PDB
com `minAvailable: 1` para o `orion-web`. O StatefulSet não tem `strategy` com surge, e um PDB com
uma réplica só travaria o drain.

**D9. O que deixei de fora de propósito.**
- **Namespace:** é criado pelo Construct (regra 1.2).
- **NetworkPolicy e `topologySpreadConstraints`:** o padrão não pede. Ficam como recomendação.
- **seccomp `RuntimeDefault`:** foi mantido no pod. Não é exigido, não custa nada e evita ruído
  do Trivy.

## 3. Itens "revisar" do conferir.py, resolvidos

| Item | Resolução |
|---|---|
| 2.2 `orion-web` | `/metrics` existe (`index.py:19`) e não toca o banco, então serve para liveness e startup. `/` existe (`index.py:252`) e toca o banco, então serve só para readiness. Destinos distintos. |
| 2.2 `orion-postgres` (mesmo destino) | O `pg_isready` checa o próprio servidor local. Aqui o processo **é** o banco, então o risco que a 2.2 descreve (reiniciar a aplicação por lentidão de uma dependência) não se aplica. Aceito. |
| 3.3 `orion-web` e `orion-postgres` | As variáveis batem 1:1 com `index.py:22-26` e com as da imagem oficial do Postgres. Só usuário e senha são sensíveis, e ambos vêm de `secretKeyRef`. |
| 3.2 ambos | Diretórios graváveis montados (D4 e D5). |
| 2.1 ambos | Limites iniciais sem consumo observado (D7). Pendente de recalibração. |
| 2.6 `orion-web` | O gunicorn drena no SIGTERM com timeout padrão de 30s, igual ao grace period padrão. Ok. |
| 2.6 `orion-postgres` | 60s declarados (D4). |
| 3.4 ambos | Nenhum dos dois fala com o apiserver. O token não é montado. |

## 4. Achados para o cliente orion (não se corrigem no manifesto)

1. `app.secret_key` hardcoded (`index.py:16`): precisa ser lida de Secret.
2. **O checkout grava `card_number` e `cvv` em texto no banco** (`index.py:85-87, 108-110`). É
   incompatível com PCI-DSS e deve ser escalado ao Seraph.
3. Expor `/health` (só processo) e `/ready` (processo e banco).
4. O `entrypoint.sh` sem `set -e` mascara migração com falha. O manifesto contorna, mas a imagem
   deveria corrigir.

## 5. O que ainda não foi validado

Nada foi aplicado em cluster. A compatibilidade da imagem do fake-shop com UID 10001 e root
filesystem somente leitura, e do Postgres com UID arbitrário e PVC via `fsGroup`, só se prova
subindo, no Ticket 04.
