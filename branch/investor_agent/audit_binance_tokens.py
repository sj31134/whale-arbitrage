binance_tokens = [
    ("RKLBUSDT", "Rocket Lab USA", 64.79, 4.00, 16.2, 32.5),
    ("ASTSUSDT", "AST SpaceMobile", 58.21, 2.20, 26.5, 16.2),
    ("IRENUSDT", "IREN (Iris Energy)", 35.75, 3.20, 11.2, 7.1),
    ("PLTRUSDT", "Palantir Technologies", 185.74, 6.00, 30.9, 420.0),
    ("ARMUSDT", "Arm Holdings", 239.32, 50.00, 4.8, 250.0),
    ("ASMLUSDT", "ASML Holding", 1705.00, 400.00, 4.3, 680.0),
    ("TSMUSDT", "TSMC", 419.17, 70.00, 6.0, 1100.0),
    ("NVDAUSDT", "NVIDIA Corporation", 218.16, 15.00, 14.5, 3400.0),
    ("TSLAUSDT", "Tesla Inc.", 349.48, 20.00, 17.5, 1100.0),
    ("COINUSDT", "Coinbase Global", 178.48, 35.00, 5.1, 45.0),
    ("MSTRUSDT", "MicroStrategy", 127.81, 14.00, 9.1, 28.0),
    ("PAXGUSDT", "PAX Gold", 4459.89, 1800.00, 2.5, 1.2),
    ("ONDOUSDT", "Ondo Finance", 0.35, 0.08, 4.4, 0.5)
]

print("=" * 110)
print("🔍 SUBAGENT 7대 텐배거 '발굴' 원칙 기준 바이낸스 토큰화 주식 정밀 감사 (Self-Auditing Verification)")
print("=" * 110)

passed = []
failed = []

for sym, name, p, low, mult, mcap in binance_tokens:
    # 7대 텐배거 발굴 원칙 기준:
    # 1. $4~$25 구간의 초기 잠복기 (Pre-Inflection)
    # 2. 바닥 대비 아직 10배 폭등하지 않은 상태 (Remaining upside >= 5x~10x)
    # 3. 시총 $50B 미만의 비대칭 폭발력
    is_pre_inflection = p <= 25.0
    is_not_already_multi_bagger = mult < 5.0
    is_not_mega_cap = mcap < 30.0

    if is_pre_inflection and is_not_already_multi_bagger and is_not_mega_cap:
        passed.append((sym, name, p, mult, mcap))
        verdict = "✅ [합격: 초기 텐배거 원석]"
    else:
        failed.append((sym, name, p, mult, mcap))
        if mult >= 10.0:
            verdict = f"❌ [탈락: 이미 {mult:.1f}배 폭등 완료된 '기(旣) 텐배거']"
        elif mcap >= 50.0:
            verdict = f"❌ [탈락: 시총 ${mcap:.0f}B의 거대 '메가캡']"
        else:
            verdict = f"❌ [탈락: 주가 ${p:.2f} 과열 및 텐배거 잠재력 미달]"
            
    print(f"{sym:10s} | {name:22s} | 현재가: ${p:7.2f} | 바닥대비: {mult:4.1f}배 | 시총: ${mcap:6.1f}B | {verdict}")

print("\n" + "=" * 110)
print(f"📊 최종 판정: 검토 대상 13개 중 합격(진짜 초기 텐배거): {len(passed)}개 | 탈락(기 텐배거/메가캡): {len(failed)}개")
print("=" * 110)
