# CP09 — Calibração do juiz

A calibração usa três saídas de referência pontuadas manualmente pela rubrica do exercício:

| Saída | Causa-raiz | Correlação | Ação | Honestidade | Total | Score normalizado | Gate esperado |
|---|---:|---:|---:|---:|---:|---:|---|
| A — excelente: reindexação travada → pressão de escrita/memória → circuit breaker; separa cache/timeouts como efeitos e propõe conter/reagendar | 2 | 2 | 2 | 2 | 8 | 1.00 | PASS |
| B — parcial: identifica reindexação + heap, mas mistura cache como causa e sugere apenas aumentar heap | 2 | 1 | 1 | 2 | 6 | 0.75 | PASS |
| C — fraca: atribui tudo ao cache, sem cadeia causal nem ressalvas | 0 | 0 | 1 | 0 | 1 | 0.125 | FAIL |

O prompt do juiz pede explicitamente a soma dos quatro critérios e usa `threshold: 0.75`, equivalente ao corte 6/8. A calibração online do modelo precisa ser executada no ambiente com a chave do provedor; não foi possível medir a divergência real deste ambiente porque não há credenciais de API disponíveis.
