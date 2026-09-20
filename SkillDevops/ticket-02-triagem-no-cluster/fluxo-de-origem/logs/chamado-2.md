# Triagem manual — chamado 2

**Início:** 2026-09-20T01:58:46-03:00  
**Sintoma declarado:** cliente orion: a loja do fake-shop em orion-stg parou depois de uma publicação do Loom; a tag foi anunciada, o deploy foi aplicado, mas o pod nunca trocou


> **Raciocínio** (2026-09-20T01:58:46-03:00): começo pelo estado dos pods do namespace para ver o que está de pé e o que não está


### 2026-09-20T01:58:49-03:00 — `kubectl get pods -n orion-stg` (rc=0, 111 ms)
```
NAME                              READY   STATUS             RESTARTS   AGE
orion-postgres-5595f8958d-rmtvv   1/1     Running            0          67m
orion-web-67888d986c-5ttt6        0/1     ImagePullBackOff   0          67m
orion-web-67888d986c-9mnkz        0/1     ImagePullBackOff   0          67m
orion-web-67888d986c-w4m5g        0/1     ImagePullBackOff   0          67m
```

> **Raciocínio** (2026-09-20T02:01:17-03:00): <sua leitura: o que o ImagePullBackOff com 0 restarts indica e o que você quer descobrir agora>


### 2026-09-20T02:01:20-03:00 — `kubectl describe pod orion-web-67888d986c-5ttt6 -n orion-stg` (rc=0, 179 ms)
```
Name:             orion-web-67888d986c-5ttt6
Namespace:        orion-stg
Priority:         0
Service Account:  default
Node:             metacortex-lab-control-plane/172.18.0.2
Start Time:       Sun, 20 Sep 2026 00:51:25 -0300
Labels:           app=orion-web
                  pod-template-hash=67888d986c
Annotations:      <none>
Status:           Pending
IP:               10.244.0.12
IPs:
  IP:           10.244.0.12
Controlled By:  ReplicaSet/orion-web-67888d986c
Containers:
  web:
    Container ID:   
    Image:          fabricioveronez/fake-shop:v1.14.2
    Image ID:       
    Port:           5000/TCP
    Host Port:      0/TCP
    State:          Waiting
      Reason:       ImagePullBackOff
    Ready:          False
    Restart Count:  0
    Environment:
      DB_HOST:                   orion-postgres
      DB_NAME:                   ecommerce
      DB_USER:                   ecommerce
      DB_PASSWORD:               Pg1234
      FLASK_APP:                 index.py
      PROMETHEUS_MULTIPROC_DIR:  /tmp/metrics
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-vh2jw (ro)
Conditions:
  Type                        Status
  PodReadyToStartContainers   True 
  Initialized                 True 
  Ready                       False 
  ContainersReady             False 
  PodScheduled                True 
Volumes:
  kube-api-access-vh2jw:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    ConfigMapOptional:       <nil>
    DownwardAPI:             true
QoS Class:                   BestEffort
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Type     Reason   Age                    From     Message
  ----     ------   ----                   ----     -------
  Normal   BackOff  4m54s (x280 over 69m)  kubelet  Back-off pulling image "fabricioveronez/fake-shop:v1.14.2"
  Warning  Failed   4m12s (x283 over 69m)  kubelet  Error: ImagePullBackOff
```

> **Raciocínio** (2026-09-20T02:03:29-03:00): corrige a nota anterior (texto de modelo gravado por engano): ImagePullBackOff com 0 restarts indica que o container nunca chegou a rodar; o problema é antes da execução, no download da imagem. Quero descobrir por que o pull falha


> **Raciocínio** (2026-09-20T02:05:16-03:00): eventos só mostram o back-off; a mensagem original do pull já saiu da janela. O postgres baixou de registry público, então descarto rede. Vou ler a mensagem de espera no status do container para ver o erro do registry


### 2026-09-20T02:05:20-03:00 — `kubectl get pod orion-web-67888d986c-5ttt6 -n orion-stg -o jsonpath={.status.containerStatuses[0].state.waiting.message}` (rc=0, 132 ms)
```
Back-off pulling image "fabricioveronez/fake-shop:v1.14.2": ErrImagePull: rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/fabricioveronez/fake-shop:v1.14.2": failed to resolve reference "docker.io/fabricioveronez/fake-shop:v1.14.2": docker.io/fabricioveronez/fake-shop:v1.14.2: not found
```

> **Raciocínio** (2026-09-20T02:07:44-03:00): a mensagem de espera trouxe o erro do registry: NotFound. O registry respondeu, então não é rede nem credencial; a referência da imagem não existe


## Causa identificada (2026-09-20T02:07:44-03:00): imagem/registry — a tag fabricioveronez/fake-shop:v1.14.2 anunciada no release não existe no registry; o pull falha e o container nunca é criado — status do container: ErrImagePull code=NotFound 'docker.io/fabricioveronez/fake-shop:v1.14.2: not found'; eventos: Back-off pulling image x280; restarts 0; Image ID vazio


> **Raciocínio** (2026-09-20T02:07:45-03:00): funcionando ao lado: orion-postgres 1/1 Running com 0 restarts; pull de imagens públicas funcionando (postgres, kube-news), rede até o registry ok; pods agendados no nó. Lição de método: os eventos só guardavam o back-off, a mensagem original tinha saído da janela; o motivo estava no status do container


---
**Fim:** 2026-09-20T02:07:50-03:00

