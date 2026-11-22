# cmp-chamado-3-com-skill-r1

**Prompt:** Chamado do cliente nyx: o kube-news em nyx-stg responde 503 para quem chama de fora. Faz a triagem e me diz a causa.

**Lab:** lab-com-skills

**Skills:** ['metacortex-triagem']

**Ferramentas:** 7 chamadas

**Tentativas de escrita:** nenhuma

---

Confirmado: o pod tem o rótulo `app=nyxapi` e o objeto Endpoints do Service `nyx-api` não traz nenhum campo `subsets` — ou seja, zero endpoints. Isso bate exatamente com o mismatch de seletor (Service pede `app=nyx-api`, pods têm `app=nyxapi`). Causa confirmada, com pods saudáveis e probes passando — o tráfego simplesmente nunca chega até eles.

# Triagem — nyx-stg — "kube-news responde 503 para chamadas externas"

**Causa:** metadado/rótulos — o Service `nyx-api` usa `selector: app=nyx-api`, mas os pods do Deployment `nyx-api` têm o rótulo `app=nyxapi` (sem hífen). Nenhum pod casa com o seletor.

**Evidência:**
- `kubectl_get services -o wide` em `nyx-stg`: Service `nyx-api` → `SELECTOR: app=nyx-api`.
- `kubectl_get pods nyx-api-656fb754c7-gdbtn -o json`: `metadata.labels.app = "nyxapi"`.
- `kubectl_get endpoints nyx-api -o json`: objeto sem campo `subsets` — zero endpoints registrados (ausência = zero), confirmando que o Service não tem para onde mandar tráfego.

**Funcionando ao lado:**
- Pods `nyx-api-656fb754c7-*` (2/2) e `nyx-postgres-*` (1/1): todos `Running`, 0 restarts, 8h de idade.
- Readiness (`/ready`) e liveness (`/health`) do container `api` passando (`Ready: True`, `ContainersReady: True`).
- Deployment `nyx-api` reporta `2/2` réplicas disponíveis — a aplicação em si está saudável.

**Hipóteses descartadas:**
- Container quebrando (CrashLoop/OOM) — descartado: RESTARTS=0 em todos os pods.
- Imagem/registry — descartado: `imageID` presente e `IfNotPresent` resolvido normalmente, sem `ImagePullBackOff`.
- Banco de dados fora do ar — descartado: `nyx-postgres` 1/1 Running, 0 restarts.

**Correção sugerida (NÃO aplicada):** alinhar o seletor do Service `nyx-api` para `app=nyxapi` (ou trocar o rótulo do Deployment/pods para `app=nyx-api`, mantendo consistência com o restante do padrão). Essa correção é de manifesto — passa pela skill `metacortex-manifests` e por PR com revisão; não deve ser aplicada diretamente no cluster.

**Caminho percorrido:**
1. `kubectl_get pods -n nyx-stg -o wide` → todos Running, 0 restarts.
2. `kubectl_get deployments -n nyx-stg -o wide` → Deployment `nyx-api` selector `app=nyxapi`.
3. `kubectl_get services -n nyx-stg -o wide` → Service `nyx-api` selector `app=nyx-api`.
4. `kubectl_get pods nyx-api-656fb754c7-gdbtn -o json` → confirma label real `app=nyxapi`.
5. `kubectl_get endpoints nyx-api -o json` → confirma ausência de `subsets` (zero endpoints).
