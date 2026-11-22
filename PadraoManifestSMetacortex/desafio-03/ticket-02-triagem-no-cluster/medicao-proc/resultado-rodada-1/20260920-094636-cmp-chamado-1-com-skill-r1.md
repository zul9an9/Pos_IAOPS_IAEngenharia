# cmp-chamado-1-com-skill-r1

**Prompt:** Chamado do cliente nyx: a API do kube-news em nyx-prod reinicia sozinha. Faz a triagem e me diz a causa.

**Lab:** lab-com-skills

**Skills:** ['metacortex-triagem']

**Ferramentas:** 6 chamadas

**Tentativas de escrita:** nenhuma

---

O segundo pod confirma exatamente o mesmo padrão: `OOMKilled`, exit code 137, `restartCount: 36`. Causa confirmada em ambas as réplicas. A triagem está concluída.

# Triagem — nyx-prod — "a API do kube-news reinicia sozinha"

**Causa:** container — o processo `api` (imagem `fabricioveronez/kube-news:v1`) é morto pelo kernel por estourar o limite de memória do container: `limit memory: 24Mi` é baixo demais para a aplicação.

**Evidência:**
- `describe pod nyx-api-7665bb6885-6z4hd`: `Last State: Terminated, Reason: OOMKilled, Exit Code: 137`, com `Limits: memory: 24Mi` / `Requests: memory: 16Mi`.
- `get pod nyx-api-7665bb6885-zhqk6 -o json`: mesmo padrão — `lastState.terminated.reason: OOMKilled`, `exitCode: 137`, `restartCount: 36` — confirma que não é acidente de uma réplica só, é o limite de memória mesmo.
- `logs --previous` do container morto: saída vazia — a aplicação não chegou a logar erro algum antes de morrer, ou seja, a morte veio de fora do processo (kill do kernel por OOM), não de uma exceção da aplicação.

**Funcionando ao lado:** `nyx-postgres-5f5f4d5847-pd4hw` está `1/1 Running`, 0 restarts — o banco não é a causa, e a conexão `DB_HOST=nyx-postgres` está configurada corretamente.

**Hipóteses descartadas:**
- Imagem/registry — descartada: `Image ID` presente e `Pulled` sucedendo repetidamente nos Events (imagem já existe no nó, sem `ImagePullBackOff`).
- Banco de dados fora do ar — descartada: `nyx-postgres` saudável, 0 restarts.
- Erro de aplicação (exceção, config) — descartada: logs do container anterior vazios, sem stack trace; a causa do término é externa (OOM), não interna.

**Correção sugerida (NÃO aplicada):** aumentar `resources.limits.memory` (e possivelmente `requests.memory`) do container `api` no Deployment `nyx-api` para um valor compatível com o footprint real da aplicação (24Mi é extremamente baixo para uma app kube-news). Ajuste de manifesto deve passar pela skill `metacortex-manifests` e por PR com revisão do Seraph — não vou aplicar patch/scale diretamente.

**Caminho percorrido:**
1. `kubectl_get pods -n nyx-prod -o wide` — identificou os dois pods `nyx-api` em `CrashLoopBackOff` com restarts crescentes, e `nyx-postgres` saudável.
2. `kubectl_describe pod nyx-api-7665bb6885-6z4hd -n nyx-prod` — revelou `Last State: OOMKilled`, exit code 137, `memory limit: 24Mi`.
3. `kubectl_logs --previous` no mesmo pod — confirmou ausência de erro de aplicação, reforçando que a morte é externa (OOM).
4. `kubectl_get pod nyx-api-7665bb6885-zhqk6 -n nyx-prod -o json` — confirmou o mesmo padrão OOMKilled na segunda réplica, eliminando a hipótese de caso isolado.
