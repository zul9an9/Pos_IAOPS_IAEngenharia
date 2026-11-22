# Assinaturas de falha e como ler cada uma

Abra este arquivo quando o passo 1 mostrar uma assinatura e você precisar saber o que cada
motivo significa e qual segunda fonte usar. As três primeiras seções vêm dos chamados reais do
laboratório (fluxo de origem); as demais completam o mapa com casos comuns do parque.

## Container: o processo sobe e morre

Leia no `describe pod`, no bloco do container: `Last State` → `Reason`, `Exit Code`,
`Started`/`Finished`, e `Limits`/`Requests`.

| Last State | Exit Code | Leitura | Segunda fonte |
|---|---|---|---|
| `OOMKilled` | 137 | O kernel matou o processo por exceder o **limite de memória** do container | `logs --previous`: se vier vazio ou sem erro, a morte veio de fora. Compare o `Limits.memory` com o que a aplicação precisa (runtime Node ou Python acima de ~50Mi só para subir) |
| `Error` | 1, 2… | A **aplicação** terminou com erro | `logs --previous`: a última linha antes da morte (conexão com banco, variável faltando, porta ocupada) |
| `Error` / `Completed` | 137 sem OOMKilled | Morte por sinal 9 que não foi OOM, normalmente a **liveness probe** falhando | `Events`: `Unhealthy ... Liveness probe failed`; confira o path e a porta da probe |
| `Completed` | 0 | O processo **terminou normalmente**, mas é um Deployment e devia continuar rodando | comando ou entrypoint errado na imagem ou no manifesto |

O tempo de vida (`Finished − Started`) ajuda: poucos segundos em todas as tentativas é
consistente com falha no boot (limite muito baixo, configuração faltando); minutos ou horas
sugere vazamento ou carga.

*Origem, chamado 1 (nyx-prod):* `OOMKilled`, 137, `Limits.memory 24Mi`, vida de cerca de 4s e
`logs --previous` vazio. A causa estava nos recursos do container, e o banco ao lado estava
saudável.

## Imagem/registry: o container nunca existiu

Sinais: `ImagePullBackOff` ou `ErrImagePull`, RESTARTS 0, `Container ID` e `Image ID` vazios
no `describe`.

Os `Events` costumam mostrar só `Back-off pulling image` repetido. **A mensagem original do
registry sai da janela de eventos.** Leia no pod o campo
`status.containerStatuses[].state.waiting.message` (peça o pod por nome com
`output: "json"`), que guarda a última mensagem do pull.

| Mensagem do registry | Leitura | Como descartar as alternativas |
|---|---|---|
| `NotFound` / `not found` / `manifest unknown` | A **referência não existe**: tag ou repositório errado, ou tag anunciada e não publicada | Se outras imagens do mesmo registry baixaram, a rede está ok. `NotFound` significa que o registry respondeu |
| `unauthorized` / `denied` / `authentication required` | Falta **credencial** (`imagePullSecrets`) ou repositório privado | Verifique se o pod referencia `imagePullSecrets` e se o Secret existe no namespace |
| `i/o timeout` / `no such host` / `connection refused` | **Rede ou DNS** até o registry | Outros pulls do mesmo registry também falham? |
| `toomanyrequests` | **Rate limit** do registry público | Na Metacortex a imagem deveria vir do registry interno (via Loom) |

*Origem, chamado 2 (orion-stg):* os eventos só mostravam back-off (x280). O `waiting.message`
trouxe `ErrImagePull code=NotFound docker.io/fabricioveronez/fake-shop:v1.14.2: not found`. O
postgres ao lado tinha baixado imagem pública, então a rede estava descartada. Causa: tag
anunciada no release e inexistente no registry.

## Caminho do tráfego/metadado: pods saudáveis e ninguém chega

Sinais: pods `1/1 Running`, 0 restarts, readiness passando, mas quem chama recebe
503/502/timeout.

Siga o caminho: **Service → Endpoints/EndpointSlice → Pod**.
1. `kubectl_get` de `services` e `endpoints` no namespace, com `output: "wide"`.
   **Compare com um Service irmão que funciona**: se o do banco tem IP e o da API mostra
   `<none>`, o mecanismo funciona e o problema é do Service da API.
2. Endpoints vazio com pods prontos significa que **nenhum pod casa com o seletor**. Cruze o
   `Selector` (`describe svc`) com os rótulos dos pods (pod por nome com `output: "json"` →
   `metadata.labels`, ou lista `wide` filtrada por `labelSelector` com o seletor do Service:
   resultado vazio confirma o descasamento).
3. Endpoints preenchido e mesmo assim sem resposta: compare o `targetPort` do Service com a
   `containerPort` e com a porta em que o processo escuta. Depois olhe o Ingress, se houver.

*Origem, chamado 3 (nyx-stg):* endpoints `<none>` na API e IP no postgres; `Selector: app=nyx-api`
e pods com `app=nyxapi`. Causa: descasamento de rótulo (um hífen), e nem o Service nem os pods,
sozinhos, pareciam errados.

## Outros casos do parque (fora do laboratório)

| Assinatura | Leitura | Fonte |
|---|---|---|
| `Pending` + `FailedScheduling: Insufficient cpu/memory` | Requests maiores que o espaço livre dos nós | `describe pod` → `Events` |
| `Pending` + `didn't tolerate taint` / `node affinity` | Restrição de agendamento | `describe pod` → `Events` |
| `Pending` + `unbound PersistentVolumeClaim` | Armazenamento | `kubectl_get pvc` no namespace |
| `CreateContainerConfigError` | Secret ou ConfigMap referenciado não existe | `describe pod` → `Events`/`Message` |
| `Running` e `0/1` há muito tempo | Readiness falhando | `Events`: `Readiness probe failed`; confira path e porta |
| Deployment `0/N` sem pods | ReplicaSet não cria pods (quota, admission) | `describe deploy` e `describe rs` → `Events` |
