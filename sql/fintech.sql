DROP TABLE IF EXISTS loan_applications CASCADE;

-- =============================================================================
-- Физическая таблица кредитных заявок.
-- Ограничения защищают БД от некорректных данных, 
-- даже если приложение пришлет несоответствующие данные.
-- =============================================================================

CREATE TABLE loan_applications (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    monthly_payment NUMERIC(20, 2) NOT NULL
		CONSTRAINT chk_monthly_payment_positive CHECK (monthly_payment > 0),
		
    annual_rate NUMERIC(5, 2) NOT NULL
		CONSTRAINT chk_annual_rate_range CHECK (annual_rate >= 0 AND annual_rate <= 150),
		
    loan_term_years INT NOT NULL
		CONSTRAINT chk_loan_term_years_range CHECK (loan_term_years > 0 AND loan_term_years <= 100),
    
    calculated_loan_limit NUMERIC(20, 2),
    total_repayment_amount NUMERIC(20, 2),
    total_interest_amount NUMERIC(20, 2),
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);


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

-- SELECT * FROM loan_applications;

-- UPDATE loan_applications 
-- SET 
-- calculated_loan_limit = NULL, 
-- total_repayment_amount = NULL, 
-- total_interest_amount = NULL;

-- SELECT * FROM loan_applications;

-- TRUNCATE TABLE loan_applications;


-- =============================================================================
-- ПОСТРОЧНЫЙ РАСЧЕТ (Итеративный подход)
-- Имитация логики приложения внутри базы.
-- Перебираем нерассчитанные заявки в цикле и обновляем 
-- каждую отдельным запросом.
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_loan_limits_row_by_row()
RETURNS VOID AS $$
DECLARE
	current_application RECORD;
	monthly_interest_rate NUMERIC;
    loan_term_months INT;
    calculated_limit NUMERIC;
    calculated_repayment NUMERIC;
    calculated_interest NUMERIC;
BEGIN
	FOR current_application IN
		SELECT id, monthly_payment, annual_rate, loan_term_years
		FROM loan_applications
		WHERE calculated_loan_limit IS NULL
	LOOP
		monthly_interest_rate := current_application.annual_rate / 100 / 12;
		loan_term_months := current_application.loan_term_years * 12;

		IF monthly_interest_rate = 0 THEN
			calculated_limit := current_application.monthly_payment * loan_term_months;
		ELSE
			calculated_limit := current_application.monthly_payment * 
				(1 - ((1 + monthly_interest_rate) ^ (-loan_term_months))) / monthly_interest_rate;
		END IF;

		calculated_repayment := current_application.monthly_payment * loan_term_months;
		calculated_interest := calculated_repayment - calculated_limit;

		UPDATE loan_applications
		SET calculated_loan_limit = ROUND(calculated_limit, 2),
    		total_repayment_amount = ROUND(calculated_repayment, 2),
    		total_interest_amount = ROUND(calculated_interest, 2),
			calculated_at = NOW()
		WHERE id = current_application.id;
	END LOOP;
END;
$$ LANGUAGE plpgsql;


SELECT calculate_loan_limits_row_by_row();
SELECT * FROM loan_applications;


-- =============================================================================
-- МАССОВЫЙ РАСЧЕТ (Декларативный подход)
-- Создаем временную виртуальную таблицу,
-- производим все расчёты в памяти базы, а затем записываем результаты 
-- в физическую таблицу одним массовым UPDATE.
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_loan_limits_bulk()
RETURNS TABLE (
    processed_count INT,
    execution_time INTERVAL
) AS $$
DECLARE
    v_start_time TIMESTAMPTZ;
    v_processed_rows_count INT := 0;
BEGIN
	v_start_time := clock_timestamp();
	
	WITH calc AS (
        SELECT 
            id,
            monthly_payment,
            loan_term_years,
            annual_rate,
            monthly_payment * loan_term_years * 12 AS total_repayment_amount,
            CASE
                WHEN annual_rate = 0 THEN monthly_payment * loan_term_years * 12
                ELSE monthly_payment * 
                    (1 - (1 + (annual_rate / 100 / 12)) ^ -(loan_term_years * 12)) / (annual_rate / 100 / 12)
            END AS calculated_limit
        FROM loan_applications
        WHERE calculated_loan_limit IS NULL
    )
    UPDATE loan_applications l
    SET 
        calculated_loan_limit = ROUND(c.calculated_limit, 2),
        total_repayment_amount = ROUND(c.total_repayment_amount, 2),
        total_interest_amount = ROUND(c.total_repayment_amount - c.calculated_limit, 2),
        calculated_at = NOW()
    FROM calc c
    WHERE l.id = c.id;

	GET DIAGNOSTICS v_processed_rows_count = ROW_COUNT;

	RETURN QUERY SELECT v_processed_rows_count, clock_timestamp() - v_start_time;
END;
$$ LANGUAGE plpgsql;


SELECT * FROM calculate_loan_limits_bulk();
SELECT * FROM loan_applications;


-- =============================================================================
-- ЧТЕНИЕ: Виртуальная таблица с расчётами.
-- Чистый SELECT. Ничего не меняет в БД.
-- Извлекаем нерассчитанные заявки и считаем для них лимиты и выплаты. 
-- =============================================================================

CREATE OR REPLACE VIEW v_calculate_loan_limits AS
WITH loan_limits_calc AS (
    SELECT 
        id,
        monthly_payment,
        loan_term_years,
        annual_rate,
        monthly_payment * loan_term_years * 12 AS total_repayment_amount,
        CASE
            WHEN annual_rate = 0 THEN monthly_payment * loan_term_years * 12
            ELSE monthly_payment * 
                (1 - (1 + (annual_rate / 100 / 12)) ^ -(loan_term_years * 12)) / (annual_rate / 100 / 12)
        END AS calculated_limit
    FROM loan_applications
    WHERE calculated_loan_limit IS NULL
)
SELECT 
    id,
    monthly_payment,
    loan_term_years,
    annual_rate,
    total_repayment_amount,
    calculated_limit,
    total_repayment_amount - calculated_limit AS total_interest_amount
FROM loan_limits_calc;

SELECT * FROM v_calculate_loan_limits;


-- =============================================================================
-- ЗАПИСЬ: Сохранение расчётов в физическую таблицу.
-- Чистый UPDATE. Берёт данные из VIEW и обновляет физические строки.
-- Возвращает статистику: сколько записей обновлено и за какое время.
-- =============================================================================

CREATE OR REPLACE FUNCTION update_loan_limits()
RETURNS TABLE (
    processed_count INT,
    execution_time INTERVAL
) AS $$
DECLARE
    v_start_time TIMESTAMPTZ;
    v_processed_rows_count INT := 0;
BEGIN
    v_start_time := clock_timestamp();

    UPDATE loan_applications l
    SET 
        calculated_loan_limit = ROUND(c.calculated_limit, 2),
        total_repayment_amount = ROUND(c.total_repayment_amount, 2),
        total_interest_amount = ROUND(c.total_interest_amount, 2),
        calculated_at = NOW()
    FROM v_calculate_loan_limits c
    WHERE l.id = c.id;

    GET DIAGNOSTICS v_processed_rows_count = ROW_COUNT;

    RETURN QUERY SELECT v_processed_rows_count, clock_timestamp() - v_start_time;
END;
$$ LANGUAGE plpgsql;


SELECT * FROM update_loan_limits();
SELECT * FROM loan_applications;






