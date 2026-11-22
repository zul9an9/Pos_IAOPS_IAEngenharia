# cmp-chamado-1-sem-skill-r1

**Prompt:** Chamado do cliente nyx: a API do kube-news em nyx-prod reinicia sozinha. Faz a triagem e me diz a causa.

**Lab:** lab-sem-skills

**Skills:** nenhuma

**Ferramentas:** 7 chamadas

**Tentativas de escrita:** nenhuma

---

Confirmado nas duas réplicas — o mesmo padrão. Causa raiz identificada, sem necessidade de mais investigação.

## Triagem — nyx-prod / kube-news API

**Causa raiz: OOMKilled — limite de memória do container subdimensionado.**

Os dois pods `nyx-api` (`nyx-api-7665bb6885-6z4hd` e `-zhqk6`) estão em `CrashLoopBackOff` há ~8h, com 35-36 reinícios cada. O último estado do container mostra:

```
Last State:  Terminated
Reason:      OOMKilled
Exit Code:   137
Limits:      memory: 24Mi   (requests: 16Mi)
```

Sequência do problema:
1. Container sobe consumindo mais memória do que o limite de **24Mi** permite.
2. Kernel mata o processo (OOM Kill, exit code 137).
3. Kubelet reinicia o container → volta a estourar o limite → novo OOMKill.
4. Com falhas repetidas, entra em `CrashLoopBackOff` (backoff crescente entre tentativas).
5. Como o app nunca fica de pé tempo suficiente, a readiness probe (`GET /ready`) também falha por timeout, então o pod nunca fica `Ready` e a API fica indisponível.

O banco (`nyx-postgres`) está saudável (`1/1 Running`, 0 restarts) e as credenciais/env vars de conexão parecem corretas — não é um problema de banco.

**24Mi é extremamente baixo** para uma API Go/HTTP típica (o kube-news costuma precisar de bem mais que isso só para subir o runtime + servidor HTTP). Isso bate com o padrão observado: sobe, estoura memória quase imediatamente, morre.

### Recomendação de correção
Aumentar o `resources.limits.memory` do deployment `nyx-api` (ex.: para 128Mi–256Mi, ajustando requests proporcionalmente) e validar o consumo real com `kubectl top pod` após a mudança.

Posso aplicar o patch no deployment se você quiser (ex.: `kubectl patch deployment nyx-api -n nyx-prod` ajustando o limite de memória) — quer que eu faça isso agora?
