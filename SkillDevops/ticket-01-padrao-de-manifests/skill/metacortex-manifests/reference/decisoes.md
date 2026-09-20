# Decisões sem resposta óbvia

Leia só quando o checklist de leitura esbarrar numa destas situações. Registre a opção escolhida
e o motivo no relatório.

## 1. Aplicação sem endpoint de saúde (2.2)

A regra 2.2 exige probes "em endpoints que a aplicação de fato expõe". Não invente um `/health`
que não existe: a probe falharia e o pod nunca ficaria pronto. Opções, da preferida para a menos
preferida:

1. **Endpoint que existe e não toca o banco**, para liveness e startup. Exemplo: o `/metrics` de
   um exporter Prometheus responde enquanto o processo vive.
2. **Rota barata que toca o banco**, para readiness. Ela tira o pod do Service quando o banco
   cai, sem reiniciar nada. Evite rotas pesadas: a readiness roda a cada poucos segundos por
   réplica.
3. **`tcpSocket` na porta**, como último recurso. Só prova que alguém aceita conexão.

A 2.2 proíbe o arranjo que derruba a aplicação quando o banco fica lento: readiness e liveness
no mesmo endpoint que checa o banco. Se só existir um endpoint e ele checar o banco, ele serve
só para a readiness, e a liveness vai para outra coisa.

Registre também uma **recomendação ao cliente**: expor `/health` (só processo) e `/ready`
(processo e banco). A skill não altera o código do cliente.

## 2. Migração de banco no start (2.2, startupProbe)

Sinais típicos: um entrypoint que roda `flask db upgrade`, `alembic upgrade`, `migrate` ou
`sequelize.sync` antes do servidor. Verifique se o script para em erro (`set -e`). Se não para,
a migração falha em silêncio e a aplicação sobe contra um esquema velho.

- **initContainer com o comando de migração, e o container principal sobrescrevendo o `command`
  para subir só o servidor.** É a opção padrão: a falha impede o pod de ficar pronto, aparece no
  `kubectl describe` e não depende de ordem de apply. Com várias réplicas, os initContainers
  podem rodar juntos. Ferramentas com tabela de versão (alembic, flyway) resolvem isso na
  reexecução. Diga isso no relatório. O initContainer também cumpre 2.1 e 3.2.
- **Job de migração antes do Deployment.** Melhor para migração longa ou quando corrida é
  inaceitável. Exige ordenação no pipeline (hook, wave).
- **Migração embutida no código** (ex.: `sync()` no boot). Não se separa no manifesto. Registre
  como recomendação ao cliente.

Se o processo ainda demora a subir, use `startupProbe` com `failureThreshold × periodSeconds`
dimensionado para o pior caso.

## 3. Banco junto da aplicação

Quando o workload entrega "aplicação + banco" no mesmo namespace:

- Use **StatefulSet** com PVC (`volumeClaimTemplates`) e Service headless. Os 4 rótulos também
  vão no PVC template.
- **A regra 2.3 barra `replicas: 1` em prod.** Não suba para 2 só para passar: dois Postgres
  independentes divergem. Apresente as opções:
  - exceção no PR, aprovada por S&C com prazo;
  - replicação via operador;
  - banco gerenciado fora do cluster.

  O veredito vira "PRONTO PARA PR COM PEDIDO DE EXCEÇÃO". Em dev e stg, 1 réplica é aceitável.
- Para o Postgres com a regra 3.2:
  - `runAsUser: 10001` e `fsGroup: 10001` (a imagem oficial aceita usuário arbitrário);
  - `PGDATA` num subdiretório do volume, para não colidir com `lost+found`;
  - `emptyDir` em `/var/run/postgresql` e `/tmp`.
- As probes usam `exec pg_isready -h 127.0.0.1`. Readiness e liveness no mesmo destino são
  aceitáveis aqui, porque o processo **é** o banco e não há dependência externa para derrubá-lo.
- Para a 2.6: o SIGTERM no Postgres é *smart shutdown* (espera as sessões). Declare um grace
  period maior que 30s, senão o SIGKILL força recuperação de crash.
- Não há PDB com uma réplica: ele só travaria o drain.

## 4. Diretórios graváveis (3.2)

Com `readOnlyRootFilesystem: true`, cada diretório que o código escreve precisa de `emptyDir`,
inclusive nos initContainers que importam o mesmo código. Candidatos comuns:
- `/tmp` (o gunicorn usa para o heartbeat dos workers);
- o diretório multiprocess do Prometheus (`PROMETHEUS_MULTIPROC_DIR`, que precisa existir antes
  do import);
- diretórios de cache e de upload.

O Python sem permissão de escrita só deixa de gravar `.pyc`, o que é inofensivo.
