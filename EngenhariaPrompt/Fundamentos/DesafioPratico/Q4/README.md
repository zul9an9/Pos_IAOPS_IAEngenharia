Por que essa query atende ao GOAL:

✅ Filtra últimos 6 meses corridos (2024-10-24 a 2026-04-24 inclusive)
✅ Apenas status = 'completed'
✅ Agrupa por mês (YYYY-MM) e categoria
✅ Calcula COUNT e SUM/100 com 2 casas decimais
✅ Ordena mês ASC, depois categoria ASC
✅ Usa índices (created_at, status, category)
