# Triagem manual — chamado 1

**Início:** 2026-09-20T01:32:18-03:00  
**Sintoma declarado:** cliente nyx: a API do kube-news em nyx-prod reinicia sozinha


> **Raciocínio** (2026-09-20T01:32:19-03:00): primeiro quero ver o estado dos pods do namespace: quais estão de pé, quais não, e quantos reinícios


### 2026-09-20T01:32:22-03:00 — `kubectl get pods -n nyx-prod` (rc=0, 297 ms)
```
NAME                            READY   STATUS             RESTARTS         AGE
nyx-api-7665bb6885-6z4hd        0/1     CrashLoopBackOff   12 (2m45s ago)   40m
nyx-api-7665bb6885-zhqk6        0/1     CrashLoopBackOff   12 (3m3s ago)    40m
nyx-postgres-5f5f4d5847-pd4hw   1/1     Running            0                40m
```

> **Raciocínio** (2026-09-20T01:37:58-03:00): as duas réplicas da API em CrashLoopBackOff com 12 restarts e o postgres saudável; o banco não parece ser o problema. Preciso saber por que o container morre: vou ver o estado anterior do container no describe


### 2026-09-20T01:38:16-03:00 — `kubectl describe pod nyx-api-7665bb6885-6z4hd -n nyx-prod` (rc=0, 278 ms)
```
Name:             nyx-api-7665bb6885-6z4hd
Namespace:        nyx-prod
Priority:         0
Service Account:  default
Node:             metacortex-lab-control-plane/172.18.0.2
Start Time:       Sun, 20 Sep 2026 00:51:25 -0300
Labels:           app=nyx-api
                  pod-template-hash=7665bb6885
Annotations:      <none>
Status:           Running
IP:               10.244.0.7
IPs:
  IP:           10.244.0.7
Controlled By:  ReplicaSet/nyx-api-7665bb6885
Containers:
  api:
    Container ID:   containerd://5b89de9d3ef1e582d5abdc379a388f71d1aa743aa9191367d1f429837ec8afd1
    Image:          fabricioveronez/kube-news:v1
    Image ID:       docker.io/fabricioveronez/kube-news@sha256:f86b40ce1bcbdf297b6236a8212f3e66c8412113aaa8855ba2747c79182734e5
    Port:           8080/TCP
    Host Port:      0/TCP
    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Sun, 20 Sep 2026 01:35:02 -0300
      Finished:     Sun, 20 Sep 2026 01:35:06 -0300
    Ready:          False
    Restart Count:  13
    Limits:
      cpu:     200m
      memory:  24Mi
    Requests:
      cpu:      50m
      memory:   16Mi
    Readiness:  http-get http://:8080/ready delay=10s timeout=1s period=10s #success=1 #failure=3
    Environment:
      DB_HOST:      nyx-postgres
      DB_DATABASE:  kubedevnews
      DB_USERNAME:  kubedevnews
      DB_PASSWORD:  Pg#123
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-gbjvx (ro)
Conditions:
  Type                        Status
  PodReadyToStartContainers   True 
  Initialized                 True 
  Ready                       False 
  ContainersReady             False 
  PodScheduled                True 
Volumes:
  kube-api-access-gbjvx:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    ConfigMapOptional:       <nil>
    DownwardAPI:             true
QoS Class:                   Burstable
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Type     Reason     Age                   From               Message
  ----     ------     ----                  ----               -------
  Normal   Scheduled  46m                   default-scheduler  Successfully assigned nyx-prod/nyx-api-7665bb6885-6z4hd to metacortex-lab-control-plane
  Normal   Pulling    46m                   kubelet            Pulling image "fabricioveronez/kube-news:v1"
  Normal   Pulled     46m                   kubelet            Successfully pulled image "fabricioveronez/kube-news:v1" in 954ms (29.29s including waiting). Image size: 64599163 bytes.
  Normal   Created    29m (x9 over 46m)     kubelet            Container created
  Normal   Started    29m (x9 over 46m)     kubelet            Container started
  Normal   Pulled     3m14s (x13 over 46m)  kubelet            Container image "fabricioveronez/kube-news:v1" already present on machine and can be accessed by the pod
  Warning  BackOff    60s (x41 over 46m)    kubelet            Back-off restarting failed container api in pod nyx-api-7665bb6885-6z4hd_nyx-prod(4abb464a-0ab8-40d3-a231-3e3bac3fccae)
```

> **Raciocínio** (2026-09-20T01:44:28-03:00): as duas réplicas da API em CrashLoopBackOff com 12 restarts e o postgres saudável; o banco não parece ser o problema. Preciso saber por que o container morre: vou ver o estado anterior do container no describe


