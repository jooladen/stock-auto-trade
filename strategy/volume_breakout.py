import pandas as pd

from config import StrategyConfig
from strategy.base import BaseStrategy, OrderSide, Position, SellReason, Signal


class VolumeBreakoutStrategy(BaseStrategy):
    """거래량 급등 + 추세 추종 전략.

    매수 조건:
      1. 오늘 거래량 > 5일 평균 거래량 × volume_multiplier
      2. 오늘 종가 > 전일 종가

    매도 조건:
      - 익절: 매수가 대비 +take_profit_pct 이상
      - 손절: 매수가 대비 -stop_loss_pct 이하
    """

    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config)

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        """주가 데이터의 마지막 날짜에서 매수 신호를 확인한다.

        엔진이 날짜별로 호출하므로, 마지막 행(오늘)만 판단한다.

        Args:
            df: 일봉 데이터 (columns: Open, High, Low, Close, Volume)
            ticker: 종목 코드

        Returns:
            매수 신호 리스트 (최대 1개)
        """
        if len(df) < self.config.volume_lookback_days + 1:
            return []

        # 5일 평균 거래량 계산 (마지막 행 기준)
        recent = df.iloc[-(self.config.volume_lookback_days + 1) :]
        vol_avg = recent["Volume"].iloc[:-1].mean()
        today = recent.iloc[-1]
        prev_close = recent["Close"].iloc[-2]

        # 조건 1: 거래량 급등
        volume_surge = today["Volume"] > vol_avg * self.config.volume_multiplier

        # 조건 2: 종가 상승
        price_up = today["Close"] > prev_close

        if volume_surge and price_up:
            return [
                Signal(
                    ticker=ticker,
                    side=OrderSide.BUY,
                    price=today["Close"],
                    reason=f"거래량 급등({int(today['Volume']):,} > 평균 {int(vol_avg):,}), 종가 상승",
                )
            ]

        return []

    def check_exit(self, position: Position, current_price: float) -> Signal | None:
        """보유 포지션의 익절/손절 조건 확인.

        Args:
            position: 보유 포지션
            current_price: 현재 가격

        Returns:
            매도 신호 (조건 충족 시) 또는 None
        """
        profit_pct = (current_price - position.buy_price) / position.buy_price

        # 익절
        if profit_pct >= self.config.take_profit_pct:
            return Signal(
                ticker=position.ticker,
                side=OrderSide.SELL,
                price=current_price,
                reason=f"익절 ({profit_pct:.2%} >= {self.config.take_profit_pct:.2%})",
            )

        # 손절
        if profit_pct <= -self.config.stop_loss_pct:
            return Signal(
                ticker=position.ticker,
                side=OrderSide.SELL,
                price=current_price,
                reason=f"손절 ({profit_pct:.2%} <= -{self.config.stop_loss_pct:.2%})",
            )

        return None
