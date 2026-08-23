# CP09 — Rubrica de causa-raiz

Cada critério recebe 0, 1 ou 2 pontos:

1. **Causa-raiz correta** — 2 se aponta a reindexação travada como causa que satura o heap e leva ao circuit breaker, timeouts e queda do cache; 1 se chega perto mas mistura causa e sintoma; 0 se aponta apenas sintomas ou outra causa.
2. **Correlação × causa** — 2 se separa explicitamente causa de consequência (por exemplo, cache hit baixo como efeito); 1 se separa parcialmente; 0 se trata tudo como causal.
3. **Ação proporcional** — 2 se recomenda contenção/reagendamento da reindexação e revisão de heap/limites de forma proporcional; 1 se é plausível mas incompleta; 0 se é imprudente ou desproporcional.
4. **Honestidade epistêmica** — 2 se marca incertezas e não afirma o que os dados não sustentam; 1 se há alguma ressalva; 0 se fabrica certeza.

Pontuação total: 0–8. O gate exige **total >= 6 e nenhum critério com 0**.
