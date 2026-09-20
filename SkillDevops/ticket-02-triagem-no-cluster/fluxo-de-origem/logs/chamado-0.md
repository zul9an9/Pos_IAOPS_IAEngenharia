# Triagem manual — chamado 0

**Início:** 2026-09-20T01:08:28-03:00  
**Sintoma declarado:** foto do estado inicial do cluster (kind, cgroup v2)


### 2026-09-20T01:08:29-03:00 — `kubectl get pods -A -o wide` (rc=0, 357 ms)
```
NAMESPACE            NAME                                                   READY   STATUS             RESTARTS        AGE   IP            NODE                           NOMINATED NODE   READINESS GATES
kube-system          coredns-559f6c778d-59p6n                               1/1     Running            0               19m   10.244.0.3    metacortex-lab-control-plane   <none>           <none>
kube-system          coredns-559f6c778d-zlz6x                               1/1     Running            0               19m   10.244.0.2    metacortex-lab-control-plane   <none>           <none>
kube-system          etcd-metacortex-lab-control-plane                      1/1     Running            0               20m   172.18.0.2    metacortex-lab-control-plane   <none>           <none>
kube-system          kindnet-rfjc9                                          1/1     Running            0               19m   172.18.0.2    metacortex-lab-control-plane   <none>           <none>
kube-system          kube-apiserver-metacortex-lab-control-plane            1/1     Running            0               20m   172.18.0.2    metacortex-lab-control-plane   <none>           <none>
kube-system          kube-controller-manager-metacortex-lab-control-plane   1/1     Running            0               20m   172.18.0.2    metacortex-lab-control-plane   <none>           <none>
kube-system          kube-proxy-rtp58                                       1/1     Running            0               19m   172.18.0.2    metacortex-lab-control-plane   <none>           <none>
kube-system          kube-scheduler-metacortex-lab-control-plane            1/1     Running            0               20m   172.18.0.2    metacortex-lab-control-plane   <none>           <none>
local-path-storage   local-path-provisioner-75f7fc7dc5-gpq87                1/1     Running            0               19m   10.244.0.4    metacortex-lab-control-plane   <none>           <none>
nyx-prod             nyx-api-7665bb6885-6z4hd                               0/1     CrashLoopBackOff   7 (5m8s ago)    17m   10.244.0.7    metacortex-lab-control-plane   <none>           <none>
nyx-prod             nyx-api-7665bb6885-zhqk6                               0/1     OOMKilled          8 (5m20s ago)   17m   10.244.0.6    metacortex-lab-control-plane   <none>           <none>
nyx-prod             nyx-postgres-5f5f4d5847-pd4hw                          1/1     Running            0               17m   10.244.0.5    metacortex-lab-control-plane   <none>           <none>
nyx-stg              nyx-api-656fb754c7-gdbtn                               1/1     Running            0               17m   10.244.0.14   metacortex-lab-control-plane   <none>           <none>
nyx-stg              nyx-api-656fb754c7-nrbhl                               1/1     Running            0               17m   10.244.0.13   metacortex-lab-control-plane   <none>           <none>
nyx-stg              nyx-postgres-5f5f4d5847-lrz9v                          1/1     Running            0               17m   10.244.0.11   metacortex-lab-control-plane   <none>           <none>
orion-stg            orion-postgres-5595f8958d-rmtvv                        1/1     Running            0               17m   10.244.0.8    metacortex-lab-control-plane   <none>           <none>
orion-stg            orion-web-67888d986c-5ttt6                             0/1     ErrImagePull       0               17m   10.244.0.12   metacortex-lab-control-plane   <none>           <none>
orion-stg            orion-web-67888d986c-9mnkz                             0/1     ImagePullBackOff   0               17m   10.244.0.9    metacortex-lab-control-plane   <none>           <none>
orion-stg            orion-web-67888d986c-w4m5g                             0/1     ImagePullBackOff   0               17m   10.244.0.10   metacortex-lab-control-plane   <none>           <none>
```

---
**Fim:** 2026-09-20T01:08:29-03:00

