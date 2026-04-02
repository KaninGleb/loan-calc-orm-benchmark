-- =============================================================================
-- ДЛЯ ТЕСТОВ
-- =============================================================================

-- INSERT INTO loan_applications (monthly_payment, annual_rate, loan_term_years)
-- VALUES 
-- (500, 10, 15),
-- (1000, 12, 20),
-- (750, 8.5, 10),
-- (750, 12.5, 15),
-- (500, 0, 8),
-- (500, 0, 5),
-- (600, 10.00, 15),
-- (400, 10.00, 15);

-- SELECT * FROM calculate_loan_limits_bulk();
-- SELECT * FROM loan_applications;


-- =============================================================================
-- 1. ТОП-5 САМЫХ ВЫГОДНЫХ КРЕДИТОВ
-- Ранжируем рассчитанные заявки по чистой прибыли банка.
-- =============================================================================

SELECT
	id,
	annual_rate,
	monthly_payment,
	total_interest_amount,
	ROW_NUMBER() OVER (ORDER BY total_interest_amount DESC) AS interest_rank
FROM loan_applications
WHERE total_interest_amount IS NOT NULL
LIMIT 5;


-- =============================================================================
-- 2. НАКОПИТЕЛЬНЫЙ ИТОГ
-- Считаем, как растет общая сумма ежемесячных платежей с каждой новой заявкой.
-- =============================================================================

SELECT
	id,
	monthly_payment,
	SUM(monthly_payment) OVER (ORDER BY id) AS cumulative_payment
FROM loan_applications;


-- =============================================================================
-- 3. АНАЛИТИКА ОТКЛОНЕНИЙ ПО ГРУППАМ РИСКА
-- Разбиваем заявки на 3 группы риска по годовому проценту.
-- Сравниваем платеж конкретного клиента со средним платежом по его группе.
-- =============================================================================

SELECT
    id,
    annual_rate,
    monthly_payment,
    risk_tier,
    ROUND(
		AVG(monthly_payment) OVER (PARTITION BY risk_tier), 2
	) AS avg_payment_by_risk_tier,
    ROUND(
		monthly_payment - AVG(monthly_payment) OVER (PARTITION BY risk_tier), 2
	) AS diff_from_avg
FROM (
    SELECT *,
        CASE
            WHEN annual_rate < 10 THEN 'low'
            WHEN annual_rate < 13 THEN 'medium'
            ELSE 'high'
        END AS risk_tier
    FROM loan_applications
) AS risk_buckets;








