"""전략 단위 테스트."""

from datetime import date

import pandas as pd
import pytest

from config import StrategyConfig
from strategy.base import OrderSide, Position
from strategy.volume_breakout import VolumeBreakoutStrategy


@pytest.fixture
def config() -> StrategyConfig:
    return StrategyConfig(
        volume_multiplier=2.0,
        volume_lookback_days=5,
        take_profit_pct=0.03,
        stop_loss_pct=0.02,
    )


@pytest.fixture
def strategy(config: StrategyConfig) -> VolumeBreakoutStrategy:
    return VolumeBreakoutStrategy(config)


def _make_df(volumes: list[int], closes: list[float]) -> pd.DataFrame:
    """테스트용 DataFrame 생성."""
    dates = pd.date_range("2025-01-01", periods=len(volumes), freq="B")
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c * 1.02 for c in closes],
            "Low": [c * 0.98 for c in closes],
            "Close": closes,
            "Volume": volumes,
        },
        index=dates,
    )


class TestVolumeBreakoutStrategy:
    """거래량 급등 전략 테스트."""

    def test_buy_signal_on_volume_surge_and_price_up(
        self, strategy: VolumeBreakoutStrategy
    ) -> None:
        """거래량 급등 + 종가 상승 시 매수 신호 생성."""
        # 5일 평균 거래량 = 100,000, 마지막 날 거래량 = 300,000 (3배)
        volumes = [100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 300_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600]
        df = _make_df(volumes, closes)

        signals = strategy.generate_signals(df, "005930")

        assert len(signals) > 0
        assert signals[-1].side == OrderSide.BUY

    def test_no_signal_when_volume_low(
        self, strategy: VolumeBreakoutStrategy
    ) -> None:
        """거래량이 낮으면 매수 신호 없음."""
        volumes = [100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 100_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600]
        df = _make_df(volumes, closes)

        signals = strategy.generate_signals(df, "005930")

        assert len(signals) == 0

    def test_no_signal_when_price_down(
        self, strategy: VolumeBreakoutStrategy
    ) -> None:
        """거래량 급등이지만 종가 하락 시 매수 신호 없음."""
        volumes = [100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 300_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_400]
        df = _make_df(volumes, closes)

        signals = strategy.generate_signals(df, "005930")

        # 마지막 날은 종가가 하락했으므로 신호 없어야 함
        buy_signals_last_day = [
            s for s in signals if s.price == 10_400 and s.side == OrderSide.BUY
        ]
        assert len(buy_signals_last_day) == 0

    def test_take_profit(self, strategy: VolumeBreakoutStrategy) -> None:
        """익절 조건 도달 시 매도 신호 생성."""
        position = Position(
            ticker="005930",
            buy_price=10_000,
            quantity=10,
            buy_date=date(2025, 1, 1),
        )

        # +3% = 10,300
        exit_signal = strategy.check_exit(position, 10_300)

        assert exit_signal is not None
        assert exit_signal.side == OrderSide.SELL
        assert "익절" in exit_signal.reason

    def test_stop_loss(self, strategy: VolumeBreakoutStrategy) -> None:
        """손절 조건 도달 시 매도 신호 생성."""
        position = Position(
            ticker="005930",
            buy_price=10_000,
            quantity=10,
            buy_date=date(2025, 1, 1),
        )

        # -2% = 9,800
        exit_signal = strategy.check_exit(position, 9_800)

        assert exit_signal is not None
        assert exit_signal.side == OrderSide.SELL
        assert "손절" in exit_signal.reason

    def test_no_exit_within_range(self, strategy: VolumeBreakoutStrategy) -> None:
        """익절/손절 범위 안이면 매도 신호 없음."""
        position = Position(
            ticker="005930",
            buy_price=10_000,
            quantity=10,
            buy_date=date(2025, 1, 1),
        )

        # +1% = 범위 내
        exit_signal = strategy.check_exit(position, 10_100)

        assert exit_signal is None

    def test_insufficient_data(self, strategy: VolumeBreakoutStrategy) -> None:
        """데이터 부족 시 빈 신호 리스트 반환."""
        volumes = [100_000, 100_000]
        closes = [10_000, 10_100]
        df = _make_df(volumes, closes)

        signals = strategy.generate_signals(df, "005930")

        assert len(signals) == 0

    def test_only_returns_signal_for_last_date(
        self, strategy: VolumeBreakoutStrategy
    ) -> None:
        """중간에 급등이 있어도 마지막 날짜가 조건 미충족이면 신호 0개."""
        # 20일 데이터: 7일째에 급등이 있지만, 마지막 날은 평범한 거래량
        volumes = (
            [100_000] * 6
            + [300_000]  # 7일째 급등
            + [100_000] * 13  # 이후 평범
        )
        closes = [10_000 + i * 50 for i in range(20)]
        df = _make_df(volumes, closes)

        signals = strategy.generate_signals(df, "005930")

        assert len(signals) == 0, "마지막 날이 조건 미충족이면 신호가 없어야 함"

    def test_returns_signal_when_last_date_qualifies(
        self, strategy: VolumeBreakoutStrategy
    ) -> None:
        """마지막 날짜가 조건 충족 시 신호 1개."""
        # 20일 데이터: 마지막 날에 급등 + 종가 상승
        volumes = [100_000] * 19 + [300_000]
        closes = [10_000 + i * 50 for i in range(20)]
        df = _make_df(volumes, closes)

        signals = strategy.generate_signals(df, "005930")

        assert len(signals) == 1, "마지막 날이 조건 충족이면 신호 1개"
        assert signals[0].side == OrderSide.BUY

    def test_max_one_signal_per_call(
        self, strategy: VolumeBreakoutStrategy
    ) -> None:
        """어떤 입력이든 반환 신호는 최대 1개."""
        # 모든 날이 급등 조건을 만족하는 극단적 데이터
        volumes = [100_000] * 5 + [300_000] * 15
        closes = [10_000 + i * 100 for i in range(20)]
        df = _make_df(volumes, closes)

        signals = strategy.generate_signals(df, "005930")

        assert len(signals) <= 1, "generate_signals는 최대 1개 신호만 반환해야 함"
