"""
설정 관리 클래스
UI에서 입력받은 설정을 안전하게 저장/로드하는 기능 제공
"""

import json
import os
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SettingsManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        초기화
        
        Args:
            config_path: 설정 파일 경로 (None이면 기본 경로 사용)
        """
        if config_path is None:
            # 기본 경로: trading_bot/config/user_settings.json
            base_dir = Path(__file__).resolve().parent
            config_path = base_dir / "user_settings.json"
        
        self.config_path = Path(config_path)
        self.default_config_path = Path(__file__).parent / "default_config.json"
        
        # 설정 파일 디렉토리 생성
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_settings(self) -> Dict:
        """
        설정 로드
        
        Returns:
            설정 딕셔너리 (기본값과 사용자 설정 병합)
        """
        try:
            # 기본 설정 로드
            default_settings = self.get_default_settings()
            
            # 사용자 설정 파일이 있으면 로드
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                
                # 기본 설정과 병합 (사용자 설정 우선)
                merged_settings = self._merge_settings(default_settings, user_settings)
                logger.info(f"설정 로드 완료: {self.config_path}")
                return merged_settings
            else:
                logger.info("사용자 설정 파일이 없습니다. 기본 설정을 사용합니다.")
                return default_settings
                
        except Exception as e:
            logger.error(f"설정 로드 실패: {e}")
            # 에러 발생 시 기본 설정 반환
            return self.get_default_settings()
    
    def save_settings(self, settings: Dict) -> bool:
        """
        설정 저장
        
        Args:
            settings: 저장할 설정 딕셔너리
        
        Returns:
            저장 성공 여부
        """
        try:
            # 설정 검증
            is_valid, error_msg = self.validate_settings(settings)
            if not is_valid:
                logger.error(f"설정 검증 실패: {error_msg}")
                return False
            
            # 설정 저장
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            # 파일 권한 설정 (소유자만 읽기/쓰기)
            os.chmod(self.config_path, 0o600)
            
            logger.info(f"설정 저장 완료: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            return False
    
    def validate_settings(self, settings: Dict) -> Tuple[bool, str]:
        """
        설정 검증
        
        Args:
            settings: 검증할 설정 딕셔너리
        
        Returns:
            (검증 성공 여부, 에러 메시지)
        """
        try:
            # 필수 필드 확인
            required_fields = [
                'api',
                'trading',
                'strategy'
            ]
            
            for field in required_fields:
                if field not in settings:
                    return False, f"필수 필드 누락: {field}"
            
            # API 키 형식 검증 (비어있어도 되지만, 있으면 형식 확인)
            if 'api' in settings:
                api = settings['api']
                if api.get('upbit_access_key') and len(api.get('upbit_access_key', '')) < 10:
                    return False, "업비트 Access Key 형식이 올바르지 않습니다."
                if api.get('upbit_secret_key') and len(api.get('upbit_secret_key', '')) < 10:
                    return False, "업비트 Secret Key 형식이 올바르지 않습니다."
            
            # 거래 설정 검증
            if 'trading' in settings:
                trading = settings['trading']
                if trading.get('initial_capital', 0) < 0:
                    return False, "초기 자본금은 0 이상이어야 합니다."
                if not 0 < trading.get('max_position_size', 0) <= 1:
                    return False, "최대 포지션 비율은 0과 1 사이여야 합니다."
                if not -1 < trading.get('stop_loss_pct', 0) < 0:
                    return False, "손절매 비율은 음수여야 합니다."
                if trading.get('take_profit_pct', 0) <= 0:
                    return False, "익절 비율은 양수여야 합니다."
            
            return True, ""
            
        except Exception as e:
            return False, f"설정 검증 중 오류: {str(e)}"
    
    def get_default_settings(self) -> Dict:
        """
        기본 설정 반환
        
        Returns:
            기본 설정 딕셔너리
        """
        try:
            if self.default_config_path.exists():
                with open(self.default_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning("기본 설정 파일을 찾을 수 없습니다. 빈 설정을 반환합니다.")
                return {}
        except Exception as e:
            logger.error(f"기본 설정 로드 실패: {e}")
            return {}
    
    def _merge_settings(self, default: Dict, user: Dict) -> Dict:
        """
        기본 설정과 사용자 설정 병합
        
        Args:
            default: 기본 설정
            user: 사용자 설정
        
        Returns:
            병합된 설정
        """
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # 중첩된 딕셔너리는 재귀적으로 병합
                merged[key] = self._merge_settings(merged[key], value)
            else:
                # 사용자 설정으로 덮어쓰기
                merged[key] = value
        
        return merged
    
    def get_config_path(self) -> Path:
        """설정 파일 경로 반환"""
        return self.config_path
    
    def config_exists(self) -> bool:
        """설정 파일 존재 여부 확인"""
        return self.config_path.exists()

