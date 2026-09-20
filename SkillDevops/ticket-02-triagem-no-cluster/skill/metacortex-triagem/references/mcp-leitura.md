# Leitura pelo mcp-server-kubernetes: como chamar e o que o braço esconde

Verificado no código-fonte do servidor (flux159/mcp-server-kubernetes, commit `0340ab6`). O
servidor executa o **binário `kubectl` do PATH** da máquina. Se o kubectl estiver fora da faixa
de versão suportada (±1 minor em relação ao servidor), a saída pode vir inconsistente.

## Ferramentas permitidas na triagem

| Ferramenta | Uso na triagem |
|---|---|
| `kubectl_get` | estado de pods, deployments, services, endpoints, eventos; objeto completo por nome |
| `kubectl_describe` | `Last State`, `Limits`, `Events` de um pod; `Selector`/`Endpoints` de um Service |
| `kubectl_logs` | log do container; `previous: true` para o que morreu |
| `explain_resource` | significado de um campo, quando necessário |
| `list_api_resources` | nome correto de um recurso (ex.: `endpointslices`) |
| `ping` | verificar se o servidor responde |

## Chamadas que resolvem os três ramos

**Estado dos pods (passo 1).** Nunca use o JSON padrão, que resume e perde READY, RESTARTS e
rótulos.
```
kubectl_get  resourceType=pods  namespace=<ns>  output=wide
```

**Motivo da morte do container:**
```
kubectl_describe  resourceType=pod  name=<pod>  namespace=<ns>
kubectl_logs      resourceType=pod  name=<pod>  namespace=<ns>  previous=true
```

**Mensagem do registry que saiu dos eventos.** Peça o pod por nome em JSON e leia
`status.containerStatuses[].state.waiting.message`:
```
kubectl_get  resourceType=pod  name=<pod>  namespace=<ns>  output=json
```

**Caminho do tráfego:**
```
kubectl_get       resourceType=services   namespace=<ns>  output=wide
kubectl_get       resourceType=endpoints  namespace=<ns>  output=wide
kubectl_describe  resourceType=service    name=<svc>      namespace=<ns>
kubectl_get       resourceType=pods  namespace=<ns>  labelSelector=<seletor do Service>  output=wide
```
O último comando **vazio**, com pods prontos no namespace, prova o descasamento seletor ×
rótulos. Para ver os rótulos reais, peça um pod por nome com `output=json` e leia
`metadata.labels`.

**Eventos do namespace:**
```
kubectl_get  resourceType=events  namespace=<ns>  sortBy=lastTimestamp
```
Sem `namespace`, o servidor lista eventos de **todos** os namespaces.

## O que o resumo JSON esconde (e por que isso importa)

Em lista com `output=json` (o padrão), o servidor devolve apenas
`{name, namespace, kind, status, createdAt}`, e o `status` é calculado:
- **pod:** a fase ou motivo equivalente ao kubectl, **sem** READY e RESTARTS;
- **deployment:** `ready/total` só quando `status.readyReplicas` existe. Com **zero** réplicas
  prontas o campo não vem, e o resumo não mostra `0/N`;
- **service:** só o tipo (`ClusterIP`);
- **endpoints:** nada de útil. A lista de IPs some.

Consequência: um agente que confia no resumo não vê CrashLoop com 15 restarts como diferente de
um pod estável, não vê `0/3`, e não vê endpoints vazios. Os três sinais que resolveram os
chamados do laboratório desaparecem.

## Aviso de depreciação

`v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice` aparece no stderr
ao ler `endpoints`. Na triagem, o objeto ainda responde e serve. Se ele deixar de existir, use
`resourceType=endpointslices` com `labelSelector=kubernetes.io/service-name=<svc>`.
