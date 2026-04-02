DROP TABLE IF EXISTS client_profiles;

-- =============================================================================
-- Физическая таблица с неструктурированными данными профиля в формате JSONB.
-- Используем JSONB для хранения динамических параметров клиента,
-- чтобы не плодить пустые колонки в таблице.
-- =============================================================================

CREATE TABLE client_profiles (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profile_data JSONB NOT NULL,
	
    CONSTRAINT chk_required_fields
        CHECK (profile_data ?& ARRAY['name', 'age', 'city']),
		
	CONSTRAINT chk_types
        CHECK (
            jsonb_typeof(profile_data->'name') = 'string' AND
            jsonb_typeof(profile_data->'age') = 'number' AND
            jsonb_typeof(profile_data->'city') = 'string'
        )
);


-- =============================================================================
-- ДЛЯ ТЕСТОВ
-- =============================================================================

-- INSERT INTO client_profiles (profile_data) VALUES
-- ('{"name": "Gleb Kanin", "age": 23, "city": "Minsk", "device": "mobile"}'),
-- ('{"name": "Ivan Ivanov", "age": 35, "city": "Grodno", "has_car": true}');

-- SELECT * FROM client_profiles;


-- =============================================================================
-- Извлекаю данные из JSONB.
-- =============================================================================

SELECT
    id,
    profile_data->>'name' AS client_name,
    profile_data->>'city' AS client_city
FROM client_profiles;

-- =============================================================================
-- Фильтрую данные внутри JSONB.
-- =============================================================================

SELECT *
FROM client_profiles
WHERE profile_data @> '{"has_car": true}';




