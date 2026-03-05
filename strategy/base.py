from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from config import StrategyConfig


class OrderSide:
    BUY = "buy"
    SELL = "sell"


class SellReason:
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    SIGNAL = "signal"


@dataclass
class Signal:
    """매매 신호."""

    ticker: str
    side: str  # OrderSide.BUY or OrderSide.SELL
    price: float
    reason: str


@dataclass
class Trade:
    """체결된 거래."""

    ticker: str
    side: str
    price: float
    quantity: int
    timestamp: datetime
    reason: str | None = None
    sell_reason: str | None = None


@dataclass
class Position:
    """보유 포지션."""

    ticker: str
    buy_price: float
    quantity: int
    buy_date: date


@dataclass
class BacktestResult:
    """백테스트 결과."""

    trades: list[Trade]
    total_return: float  # 총 수익률 (%)
    win_rate: float  # 승률 (%)
    max_drawdown: float  # 최대 낙폭 (%)
    sharpe_ratio: float  # 샤프 비율
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit_per_trade: float  # 거래당 평균 수익률
    equity_curve: list[float] | None = None  # 일별 자산 곡선


class BaseStrategy(ABC):
    """매매 전략 추상 클래스."""

    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        """주가 데이터로부터 매수 신호 생성."""

    @abstractmethod
    def check_exit(self, position: Position, current_price: float) -> Signal | None:
        """보유 포지션의 청산 조건 확인 (익절/손절)."""
