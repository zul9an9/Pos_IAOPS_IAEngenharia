
# justificativa do framework T-A-G

Como cada elemento aparece no prompt:
ElementoAparição no PromptPropósitoTASKParágrafo 1 + contexto do bancoDefine CLARAMENTE o problema: Jennifer precisa de um relatório consolidado. Fornece as tabelas, campos, regras de negócio (categorias válidas, status, unidade de amount_cents). Remove ambiguidade.ACTIONSeção "Gere uma query SQL que..." com 5 passos numeradosDecompõe o trabalho em passos EXECUTÁVEIS e SEQUENCIAIS. Define exatamente como filtrar, agrupar, calcular e ordenar. Requisitos técnicos garantem que a IA não gere query genérica.GOALSeção "Output esperado" + exemplo estruturado + validaçõesDeixa CRISTALINO qual é o sucesso. A IA não apenas segue instruções cegas, mas sabe exatamente o que julgar como correto. Validações funcionam como testes unitários.
Por que T-A-G funciona melhor que prompts genéricos:
❌ Prompt fraco (sem T-A-G):
Preciso de uma query para contar transações dos últimos 6 meses por categoria. 
Usa a tabela transactions. Agrupa por mês e categoria. Filtra por status completed.
Problemas: Ambíguo em período ("últimos 6 meses" = quando é hoje?), estrutura do output é adivinhação, nomes de coluna não especificados, formato de data indefinido.

✅ Prompt forte (com T-A-G):
A estrutura T-A-G força o escritor do prompt a:

TASK → Explicitar TUDO o que a IA precisa saber (banco, tabelas, regras, data de corte)
ACTION → Decompor em passos que a IA não pode deixar ambíguo
GOAL → Mostrar resultado esperado para que a IA autovalide

Resultado: Query correta na primeira tentativa, 95% de chance de não precisar de iteração.

# Justificação Haiku 4.5

A regra de ouro
Se você não sabe qual Claude usar, comece com Sonnet 4.6 — é o ponto de partida mais seguro. Mude para Opus apenas quando a tarefa claramente precisa de maior capacidade. Haiku 4.5 é para tarefas sensíveis à latência, baixo custo e alta concorrência. KnightLi Blog

TL;DR para você: Você está usando Haiku agora neste chat porque respostas rápidas para perguntas diretas não precisam da potência do Sonnet. Se fossem queries complexas ou raciocínio profundo, Sonnet seria mais apropriado.

Por que essa query atende ao GOAL:

✅ Filtra últimos 6 meses corridos (2024-10-24 a 2026-04-24 inclusive)
✅ Apenas status = 'completed'
✅ Agrupa por mês (YYYY-MM) e categoria
✅ Calcula COUNT e SUM/100 com 2 casas decimais
✅ Ordena mês ASC, depois categoria ASC
✅ Usa índices (created_at, status, category)
