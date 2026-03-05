from dataclasses import dataclass


@dataclass
class StrategyConfig:
    """전략 파라미터 설정."""

    # 매수 조건
    volume_multiplier: float = 2.0  # 거래량 배수 (5일 평균 대비)
    volume_lookback_days: int = 5  # 거래량 비교 기간

    # 매도 조건
    take_profit_pct: float = 0.03  # 익절 비율 (3%)
    stop_loss_pct: float = 0.02  # 손절 비율 (2%)

    # 리스크 관리
    max_daily_trades: int = 2  # 하루 최대 진입 횟수
    max_positions: int = 5  # 동시 보유 종목 수
    position_size_pct: float = 0.2  # 종목당 투자 비중 (20%)

    # 백테스트
    initial_capital: float = 10_000_000  # 초기 자본금 (1천만원)
    commission_rate: float = 0.00015  # 수수료율 (0.015%)
    slippage_pct: float = 0.001  # 슬리피지 (0.1%)
