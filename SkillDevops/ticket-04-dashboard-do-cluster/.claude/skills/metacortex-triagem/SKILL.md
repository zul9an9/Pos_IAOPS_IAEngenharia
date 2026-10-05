---
name: metacortex-triagem
description: >-
  Triagem de workload que JÁ ESTÁ RODANDO num cluster Kubernetes do parque da Metacortex, lendo
  o cluster pelo mcp-server-kubernetes: descobre em que camada está a causa (container, imagem/
  registry, rótulos/Service) a partir do sintoma que o cliente declarou. Use sempre que alguém
  disser que algo "está fora do ar", "não sobe", "reinicia sozinho", "está 0/N", "não tem
  endpoint", "responde 503", "não entrega tráfego", "está em CrashLoopBackOff/ImagePullBackOff",
  ou pedir para investigar um namespace, pod, deployment ou service no cluster — mesmo sem
  dizer "triagem". NÃO use para escrever, revisar ou conferir arquivo YAML contra o padrão
  (isso é a skill metacortex-manifests), para explicar conceitos de Kubernetes, nem para
  provisionar VM ou cluster.
allowed-tools: mcp__kubernetes__kubectl_get, mcp__kubernetes__kubectl_describe, mcp__kubernetes__kubectl_logs, mcp__kubernetes__explain_resource, mcp__kubernetes__list_api_resources, mcp__kubernetes__ping
---

# Triagem de cluster — método da Metacortex

A triagem responde uma pergunta só: **em que camada está a causa do sintoma, e qual evidência
prova isso.** Identificada a causa, o trabalho acabou.

## Limite absoluto: triagem lê, nunca escreve

Use apenas as ferramentas de leitura do MCP: `kubectl_get`, `kubectl_describe`,
`kubectl_logs`, `explain_resource`, `list_api_resources` e `ping`.

Nunca chame `kubectl_apply`, `kubectl_create`, `kubectl_patch`, `kubectl_scale`,
`kubectl_rollout`, `kubectl_delete`, `kubectl_generic`, `exec_in_pod`, `port_forward`,
`kubectl_context` nem nada de helm. A proibição vale também para o `rollout status`, que só lê
(use `kubectl_get` no Deployment), e para o `exec`: mesmo um `cat` dentro do container é
executar no workload do cliente.

O limite vale **mesmo quando a ferramenta está disponível** (o servidor em modo não destrutivo
permite apply, patch, scale e exec) e **mesmo quando o usuário pede** "já corrige", "reinicia
aí" ou "sobe um patch". Nesses casos:
1. termine a triagem;
2. escreva a correção como **sugestão** no relatório;
3. diga quem aplica: correção de manifesto passa pela skill `metacortex-manifests` e pelo PR
   com revisão; correção de registry ou release passa pelo time do Loom;
4. não execute nada.

Não troque de contexto nem de cluster. A triagem roda no contexto atual; se o sintoma for de
outro cluster, pergunte.

## Armadilhas do MCP (leia antes da primeira chamada)

- **`kubectl_get` de lista em JSON devolve um resumo.** Ele traz só nome e um status calculado,
  e perde READY, RESTARTS, rótulos e a lista de endpoints. Para listas, use sempre
  `output: "wide"`, que devolve a tabela real do kubectl.
- **Objeto com `name` devolve o objeto completo.** Para ler um campo específico (o estado de um
  container, o seletor, os rótulos), peça o objeto pelo nome com `output: "json"` e leia o
  campo.
- **Log de container que morreu:** `kubectl_logs` com `previous: true`.
- **Campo ausente não é campo vazio.** Um Deployment sem nenhuma réplica pronta não traz
  `readyReplicas`, e um Endpoints sem pods não traz `subsets`. Ausência significa zero.

Detalhes e exemplos de chamada: `references/mcp-leitura.md`.

## O método

### 0. O pedido fala de um objeto rodando ou de um arquivo?

Se o usuário fala de **arquivo** ("esse manifesto não sobe", "esse YAML não aplica") e não
diz o que aconteceu, pergunte antes de ler o cluster: **foi aplicado? Qual erro apareceu?**
- `apply` recusado (erro de validação, nome inválido, campo desconhecido): não há nada rodando
  para triar. É conferência de manifesto, na skill `metacortex-manifests`.
