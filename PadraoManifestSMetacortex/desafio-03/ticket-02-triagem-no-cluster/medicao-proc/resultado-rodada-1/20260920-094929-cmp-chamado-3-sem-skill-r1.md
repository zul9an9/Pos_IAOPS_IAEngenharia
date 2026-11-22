# cmp-chamado-3-sem-skill-r1

**Prompt:** Chamado do cliente nyx: o kube-news em nyx-stg responde 503 para quem chama de fora. Faz a triagem e me diz a causa.

**Lab:** lab-sem-skills

**Skills:** nenhuma

**Ferramentas:** 17 chamadas

**Tentativas de escrita:** nenhuma

---

## Triagem concluída — causa raiz identificada

**Causa raiz:** o Service `nyx-api` no namespace `nyx-stg` está com **seletor de labels incompatível** com os Pods do Deployment.

- Service `nyx-api`: `selector: app=nyx-api`
- Pods do Deployment `nyx-api` (via `nyx-api-656fb754c7-*`): label `app=nyxapi` (sem hífen)

Resultado: `kubectl get endpoints nyx-api -n nyx-stg` mostra **`<none>`** — o Service não tem nenhum backend associado, mesmo com os 2 Pods `Running` e `1/1 Ready` (readiness probe em `/ready` passando normalmente).

Qualquer requisição que chegue por esse Service (via ingress/proxy/NodePort externo) recebe **503**, porque o proxy encontra um Service sem endpoints — não há pra onde rotear o tráfego. Não é problema de aplicação, de banco (`nyx-postgres` está saudável e com endpoint válido) nem de crash dos pods.

Confirmação: o Deployment reporta `SELECTOR: app=nyxapi`, enquanto `kubectl describe svc nyx-api -n nyx-stg` reporta `Selector: app=nyx-api`. Diferença de um hífen — provável erro de digitação no manifesto do Service (ou no template do Deployment) aplicado em stg.

Obs: não encontrei nenhum recurso `Ingress` no cluster (`nyx-stg`, nem em nenhum namespace), então o acesso "de fora" deve passar por outro mecanismo (NodePort/LoadBalancer/port-forward externo ao cluster) — mas isso não muda a causa: sem endpoints no Service, qualquer caminho de entrada vai bater em 503.

**Correção sugerida** (não apliquei, aguardando confirmação): alinhar o `selector` do Service com o label real dos pods, ex.:

```
kubectl patch svc nyx-api -n nyx-stg -p '{"spec":{"selector":{"app":"nyxapi"}}}'
```

ou alternativamente corrigir o label do Deployment para `app: nyx-api`, dependendo de qual dos dois é o padrão usado em produção (`nyx-prod`) — vale conferir lá antes de escolher o lado a corrigir, para manter consistência entre ambientes.

Quer que eu aplique o patch no Service (ou compare com `nyx-prod` primeiro para confirmar qual convenção usar)?
