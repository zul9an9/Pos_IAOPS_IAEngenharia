# cmp-chamado-2-com-skill-r1

**Prompt:** Chamado do cliente orion: a loja do fake-shop em orion-stg parou depois de uma publicação do Loom; a tag foi anunciada e o deploy aplicado, mas o pod nunca trocou. Faz a triagem e me diz a causa.

**Lab:** lab-com-skills

**Skills:** ['metacortex-triagem']

**Ferramentas:** 6 chamadas

**Tentativas de escrita:** nenhuma

---

## Triagem — orion-stg — "loja do fake-shop parou depois da publicação do Loom"

**Causa:** imagem/registry — a tag `fabricioveronez/fake-shop:v1.14.2` anunciada pelo Loom não existe no `docker.io`

**Evidência:**
- `status.containerStatuses[].state.waiting.message` do pod `orion-web-67888d986c-5ttt6`: `"...failed to resolve reference \"docker.io/fabricioveronez/fake-shop:v1.14.2\": docker.io/fabricioveronez/fake-shop:v1.14.2: not found"` — mensagem original do registry, não só o back-off dos eventos
- Deployment `orion-web`: `revision: "1"` (é a única revisão — não há ReplicaSet antigo por trás), `status.conditions`: `Progressing=False / ProgressDeadlineExceeded` ("ReplicaSet has timed out progressing") e `Available=False / MinimumReplicasUnavailable`

**Funcionando ao lado:** `orion-postgres` — `1/1 Running`, 0 restarts, saudável

**Hipóteses descartadas:**
- Container crashando (CrashLoopBackOff/OOM) — descartada: RESTARTS=0 em todos os pods `orion-web`, não `Error`/`OOMKilled`
- "Pod antigo não foi substituído" (problema de rollout) — descartada: `revision: 1` no Deployment, não existe ReplicaSet anterior; os 3 pods já são da versão nova (`orion-web-67888d986c`, mesmo `pod-template-hash` da spec atual) — eles nunca chegaram a subir, não é uma troca travada

**Correção sugerida (NÃO aplicada):** confirmar com o time do Loom se a tag `v1.14.2` foi de fato publicada no `docker.io/fabricioveronez/fake-shop` (parece ter sido anunciada antes do push terminar, ou o nome/tag está errado). Corrigido o publish, o Deployment vai puxar a imagem automaticamente (`imagePullPolicy: IfNotPresent`, sem necessidade de reaplicar). Nenhuma alteração de manifesto é necessária.

**Caminho percorrido:**
1. `kubectl_get pods -n orion-stg -o wide` → 3 pods `orion-web` em `ImagePullBackOff`, `orion-postgres` saudável
2. `kubectl_describe pod orion-web-67888d986c-5ttt6` → eventos só com back-off repetido, imagem `fabricioveronez/fake-shop:v1.14.2`
3. `kubectl_get pod ... -o json` → mensagem completa do registry: `not found`
4. `kubectl_get deployment orion-web -o json` → confirma revisão única, sem rollout anterior, `ProgressDeadlineExceeded`