- Aplicado, mas não fica pronto ou não entrega tráfego: siga a triagem pelo namespace e pelo
  nome que o usuário informar.

### 1. Sempre comece pelo estado dos pods do namespace do sintoma

`kubectl_get` com `resourceType: pods`, o namespace do chamado e `output: "wide"`.

Classifique **cada** pod por READY, STATUS e RESTARTS, e anote já o que está **saudável ao
lado**. Isso separa triagem de chute: se o banco está `1/1` com 0 restarts, a hipótese "o banco
caiu" morre aqui.

Se o namespace não foi informado e há mais de um candidato (ex.: "o nyx" pode ser `nyx-prod`
ou `nyx-stg`), pergunte, ou olhe os candidatos e diga em qual achou o sintoma.

### 2. Escolha o ramo pela assinatura (não pelo sintoma declarado)

O cliente diz "está fora do ar" em todos os casos. Quem decide o caminho é o que o passo 1
mostrou.

| Assinatura no passo 1 | Camada provável | Próxima fonte |
|---|---|---|
| `CrashLoopBackOff`, `Error`, `OOMKilled`, RESTARTS subindo | **container** (o processo sobe e morre) | `describe pod`, bloco `Last State` (Reason, Exit Code, Started/Finished) e `Limits` |
| `ImagePullBackOff`, `ErrImagePull`, RESTARTS 0, `Image ID` vazio | **imagem/registry** (o container nunca existiu) | `describe pod` (campo `Image`, `Events`); se os eventos só mostram back-off, leia `status.containerStatuses[].state.waiting.message` do pod |
| Pods `1/1 Running`, 0 restarts, e o cliente não chega | **caminho do tráfego/metadado** | Services e endpoints do namespace, comparando com um Service irmão que funciona |
| `Pending` sem motivo no status | **agendamento** | `describe pod`, `Events` (FailedScheduling: recursos, taints, PVC) |
| `CreateContainerConfigError` | **configuração** | `describe pod`: Secret ou ConfigMap referenciado que não existe |

Tabela completa de assinaturas e leitura de cada motivo: `references/assinaturas.md`.

### 3. Desça uma camada por vez, e cruze duas fontes nos três momentos em que uma não basta

1. **Quando uma fonte dá o motivo e outra descarta a alternativa.** Exemplo: o `Last State`
   diz OOMKilled, e o `logs --previous` vazio confirma que a aplicação não reportou erro, ou
   seja, a morte veio de fora.
2. **Quando a fonte principal perdeu a informação.** Os eventos guardam só o back-off
   repetido, e a mensagem original do registry saiu da janela. Vá ao status do container,
   que guarda a última mensagem.
3. **Quando o defeito é um vínculo entre dois objetos.** O seletor do Service contra os
   rótulos dos pods, ou o `targetPort` do Service contra a porta do container. Nenhum dos dois
   objetos, sozinho, parece errado.

Não aprofunde numa fonte que já respondeu: um `describe` com `OOMKilled` não precisa de três
`describe` iguais.

### 4. Pare quando tiver as três partes da causa

- **camada** (container, imagem/registry, metadado/rótulos, configuração, agendamento, rede);
- **o que está errado**, numa frase, com o valor concreto (`limit 24Mi`, `tag v1.14.2`,
  `app=nyx-api` × `app=nyxapi`);
- **evidência** de pelo menos uma fonte decisiva, confirmada ou não contradita por outra.

Com isso, pare. Não audite o resto do namespace nem "aproveite para olhar" outras coisas.
Achados paralelos só entram no relatório se afetarem a causa.

## Relatório

```
# Triagem — <namespace> — "<sintoma como o cliente disse>"

**Causa:** <camada> — <o que está errado, com o valor concreto>
**Evidência:**
- <fonte 1>: <trecho que prova>
- <fonte 2>: <trecho que confirma ou descarta a alternativa>
**Funcionando ao lado:** <o que foi verificado e está saudável>
**Hipóteses descartadas:** <hipótese — o que a descartou>
**Correção sugerida (NÃO aplicada):** <o quê> — <quem aplica e por onde>
**Caminho percorrido:** <as consultas, em ordem, em uma linha cada>
```
