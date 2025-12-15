"""
Streamlit Cloud 진단 유틸

목표:
- Cloud에서 로그 메뉴를 못 보더라도, 앱 UI에서 원인(데이터 소스/폴백/패키지 설치 상태)을 확인할 수 있게 함
- Secrets 값은 절대 노출하지 않고, 존재 여부/버전/최신 날짜 같은 안전한 정보만 표시
"""

from __future__ import annotations

import os
import sys
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class Diagnostics:
    env_is_streamlit_cloud: bool
    python_version: str
    platform: str
    use_supabase: bool
    db_path: str
    db_exists: bool
    secrets: dict[str, bool]
    pkg_versions: dict[str, Optional[str]]
    sqlite_max_dates: dict[str, Optional[str]]
    supabase_max_dates: dict[str, Optional[str]]
    supabase_rpc_common_range: dict[str, Optional[str]]
    errors: list[str]


def _safe_pkg_version(dist_name: str) -> Optional[str]:
    try:
        from importlib.metadata import version
        return version(dist_name)
    except Exception:
        return None


def _sqlite_max_date(db_path: str, sql: str, params: tuple[Any, ...] = ()) -> Optional[str]:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql, params)
        val = cur.fetchone()[0]
        conn.close()
        return val
    except Exception:
        return None


def collect_diagnostics(data_loader, coin: str = "BTC") -> Diagnostics:
    # DataLoader 타입에 의존하지 않도록 duck-typing으로 접근
    env_is_streamlit_cloud = os.path.exists("/mount/src")
    errors: list[str] = []

    # Secrets 존재 여부만 확인 (값은 절대 노출 금지)
    secrets_presence = {
        "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
        "SUPABASE_KEY": bool(os.getenv("SUPABASE_KEY")) or bool(os.getenv("SUPABASE_ANON_KEY")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
    }

    # Streamlit secrets도 고려 (있으면 presence만 true)
    try:
        import streamlit as st
        for k in list(secrets_presence.keys()):
            if hasattr(st, "secrets") and k in st.secrets:
                secrets_presence[k] = True
    except Exception:
        pass

    # 패키지 버전(설치 여부) 확인: Cloud 모델 에러 원인 파악용
    pkg_versions = {
        "streamlit": _safe_pkg_version("streamlit"),
        "pandas": _safe_pkg_version("pandas"),
        "numpy": _safe_pkg_version("numpy"),
        "supabase": _safe_pkg_version("supabase"),
        "xgboost": _safe_pkg_version("xgboost"),
        "lightgbm": _safe_pkg_version("lightgbm"),
        "tensorflow": _safe_pkg_version("tensorflow"),
        "scikit-learn": _safe_pkg_version("scikit-learn"),
    }

    # SQLite 최신일(폴백 스냅샷이 최신인지 확인)
    sqlite_max_dates: dict[str, Optional[str]] = {}
    supabase_max_dates: dict[str, Optional[str]] = {}
    supabase_rpc_common_range: dict[str, Optional[str]] = {"min_date": None, "max_date": None}

    market = "KRW-BTC" if coin == "BTC" else "KRW-ETH"
    symbol = "BTCUSDT" if coin == "BTC" else "ETHUSDT"

    db_path = getattr(data_loader, "_db_path", None) or str(getattr(data_loader, "db_path", ""))
    db_exists = bool(db_path) and Path(db_path).exists()

    if db_exists and db_path:
        sqlite_max_dates["upbit_daily"] = _sqlite_max_date(
            db_path,
            "SELECT MAX(date) FROM upbit_daily WHERE market=?",
            (market,),
        )
        sqlite_max_dates["binance_spot_daily"] = _sqlite_max_date(
            db_path,
            "SELECT MAX(date) FROM binance_spot_daily WHERE symbol=?",
            (symbol,),
        )
        sqlite_max_dates["exchange_rate"] = _sqlite_max_date(
            db_path,
            "SELECT MAX(date) FROM exchange_rate",
        )

    # Supabase 최신일 + RPC 동작 여부 확인(anon key 설정/권한 문제를 UI에서 보이게)
    try:
        if getattr(data_loader, "use_supabase", False):
            sp = data_loader._get_supabase_client()
            if sp:
                try:
                    r = sp.table("upbit_daily").select("date").eq("market", market).order("date", desc=True).limit(1).execute()
                    supabase_max_dates["upbit_daily"] = r.data[0]["date"] if r.data else None
                except Exception as e:
                    errors.append(f"supabase upbit_daily max_date 실패: {e}")
                try:
                    r = sp.table("binance_spot_daily").select("date").eq("symbol", symbol).order("date", desc=True).limit(1).execute()
                    supabase_max_dates["binance_spot_daily"] = r.data[0]["date"] if r.data else None
                except Exception as e:
                    errors.append(f"supabase binance_spot_daily max_date 실패: {e}")
                try:
                    r = sp.table("exchange_rate").select("date").order("date", desc=True).limit(1).execute()
                    supabase_max_dates["exchange_rate"] = r.data[0]["date"] if r.data else None
                except Exception as e:
                    errors.append(f"supabase exchange_rate max_date 실패: {e}")

                # RPC
                try:
                    rpc = sp.rpc("get_common_date_range", {"p_market": market, "p_symbol": symbol}).execute()
                    if rpc.data:
                        supabase_rpc_common_range["min_date"] = rpc.data[0].get("min_date")
                        supabase_rpc_common_range["max_date"] = rpc.data[0].get("max_date")
                except Exception as e:
                    errors.append(f"supabase RPC(get_common_date_range) 실패: {e}")
    except Exception as e:
        errors.append(f"supabase 진단 중 예외: {e}")

    return Diagnostics(
        env_is_streamlit_cloud=env_is_streamlit_cloud,
        python_version=sys.version,
        platform=sys.platform,
        use_supabase=bool(getattr(data_loader, "use_supabase", False)),
        db_path=str(db_path),
        db_exists=db_exists,
        secrets=secrets_presence,
        pkg_versions=pkg_versions,
        sqlite_max_dates=sqlite_max_dates,
        supabase_max_dates=supabase_max_dates,
        supabase_rpc_common_range=supabase_rpc_common_range,
        errors=errors,
    )


def to_dict(d: Diagnostics) -> dict[str, Any]:
    return asdict(d)


