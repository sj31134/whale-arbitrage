# 프로젝트 구조 가이드

> **정리 완료일**: 2025-01-XX  
> 프로젝트 파일들을 논리적으로 분류하여 구조화했습니다.

## 📁 디렉토리 구조

```
whale_tracking/
├── config/              # 설정 파일 (.env 등)
├── data/                # 데이터 파일
│   ├── richlist/        # Rich List CSV 파일들
│   └── exports/         # Excel 등 내보낸 파일들
├── docs/                # 문서
│   ├── analysis/        # 분석 관련 문서
│   └── guides/          # 가이드 문서
├── logs/                # 로그 파일
├── scripts/             # Python 스크립트
│   ├── collectors/      # Supabase 기반 수집 스크립트
│   ├── analysis/        # 데이터 분석 스크립트
│   ├── utils/           # 유틸리티/검증 스크립트
│   ├── tests/           # 테스트 스크립트
│   ├── maintenance/     # 유지보수/업데이트 스크립트
│   ├── main/            # 메인 실행 스크립트
│   └── subprojects/     # Arbitrage & Risk AI 서브 프로젝트
├── sql/                 # SQL 파일
│   └── migrations/      # 마이그레이션 SQL
├── src/                 # 소스 코드 모듈
│   ├── collectors/      # 수집 모듈
│   ├── database/        # 데이터베이스 모듈
│   └── utils/           # 유틸리티 모듈
├── temp/                # 임시 파일
└── tests/               # 테스트 코드
```

## 📝 주요 스크립트 위치

### 데이터 수집
- `scripts/collectors/` - 모든 수집 스크립트 (collect_*.py)

### 데이터 분석
- `scripts/analysis/` - 분석 스크립트 (analyze_*.py)

### 유틸리티/검증
- `scripts/utils/` - 확인/검증 스크립트 (check_*, verify_*, inspect_*.py)

### 테스트
- `scripts/tests/` - 테스트 스크립트 (test_*.py)

### 유지보수
- `scripts/maintenance/` - 업데이트/수정 스크립트 (update_*, fix_*, add_*.py)

### 메인 실행
- `scripts/main/` - 실행 스크립트 (run_*.py, main.py)

## 🔄 스크립트 실행 방법

### 데이터 수집
```bash
python3 scripts/collectors/collect_btc_whale_transactions.py
python3 scripts/main/run_parallel_collection.py
```

### 데이터 분석
```bash
python3 scripts/analysis/analyze_top_picks.py
```

### 유틸리티
```bash
python3 scripts/utils/check_label_progress.py
python3 scripts/utils/verify_transaction_direction.py
```

### 유지보수
```bash
python3 scripts/maintenance/update_direction_direct.py
python3 scripts/maintenance/update_labels_stable.py
```

