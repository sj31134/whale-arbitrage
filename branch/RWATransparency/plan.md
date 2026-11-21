# RWATransparency: 6-Week Execution Roadmap

## 📅 Week 1–2: 데이터 파이프라인 구축 (Data Pipeline) ✅ COMPLETED
- [x] **분석 대상 확정**: 주요 RWA 토큰(Ondo, BUIDL, Mountain 등) 리스트업 완료.
- [x] **Layer 1 (On-chain)**: CoinGecko API 연동(가격/거래량) 수집기 구현 완료.
- [x] **Layer 2 (Off-chain)**: 오프체인 리포트 크롤링 템플릿 구현 완료.
- [x] **통합 DB 설계**: 자산별-일자별 패널 데이터 스키마 구축 완료.

## 📅 Week 3: TDT 점수 산출 (TDT Score Calculation) ✅ COMPLETED
- [x] **지표 정량화**:
    - Update Latency: 공시 주기 스코어링 구현.
    - Completeness: 필수 필드 누락률 계산 구현.
    - Consistency: 온/오프체인 발행량 불일치율 계산 구현.
- [x] **TDT 생성**: 가중치 기반(동일 가중치) TDT 점수 산출 완료.

## 📅 Week 4: 계량 분석 (Econometric Analysis) ✅ COMPLETED
- [x] **패널 회귀 (Panel Regression)**: TDT가 유동성(Amihud) 및 변동성에 미치는 영향 검정 완료.
- [x] **상호작용 효과 (H3)**: 거시 충격(Shock)과 TDT의 상호작용항 분석 완료.
- [x] **통제변수 결합**: 시총(log), BTC 변동성 데이터 병합 완료.

## 📅 Week 5: 추가 고도화 (Advanced Modeling) ✅ COMPLETED
- [ ] **이벤트 스터디**: 감사 보고서 업데이트 전후의 시장 반응 차이 분석. (추후 진행)
- [x] **ML 리스크 예측**: Gradient Boosting 기반 급락 예측 모델 구현 완료 (AUC=0.88).
- [x] **설명가능성**: Permutation Importance 기반 TDT 구성 요소 중요도 분석 완료.
- [x] **강건성 분석**: 클러스터 SE, BH 보정, 서브샘플 분석 완료 (Petersen 2009 방법론).
- [x] **RWA 전용 분석**: 순수 RWA 토큰에서 TDT → 변동성 감소 효과 확인 (p<0.001).

## 📅 Week 6: 시나리오 완성 및 정리 (Reporting) ✅ COMPLETED
- [x] **대시보드 구현**: Streamlit 기반 RWA 리스크 스코어 카드 완료 (http://localhost:8501).
- [x] **논문/결과 보고서 정리**: 핵심 도표(Regression Table, TDT Distribution) 생성 완료.
- [x] **README 업데이트**: 프로젝트 구조, 실행 방법, 연구 결과 문서화.
- [ ] **이직용 포트폴리오 최적화**: 거래소/VC 관점의 리스크 관리 프레임워크 요약. (추후)
