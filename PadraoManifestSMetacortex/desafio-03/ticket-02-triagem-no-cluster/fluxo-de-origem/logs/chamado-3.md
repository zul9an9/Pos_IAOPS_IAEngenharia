# Triagem manual — chamado 3

**Início:** 2026-09-20T02:08:55-03:00  
**Sintoma declarado:** cliente nyx: o kube-news em nyx-stg responde 503 para quem chama de fora


> **Raciocínio** (2026-09-20T02:08:55-03:00): começo pelo estado dos pods para saber se a aplicação está de pé


### 2026-09-20T02:09:01-03:00 — `kubectl get pods -n nyx-stg` (rc=0, 216 ms)
```
NAME                            READY   STATUS    RESTARTS   AGE
nyx-api-656fb754c7-gdbtn        1/1     Running   0          77m
nyx-api-656fb754c7-nrbhl        1/1     Running   0          77m
nyx-postgres-5f5f4d5847-lrz9v   1/1     Running   0          77m
```

### 2026-09-20T02:15:28-03:00 — `kubectl get svc,endpoints -n nyx-stg` (rc=0, 216 ms)
```
NAME                   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/nyx-api        ClusterIP   10.96.244.128   <none>        80/TCP     84m
service/nyx-postgres   ClusterIP   10.96.247.130   <none>        5432/TCP   84m

NAME                     ENDPOINTS          AGE
endpoints/nyx-api        <none>             84m
endpoints/nyx-postgres   10.244.0.11:5432   84m

[stderr]
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
```

> **Raciocínio** (2026-09-20T02:19:21-03:00): Service nyx-api existe mas os endpoints estão vazios, enquanto o do postgres tem IP. Pods prontos + endpoints vazios = nenhum pod casa com o seletor. Vou cruzar o seletor do Service com os rótulos dos pods


### 2026-09-20T02:19:22-03:00 — `kubectl describe svc nyx-api -n nyx-stg` (rc=0, 172 ms)
```
Name:                     nyx-api
Namespace:                nyx-stg
Labels:                   <none>
Annotations:              <none>
Selector:                 app=nyx-api
Type:                     ClusterIP
IP Family Policy:         SingleStack
IP Families:              IPv4
IP:                       10.96.244.128
IPs:                      10.96.244.128
Port:                     <unset>  80/TCP
TargetPort:               8080/TCP
Endpoints:                
Session Affinity:         None
Internal Traffic Policy:  Cluster
Events:                   <none>
```

### 2026-09-20T02:19:25-03:00 — `kubectl get pods -n nyx-stg --show-labels` (rc=0, 117 ms)
```
NAME                            READY   STATUS    RESTARTS   AGE   LABELS
nyx-api-656fb754c7-gdbtn        1/1     Running   0          88m   app=nyxapi,pod-template-hash=656fb754c7
nyx-api-656fb754c7-nrbhl        1/1     Running   0          88m   app=nyxapi,pod-template-hash=656fb754c7
nyx-postgres-5f5f4d5847-lrz9v   1/1     Running   0          88m   app=nyx-postgres,pod-template-hash=5f5f4d5847
```

## Causa identificada (2026-09-20T02:21:19-03:00): metadado/rótulos — o seletor do Service nyx-api (app=nyx-api) não casa com o rótulo dos pods (app=nyxapi); o Service fica sem endpoints e quem chama recebe 503 — get endpoints: nyx-api <none> vs nyx-postgres com IP; describe svc: Selector app=nyx-api, Endpoints vazio; get pods --show-labels: app=nyxapi; pods 1/1 Running com readiness passando


> **Raciocínio** (2026-09-20T02:21:19-03:00): funcionando ao lado: pods da API 1/1 Running com 0 restarts e readiness passando; nyx-postgres 1/1 com endpoint preenchido. Lição de método: nem o pod nem o Service sozinhos mostram o erro, só o cruzamento seletor x rótulos; e o aviso de Endpoints depreciado importa para o Ticket 04


---
**Fim:** 2026-09-20T02:21:24-03:00

