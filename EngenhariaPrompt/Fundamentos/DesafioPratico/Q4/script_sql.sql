SELECT
    TO_CHAR(DATE_TRUNC('month', t.created_at), 'YYYY-MM') AS mês,
    t.category AS categoria,
    COUNT(*) AS quantidade_transacoes,
    TO_CHAR(SUM(t.amount_cents) / 100.0, 'FM9999999.00') AS volume_reais
FROM
    transactions t
WHERE
    t.status = 'completed'
    AND t.category IN ('subscription', 'one_time', 'refund', 'credit_adjustment')
    AND t.created_at >= '2024-10-24'::TIMESTAMPTZ
    AND t.created_at < '2026-04-25'::TIMESTAMPTZ
GROUP BY
    DATE_TRUNC('month', t.created_at),
    t.category
ORDER BY
    mês ASC,
    categoria ASC;
