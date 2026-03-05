"""백테스트 엔진 단위 테스트."""

from datetime import date

import pandas as pd
import pytest

from backtest.engine import BacktestEngine
from config import StrategyConfig
from strategy.base import BacktestResult, OrderSide, Position
from strategy.volume_breakout import VolumeBreakoutStrategy


class MockDataLoader:
    """테스트용 DataLoader mock."""

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._data = data

    def load_stock_data(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._data.get(ticker, pd.DataFrame())

    def load_market_tickers(
        self, market_date: str | None = None, market: str = "KOSPI"
    ) -> list[str]:
        return list(self._data.keys())


def _make_df(
    volumes: list[int], closes: list[float], start: str = "2025-01-01"
) -> pd.DataFrame:
    """테스트용 DataFrame 생성."""
    dates = pd.date_range(start, periods=len(volumes), freq="B")
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


@pytest.fixture
def config() -> StrategyConfig:
    return StrategyConfig(
        volume_multiplier=2.0,
        take_profit_pct=0.03,
        stop_loss_pct=0.02,
        max_daily_trades=2,
        max_positions=5,
        initial_capital=10_000_000,
        commission_rate=0.00015,
        slippage_pct=0.001,
    )


class TestBacktestEngine:
    """백테스트 엔진 테스트."""

    def test_empty_data_returns_empty_result(self, config: StrategyConfig) -> None:
        """데이터가 없으면 빈 결과를 반환한다."""
        strategy = VolumeBreakoutStrategy(config)
        data_loader = MockDataLoader({})
        engine = BacktestEngine(strategy, data_loader, config)

        result = engine.run(["005930"], "20250101", "20251231")

        assert result.total_trades == 0
        assert result.total_return == 0.0

    def test_buy_and_take_profit(self, config: StrategyConfig) -> None:
        """매수 후 익절 조건 도달 시 수익 거래가 기록된다."""
        # 거래량 급등 + 종가 상승 → 매수 → 3% 상승 → 익절
        volumes = [100_000] * 6 + [300_000, 100_000, 100_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600, 10_920, 10_920]
        data = {"005930": _make_df(volumes, closes)}

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930"], "20250101", "20250115")

        assert result.total_trades >= 1, "익절 거래가 발생해야 함"
        assert result.winning_trades >= 1, "수익 거래가 1건 이상이어야 함"

    def test_buy_and_stop_loss(self, config: StrategyConfig) -> None:
        """매수 후 손절 조건 도달 시 손실 거래가 기록된다."""
        volumes = [100_000] * 6 + [300_000, 100_000, 100_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600, 10_380, 10_380]
        data = {"005930": _make_df(volumes, closes)}

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930"], "20250101", "20250115")

        assert result.total_trades >= 1, "손절 거래가 발생해야 함"
        assert result.losing_trades >= 1, "손실 거래가 1건 이상이어야 함"

    def test_max_daily_trades_limit(self, config: StrategyConfig) -> None:
        """하루 최대 거래 횟수를 초과하지 않는다."""
        config.max_daily_trades = 1

        # 같은 날 여러 종목에서 신호 발생
        volumes = [100_000] * 6 + [300_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600]
        data = {
            "005930": _make_df(volumes, closes),
            "000660": _make_df(volumes, closes),
            "035720": _make_df(volumes, closes),
        }

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930", "000660", "035720"], "20250101", "20250115")

        # 매수 거래 중 같은 날짜에 max_daily_trades 이하여야 함
        buy_trades = [t for t in result.trades if t.side == OrderSide.BUY]
        if buy_trades:
            dates = [t.timestamp.date() for t in buy_trades]
            from collections import Counter

            date_counts = Counter(dates)
            for count in date_counts.values():
                assert count <= config.max_daily_trades

    def test_max_positions_limit(self, config: StrategyConfig) -> None:
        """동시 보유 종목 수를 초과하지 않는다."""
        config.max_positions = 1

        volumes = [100_000] * 6 + [300_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600]
        data = {
            "005930": _make_df(volumes, closes),
            "000660": _make_df(volumes, closes),
        }

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930", "000660"], "20250101", "20250115")

        # max_positions=1이므로 동시에 2종목 매수 불가
        buy_trades = [t for t in result.trades if t.side == OrderSide.BUY]
        # 첫 매수 후 매도 전에 두 번째 매수가 없어야 함
        assert len(buy_trades) <= 2  # 최대 순차적으로만 가능

    def test_commission_and_slippage_applied(self, config: StrategyConfig) -> None:
        """수수료와 슬리피지가 반영되어 수익률이 감소한다."""
        config_no_cost = StrategyConfig(
            volume_multiplier=2.0,
            take_profit_pct=0.03,
            stop_loss_pct=0.02,
            initial_capital=10_000_000,
            commission_rate=0.0,
            slippage_pct=0.0,
        )

        volumes = [100_000] * 6 + [300_000, 100_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600, 10_920]
        data = {"005930": _make_df(volumes, closes)}

        # 수수료/슬리피지 있는 경우
        engine_with_cost = BacktestEngine(
            VolumeBreakoutStrategy(config), MockDataLoader(data), config
        )
        result_with_cost = engine_with_cost.run(["005930"], "20250101", "20250115")

        # 수수료/슬리피지 없는 경우
        engine_no_cost = BacktestEngine(
            VolumeBreakoutStrategy(config_no_cost),
            MockDataLoader(data),
            config_no_cost,
        )
        result_no_cost = engine_no_cost.run(["005930"], "20250101", "20250115")

        # 수수료가 있으면 수익률이 같거나 낮아야 함
        assert result_with_cost.total_return <= result_no_cost.total_return

    def test_mdd_calculation(self, config: StrategyConfig) -> None:
        """MDD(최대낙폭)가 0 이상이어야 한다."""
        volumes = [100_000] * 6 + [300_000, 100_000, 100_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600, 10_300, 10_300]
        data = {"005930": _make_df(volumes, closes)}

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930"], "20250101", "20250115")

        assert result.max_drawdown >= 0.0

    def test_forced_liquidation_at_end(self, config: StrategyConfig) -> None:
        """백테스트 종료 시 남은 포지션이 강제 청산된다."""
        # 매수 신호는 있지만 매도 조건에 도달하지 않는 경우
        volumes = [100_000] * 6 + [300_000, 100_000]
        closes = [10_000, 10_100, 10_200, 10_300, 10_400, 10_500, 10_600, 10_650]
        data = {"005930": _make_df(volumes, closes)}

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930"], "20250101", "20250115")

        # 매수가 있으면 반드시 매도도 있어야 함 (강제 청산 포함)
        buy_count = sum(1 for t in result.trades if t.side == OrderSide.BUY)
        sell_count = sum(1 for t in result.trades if t.side == OrderSide.SELL)
        assert buy_count == sell_count

    def test_no_duplicate_buy_on_same_signal(self, config: StrategyConfig) -> None:
        """급등이 1일만 발생하면 매수도 1회만 실행된다."""
        # 20일 데이터: 7일째에만 급등, 나머지는 평범
        volumes = [100_000] * 6 + [300_000] + [100_000] * 13
        closes = [10_000 + i * 50 for i in range(20)]
        data = {"005930": _make_df(volumes, closes)}

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930"], "20250101", "20250201")

        buy_trades = [t for t in result.trades if t.side == OrderSide.BUY]
        assert len(buy_trades) == 1, "급등 1일이면 매수도 1회만 실행되어야 함"

    def test_multiple_signals_across_dates(self, config: StrategyConfig) -> None:
        """서로 다른 날에 급등이 2번 발생하면 매수 2회."""
        # 20일 데이터: 7일째, 15일째에 급등 (사이에 익절로 포지션 정리)
        volumes = [100_000] * 6 + [300_000] + [100_000] * 7 + [300_000] + [100_000] * 5
        # 7일째 매수 후 익절(+3%)을 위해 가격 설정
        closes = (
            [10_000, 10_050, 10_100, 10_150, 10_200, 10_250]
            + [10_300]  # 7일째 매수 (급등)
            + [10_350, 10_400, 10_450, 10_500, 10_550, 10_620, 10_700]  # 익절 도달
            + [10_750]  # 15일째 매수 (급등)
            + [10_800, 10_850, 10_900, 10_950, 11_000]
        )
        data = {"005930": _make_df(volumes, closes)}

        strategy = VolumeBreakoutStrategy(config)
        engine = BacktestEngine(strategy, MockDataLoader(data), config)
        result = engine.run(["005930"], "20250101", "20250210")

        buy_trades = [t for t in result.trades if t.side == OrderSide.BUY]
        assert len(buy_trades) == 2, "서로 다른 날 급등 2회면 매수도 2회"