### 2026-09-20T01:48:36-03:00 — `kubectl logs nyx-api-7665bb6885-6z4hd -n nyx-prod --previous` (rc=0, 378 ms)
```

```

### 2026-09-20T01:49:01-03:00 — `kubectl logs nyx-api-7665bb6885-6z4hd -n nyx-prod --previous` (rc=0, 119 ms)
```

```

### 2026-09-20T01:49:04-03:00 — `kubectl logs nyx-api-7665bb6885-6z4hd -n nyx-prod --previous` (rc=0, 107 ms)
```

```

### 2026-09-20T01:49:16-03:00 — `kubectl describe pod nyx-api-7665bb6885-6z4hd -n nyx-prod` (rc=0, 173 ms)
```
Name:             nyx-api-7665bb6885-6z4hd
Namespace:        nyx-prod
Priority:         0
Service Account:  default
Node:             metacortex-lab-control-plane/172.18.0.2
Start Time:       Sun, 20 Sep 2026 00:51:25 -0300
Labels:           app=nyx-api
                  pod-template-hash=7665bb6885
Annotations:      <none>
Status:           Running
IP:               10.244.0.7
IPs:
  IP:           10.244.0.7
Controlled By:  ReplicaSet/nyx-api-7665bb6885
Containers:
  api:
    Container ID:   containerd://44e80da72a25c62647f3790345bb1a3fe9ef91bddbfcf135d5f057886911df97
    Image:          fabricioveronez/kube-news:v1
    Image ID:       docker.io/fabricioveronez/kube-news@sha256:f86b40ce1bcbdf297b6236a8212f3e66c8412113aaa8855ba2747c79182734e5
    Port:           8080/TCP
    Host Port:      0/TCP
    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Sun, 20 Sep 2026 01:45:48 -0300
      Finished:     Sun, 20 Sep 2026 01:45:52 -0300
    Ready:          False
    Restart Count:  15
    Limits:
      cpu:     200m
      memory:  24Mi
    Requests:
      cpu:      50m
      memory:   16Mi
    Readiness:  http-get http://:8080/ready delay=10s timeout=1s period=10s #success=1 #failure=3
    Environment:
      DB_HOST:      nyx-postgres
      DB_DATABASE:  kubedevnews
      DB_USERNAME:  kubedevnews
      DB_PASSWORD:  Pg#123
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-gbjvx (ro)
Conditions:
  Type                        Status
  PodReadyToStartContainers   True 
  Initialized                 True 
  Ready                       False 
  ContainersReady             False 
  PodScheduled                True 
Volumes:
  kube-api-access-gbjvx:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    ConfigMapOptional:       <nil>
    DownwardAPI:             true
QoS Class:                   Burstable
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Type     Reason     Age                   From               Message
  ----     ------     ----                  ----               -------
  Normal   Scheduled  57m                   default-scheduler  Successfully assigned nyx-prod/nyx-api-7665bb6885-6z4hd to metacortex-lab-control-plane
  Normal   Pulling    57m                   kubelet            Pulling image "fabricioveronez/kube-news:v1"
  Normal   Pulled     57m                   kubelet            Successfully pulled image "fabricioveronez/kube-news:v1" in 954ms (29.29s including waiting). Image size: 64599163 bytes.
  Normal   Created    40m (x9 over 57m)     kubelet            Container created
  Normal   Started    40m (x9 over 57m)     kubelet            Container started
  Normal   Pulled     3m28s (x15 over 57m)  kubelet            Container image "fabricioveronez/kube-news:v1" already present on machine and can be accessed by the pod
  Warning  BackOff    75s (x50 over 57m)    kubelet            Back-off restarting failed container api in pod nyx-api-7665bb6885-6z4hd_nyx-prod(4abb464a-0ab8-40d3-a231-3e3bac3fccae)
```

### 2026-09-20T01:49:30-03:00 — `kubectl logs nyx-api-7665bb6885-6z4hd -n nyx-prod --previous` (rc=0, 110 ms)
```

```

> **Raciocínio** (2026-09-20T01:53:20-03:00): log --previous vazio: a aplicação não registrou erro nenhum antes de morrer, então descarto falha da própria aplicação ou do banco; o processo foi morto de fora


## Causa identificada (2026-09-20T01:53:21-03:00): recursos do container — limite de memória de 24Mi abaixo do que o Node precisa para subir; o kernel mata o processo por falta de memória — describe: Last State Terminated/OOMKilled, Exit Code 137, Limits memory 24Mi; container viveu ~4s; logs --previous vazio


> **Raciocínio** (2026-09-20T01:53:21-03:00): funcionando ao lado: nyx-postgres 1/1 Running com 0 restarts; imagem baixada com sucesso; pod agendado normalmente no nó


---
**Fim:** 2026-09-20T01:53:26-03:00

