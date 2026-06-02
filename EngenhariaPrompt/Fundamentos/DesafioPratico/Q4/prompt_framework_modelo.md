#TASK (O que fazer)
Jennifer precisa de um relatório mensal de transações consolidadas do Ledger (PostgreSQL) para apresentar crescimento dos últimos 6 meses por categoria. O relatório será entregue em formato estruturado (mês, categoria, quantidade de transações, volume total).
Contexto do banco:

Tabela transactions: id, customer_id, category, amount_cents, status, payment_method, created_at, completed_at
Tabela customers: id, segment, country, signup_at
Categorias válidas: subscription, one_time, refund, credit_adjustment
Apenas transações com status = 'completed' entram no relatório
amount_cents está em centavos (dividir por 100 para obter reais)
Data de corte: hoje é 2026-04-24

# ACTION (Como fazer)
Gere uma query SQL PostgreSQL que:

Filtre o período: últimos 6 meses corridos a partir de 2026-04-24 (2024-10-24 até 2026-04-24 inclusive)
Filtre os dados válidos: apenas transações com status = 'completed' e categorias válidas
Agrupe os dados: por mês (formato YYYY-MM derivado de created_at) e categoria
Calcule as métricas:

Quantidade de transações (COUNT)
Volume total em reais (SUM de amount_cents / 100.0, com 2 casas decimais)


Ordene o resultado: mês em ordem crescente (antiga → recente), depois categoria em ordem crescente (alfabética)

# GOAL (Resultado esperado)
Output esperado:
Uma query SQL que retorna uma tabela com estrutura:
mês            | categoria            | quantidade_transacoes | volume_reais
---------------|----------------------|-----------------------|---------------
2025-10        | credit_adjustment    | 142                   | 1245.67
2025-10        | one_time             | 587                   | 12450.34
2025-10        | refund               | 23                    | -234.56
2025-10        | subscription         | 1204                  | 24567.89
2025-11        | credit_adjustment    | 156                   | 1456.78
...
2026-04        | subscription         | 1420                  | 28900.45
Validações:

Primeiras linhas começam com 2025-10
Últimas linhas terminam com 2026-04
Exatamente 6 meses (24 linhas: 6 meses × 4 categorias, assumindo dados completos)
Nenhuma categoria fora da lista: subscription, one_time, refund, credit_adjustment
Volume sempre com 2 casas decimais
Ordenação verificável: mês crescente → categoria alfabética dentro de cada mês
Use índices existentes (created_at, status, category) para otimização
Nomes de coluna no resultado devem ser descritivos: mês, categoria, quantidade_transacoes, volume_reais
Volume em reais com exatamente 2 casas decimais
