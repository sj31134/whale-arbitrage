# 🚀 Supabase 초고속 라벨 업데이트 가이드

이 가이드는 `whale_transactions` 테이블의 라벨(`from_label`, `to_label`)을 `whale_address` 테이블 정보를 바탕으로 1~2분 내에 일괄 업데이트하는 방법을 설명합니다.

## 1단계: SQL Editor 접속
1. **Supabase Dashboard** 접속 (https://supabase.com/dashboard)
2. 해당 프로젝트 선택
3. 좌측 메뉴에서 **SQL Editor** 클릭
4. **New query** 클릭

## 2단계: RPC 함수 생성 및 실행
아래 SQL 코드를 복사하여 SQL Editor에 붙여넣고 **Run** 버튼을 클릭하세요.

```sql
-- ============================================
-- 초고속 라벨 업데이트를 위한 RPC 함수
-- ============================================

-- 1. 함수 생성
CREATE OR REPLACE FUNCTION update_whale_labels_fast()
RETURNS TABLE(
    updated_from BIGINT,
    updated_to BIGINT
) AS $$
DECLARE
    from_count BIGINT;
    to_count BIGINT;
BEGIN
    -- 타임아웃을 10분으로 설정 (대량 업데이트를 위해)
    SET statement_timeout = '600s';

    -- 1. from_label 일괄 업데이트
    UPDATE whale_transactions wt
    SET from_label = wa.name_tag,
        updated_at = NOW()
    FROM whale_address wa
    WHERE LOWER(wt.from_address) = LOWER(wa.address)
      AND wt.from_label IS NULL
      AND wa.name_tag IS NOT NULL;
      
    GET DIAGNOSTICS from_count = ROW_COUNT;
    RAISE NOTICE 'from_label 업데이트: % 건', from_count;

    -- 2. to_label 일괄 업데이트
    UPDATE whale_transactions wt
    SET to_label = wa.name_tag,
        updated_at = NOW()
    FROM whale_address wa
    WHERE LOWER(wt.to_address) = LOWER(wa.address)
      AND wt.to_label IS NULL
      AND wa.name_tag IS NOT NULL;
      
    GET DIAGNOSTICS to_count = ROW_COUNT;
    RAISE NOTICE 'to_label 업데이트: % 건', to_count;

    -- 결과 반환
    RETURN QUERY SELECT from_count, to_count;
END;
$$ LANGUAGE plpgsql;

-- 2. 함수 실행
SELECT * FROM update_whale_labels_fast();
```

## 3단계: 결과 확인
쿼리 실행이 완료되면 결과창에 업데이트된 `from_label` 수와 `to_label` 수가 표시됩니다.
- `updated_from`: 송신 주소 라벨 업데이트 건수
- `updated_to`: 수신 주소 라벨 업데이트 건수

## 4단계: 검증 (선택 사항)
터미널에서 다음 명령어를 실행하여 전체 진행률을 확인할 수 있습니다.
```bash
python3 scripts/check_label_progress.py
```

