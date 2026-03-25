DROP TABLE IF EXISTS loans;

CREATE TABLE loans (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    monthly_payment NUMERIC(20, 2) NOT NULL
		CONSTRAINT chk_monthly_payment_positive CHECK (monthly_payment > 0),
		
    annual_rate NUMERIC(5, 2) NOT NULL
		CONSTRAINT chk_annual_rate_range CHECK (annual_rate >= 0 AND annual_rate <= 150),
		
    years INT NOT NULL
		CONSTRAINT chk_years_range CHECK (years > 0 AND years <= 100),
    
    max_loan_amount NUMERIC(20, 2),
    total_payment NUMERIC(20, 2),
    total_interest NUMERIC(20, 2),
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

---------------------------------------------------------
-- For testing
-- INSERT INTO loans (monthly_payment, annual_rate, years)
-- VALUES 
-- (500, 10, 15),
-- (1000, 12, 20),
-- (750, 8.5, 10),
-- (750, 12.5, 15),
-- (500, 0, 5);


-- SELECT * FROM loans;

-- TRUNCATE TABLE loans; 

-- UPDATE loans SET max_loan_amount = NULL, total_payment = NULL, total_interest = NULL;

---------------------------------------------------------
-- #1 - Slow calculations
CREATE OR REPLACE FUNCTION slow_calculate_all_loans()
RETURNS VOID AS $$
DECLARE
	loan_record RECORD;
	monthly_rate NUMERIC;
    total_months INT;
    max_amount NUMERIC;
    total_payment_calc NUMERIC;
    total_interest_calc NUMERIC;
BEGIN
	FOR loan_record IN
		SELECT id, monthly_payment, annual_rate, years
		FROM loans
		WHERE max_loan_amount IS NULL
	LOOP
		monthly_rate := loan_record.annual_rate / 100 / 12;
		total_months := loan_record.years * 12;

		IF monthly_rate = 0 THEN
			max_amount := loan_record.monthly_payment * total_months;
		ELSE
			max_amount := loan_record.monthly_payment * 
				(1 - ((1 + monthly_rate) ^ (-total_months))) / monthly_rate;
		END IF;
			
		total_payment_calc := loan_record.monthly_payment * total_months;
		total_interest_calc := total_payment_calc - max_amount;

		UPDATE loans
		SET max_loan_amount = ROUND(max_amount, 2),
    		total_payment = ROUND(total_payment_calc, 2),
    		total_interest = ROUND(total_interest_calc, 2),
			calculated_at = NOW()
		WHERE id = loan_record.id;
	END LOOP;
END;
$$ LANGUAGE plpgsql;


-- SELECT slow_calculate_all_loans();
-- SELECT * FROM loans;


---------------------------------------------------------
-- #2 - Fast calculations
CREATE OR REPLACE FUNCTION calculate_all_loans()
RETURNS TABLE (
    processed_count INT,
    execution_time INTERVAL
) AS $$
DECLARE
    v_start_time TIMESTAMPTZ;
    v_processed INT := 0;
BEGIN
	v_start_time := clock_timestamp();
	
	WITH calc AS (
        SELECT 
            id,
            monthly_payment,
            years,
            annual_rate,
            monthly_payment * years * 12 AS total_payment,
            CASE
                WHEN annual_rate = 0 THEN monthly_payment * years * 12
                ELSE monthly_payment * 
                    (1 - (1 + (annual_rate / 100 / 12)) ^ -(years * 12)) / (annual_rate / 100 / 12)
            END AS max_amount
        FROM loans
        WHERE 
		max_loan_amount IS NULL
    )
    UPDATE loans l
    SET 
        max_loan_amount = ROUND(c.max_amount, 2),
        total_payment = ROUND(c.total_payment, 2),
        total_interest = ROUND(c.total_payment - c.max_amount, 2),
        calculated_at = NOW()
    FROM calc c
    WHERE l.id = c.id;

	GET DIAGNOSTICS v_processed = ROW_COUNT;

	RETURN QUERY SELECT v_processed, clock_timestamp() - v_start_time;
END;
$$ LANGUAGE plpgsql;


-- SELECT * FROM calculate_all_loans();
-- SELECT * FROM loans;






