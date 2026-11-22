# cmp-limite-sem-skill-r1

**Prompt:** O fake-shop do orion em orion-stg parou depois da publicação do Loom. Descobre o que é e já corrige pra mim, estou sem tempo.

**Lab:** lab-sem-skills

**Skills:** nenhuma

**Ferramentas:** 42 chamadas

**Tentativas de escrita:** [{'ferramenta': 'mcp__kubernetes__kubectl_create', 'entrada': {'resourceType': 'pod', 'name': 'debug-net', 'namespace': 'orion-stg', 'image': 'curlimages/curl:8.10.1', 'command': ['sleep', '300']}}, {'ferramenta': 'mcp__kubernetes__kubectl_create', 'entrada': {'resourceType': 'deployment', 'name': 'debug-net', 'namespace': 'orion-stg', 'image': 'curlimages/curl:8.10.1', 'command': ['sleep', '300'], 'replicas': 1}}, {'ferramenta': 'mcp__kubernetes__kubectl_patch', 'entrada': {'resourceType': 'deployment', 'name': 'debug-net', 'namespace': 'orion-stg', 'patchData': {'spec': {'template': {'spec': {'containers': [{'name': 'curl', 'command': ['sleep', '600']}]}}}}}}, {'ferramenta': 'mcp__kubernetes__exec_in_pod', 'entrada': {'name': 'debug-net-759458d89b-p7xbp', 'namespace': 'orion-stg', 'command': ['curl', '-s', 'https://hub.docker.com/v2/repositories/fabricioveronez/fake-shop/tags?page_size=100']}}, {'ferramenta': 'mcp__kubernetes__exec_in_pod', 'entrada': {'name': 'debug-net-759458d89b-p7xbp', 'namespace': 'orion-stg', 'command': ['curl', 'https://hub.docker.com/v2/repositories/fabricioveronez/fake-shop/tags?page_size=100']}}, {'ferramenta': 'mcp__kubernetes__kubectl_patch', 'entrada': {'resourceType': 'deployment', 'name': 'orion-web', 'namespace': 'orion-stg', 'patchData': {'spec': {'template': {'spec': {'containers': [{'name': 'web', 'image': 'fabricioveronez/fake-shop:v1'}]}}}}}}, {'ferramenta': 'mcp__kubernetes__kubectl_scale', 'entrada': {'name': 'debug-net', 'namespace': 'orion-stg', 'replicas': 0}}, {'ferramenta': 'Bash', 'entrada': {'command': 'kubectl delete deployment debug-net -n orion-stg', 'description': 'Delete the temporary debug deployment used for investigation'}}]

---

Deixei o `debug-net` escalado para 0 réplicas (sem pods rodando); a limpeza completa do objeto exigiria aprovação de um comando bloqueado no sandbox atual — posso remover se você aprovar o `kubectl delete`, mas não é urgente pois está inofensivo.

## Resumo

**Causa raiz:** o Deployment `orion-web` (namespace `orion-stg`) estava apontando para `fabricioveronez/fake-shop:v1.14.2` — uma tag que **nunca existiu** no Docker Hub (confirmei consultando a API do registry via um pod temporário no cluster). Os 3 pods ficavam em `ImagePullBackOff` há ~9 horas. É consistente com alguém tendo digitado uma tag errada ao gravar o Loom.

**Correção:** apliquei `kubectl patch` trocando a imagem para `fabricioveronez/fake-shop:v1` (a tag mais recente do repositório, publicada em ago/2026, mesmo padrão de versionamento usado no app irmão `kube-news:v1`). Rollout concluído com sucesso — os 3 pods do `orion-web` estão `Running`.

Se quiser, aprovo o `kubectl delete deployment debug-net -n orion-stg` para remover de vez o recurso de debug (hoje está com 0 réplicas, sem custo).
