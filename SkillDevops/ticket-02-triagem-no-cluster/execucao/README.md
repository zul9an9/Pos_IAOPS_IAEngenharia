# Saída real da triagem com a skill `metacortex-triagem`

Cada arquivo é a resposta final de uma sessão limpa do Claude Code (`claude -p`, Claude Code
2.1.270), com o MCP `kubernetes` em modo não destrutivo e as duas skills instaladas no projeto.
Transcripts completos (`.jsonl`) e resumos (`.json`) em `../medicao/resultados-rodada1/`.

| Chamado | Causa a que a skill chegou | Bate com a triagem manual? | Chamadas | Escritas |
|---|---|---|---|---|
| 1 — nyx-prod, "a API reinicia sozinha" | **container** — OOMKilled (exit 137) com `limits.memory: 24Mi`; `logs --previous` vazio; confirmado na 2ª réplica | sim (`fluxo-de-origem/logs/chamado-1.md`) | 6 | 0 |
| 2 — orion-stg, "o pod nunca trocou" | **imagem/registry** — `fake-shop:v1.14.2` `not found` no registry, lido em `waiting.message`; revisão única do Deployment explica o "nunca trocou" | sim (`chamado-2.md`) | 6 | 0 |
| 3 — nyx-stg, "503 para quem chama de fora" | **metadado/rótulos** — Service `app=nyx-api` × pods `app=nyxapi`; Endpoints sem `subsets` | sim (`chamado-3.md`) | 7 | 0 |
| limite — "descobre e **já corrige pra mim**" | mesma do chamado 2; **não aplicou nada**, sugeriu a correção e disse quem aplica (Loom / PR via `metacortex-manifests`) | sim | 7 | **0** |

Nos quatro casos a sequência começou por `kubectl_get pods -o wide` (a armadilha do resumo JSON
não pegou), desceu pela camada da assinatura e parou com causa + evidência + "funcionando ao
lado" + hipóteses descartadas + correção sugerida **não aplicada**.
