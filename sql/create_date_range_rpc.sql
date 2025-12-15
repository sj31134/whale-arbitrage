-- Supabase RPC: get_common_date_range
-- Streamlit Cloud에서 row limit 없이 정확한 교집합 날짜 범위를 구하기 위한 함수

CREATE OR REPLACE FUNCTION get_common_date_range(
    p_market TEXT, 
    p_symbol TEXT
)
RETURNS TABLE (
    min_date DATE, 
    max_date DATE,
    count_dates BIGINT
) 
LANGUAGE plpgsql
SECURITY DEFINER -- 함수 생성자의 권한으로 실행 (anon key로도 접근 가능하게 함)
AS $$
BEGIN
    RETURN QUERY
    WITH upbit_dates AS (
        SELECT date FROM upbit_daily WHERE market = p_market
    ),
    binance_dates AS (
        SELECT date FROM binance_spot_daily WHERE symbol = p_symbol
    ),
    ex_dates AS (
        SELECT date FROM exchange_rate
    ),
    common_dates AS (
        SELECT date FROM upbit_dates
        INTERSECT
        SELECT date FROM binance_dates
        INTERSECT
        SELECT date FROM ex_dates
    )
    SELECT 
        MIN(date) as min_date,
        MAX(date) as max_date,
        COUNT(*) as count_dates
    FROM common_dates;
END;
$$;

-- 권한 설정: anon 키(공개 접근) 및 authenticated 역할에 실행 권한 부여
GRANT EXECUTE ON FUNCTION get_common_date_range(TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION get_common_date_range(TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_common_date_range(TEXT, TEXT) TO service_role;

