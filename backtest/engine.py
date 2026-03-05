import logging
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

from backtest.data_loader import DataLoader
from config import StrategyConfig
from strategy.base import (
    BacktestResult,
    BaseStrategy,
    OrderSide,
    Position,
    SellReason,
    Trade,
)

logger = logging.getLogger("stock-auto-trade")


class BacktestEngine:
    """백테스트 시뮬레이션 엔진."""

    def __init__(
        self,
        strategy: BaseStrategy,
        data_loader: DataLoader,
        config: StrategyConfig,
    ) -> None:
        self.strategy = strategy
        self.data_loader = data_loader
        self.config = config

    def run(
        self,
        tickers: list[str],
        start_date: str,
        end_date: str,
    ) -> BacktestResult:
        """백테스트를 실행한다.

        Args:
            tickers: 대상 종목 코드 리스트
            start_date: 시작일 (예: "20250101")
            end_date: 종료일 (예: "20251231")

        Returns:
            백테스트 결과
        """
        capital = self.config.initial_capital
        positions: dict[str, Position] = {}
        trades: list[Trade] = []
        equity_curve: list[float] = [capital]

        # 종목별 데이터 로드
        stock_data: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            df = self.data_loader.load_stock_data(ticker, start_date, end_date)
            if not df.empty:
                stock_data[ticker] = df

        if not stock_data:
            logger.warning("유효한 데이터가 없습니다.")
            return self._empty_result()

        # 전체 거래일 목록 (모든 종목의 날짜 합집합)
        all_dates = sorted(
            set().union(*(df.index.tolist() for df in stock_data.values()))
        )

        logger.info(
            "백테스트 시작: %d 종목, %s ~ %s (%d 거래일)",
            len(stock_data),
            start_date,
            end_date,
            len(all_dates),
        )

        daily_trade_count: dict[str, int] = defaultdict(int)

        for current_date in all_dates:
            date_str = current_date.strftime("%Y%m%d") if hasattr(current_date, "strftime") else str(current_date)

            # 1) 보유 포지션 청산 체크
            positions_to_close: list[str] = []
            for ticker, position in positions.items():
                if ticker not in stock_data:
                    continue
                df = stock_data[ticker]
                if current_date not in df.index:
                    continue

                current_price = df.loc[current_date, "Close"]
                exit_signal = self.strategy.check_exit(position, current_price)

                if exit_signal is not None:
                    sell_price = self._apply_slippage(current_price, OrderSide.SELL)
                    sell_price = self._apply_commission(sell_price, OrderSide.SELL)

                    trade = Trade(
                        ticker=ticker,
                        side=OrderSide.SELL,
                        price=sell_price,
                        quantity=position.quantity,
                        timestamp=datetime.combine(current_date, datetime.min.time())
                        if hasattr(current_date, "year")
                        else datetime.now(),
                        reason=exit_signal.reason,
                        sell_reason=exit_signal.reason,
                    )
                    trades.append(trade)

                    capital += sell_price * position.quantity
                    positions_to_close.append(ticker)

                    logger.info(
                        "[매도] %s | 가격: %s | 수량: %d | 사유: %s",
                        ticker,
                        f"{sell_price:,.0f}",
                        position.quantity,
                        exit_signal.reason,
                    )

            for ticker in positions_to_close:
                del positions[ticker]

            # 2) 매수 신호 체크
            for ticker, df in stock_data.items():
                if ticker in positions:
                    continue
                if current_date not in df.index:
                    continue
                if len(positions) >= self.config.max_positions:
                    break
                if daily_trade_count[date_str] >= self.config.max_daily_trades:
                    break

                signals = self.strategy.generate_signals(
                    df.loc[:current_date], ticker
                )

                if not signals:
                    continue

                # 마지막 신호만 사용 (오늘 날짜의 신호)
                last_signal = signals[-1]
                buy_price = self._apply_slippage(last_signal.price, OrderSide.BUY)
                buy_price = self._apply_commission(buy_price, OrderSide.BUY)

                # 투자 금액 계산
                invest_amount = capital * self.config.position_size_pct
                quantity = int(invest_amount / buy_price)

                if quantity <= 0:
                    continue

                cost = buy_price * quantity
                if cost > capital:
                    continue

                capital -= cost
                positions[ticker] = Position(
                    ticker=ticker,
                    buy_price=buy_price,
                    quantity=quantity,
                    buy_date=current_date,
                )

                trades.append(
                    Trade(
                        ticker=ticker,
                        side=OrderSide.BUY,
                        price=buy_price,
                        quantity=quantity,
                        timestamp=datetime.combine(current_date, datetime.min.time())
                        if hasattr(current_date, "year")
                        else datetime.now(),
                        reason=last_signal.reason,
                    )
                )

                daily_trade_count[date_str] += 1

                logger.info(
                    "[매수] %s | 가격: %s | 수량: %d | 사유: %s",
                    ticker,
                    f"{buy_price:,.0f}",
                    quantity,
                    last_signal.reason,
                )

            # 3) 일일 자산 평가
            portfolio_value = capital
            for ticker, position in positions.items():
                if ticker in stock_data and current_date in stock_data[ticker].index:
                    portfolio_value += (
                        stock_data[ticker].loc[current_date, "Close"] * position.quantity
                    )
            equity_curve.append(portfolio_value)

        # 남은 포지션 강제 청산 (백테스트 종료)
        for ticker, position in positions.items():
            if ticker in stock_data:
                df = stock_data[ticker]
                last_price = df.iloc[-1]["Close"]
                capital += last_price * position.quantity
                trades.append(
                    Trade(
                        ticker=ticker,
                        side=OrderSide.SELL,
                        price=last_price,
                        quantity=position.quantity,
                        timestamp=datetime.now(),
                        reason="백테스트 종료 강제 청산",
                        sell_reason="백테스트 종료 강제 청산",
                    )
                )

        return self._calculate_result(trades, equity_curve)

    def _apply_slippage(self, price: float, side: str) -> float:
        """슬리피지 적용."""
        if side == OrderSide.BUY:
            return price * (1 + self.config.slippage_pct)
        return price * (1 - self.config.slippage_pct)

    def _apply_commission(self, price: float, side: str) -> float:
        """수수료 적용."""
        if side == OrderSide.BUY:
            return price * (1 + self.config.commission_rate)
        return price * (1 - self.config.commission_rate)

    def _calculate_result(
        self, trades: list[Trade], equity_curve: list[float]
    ) -> BacktestResult:
        """거래 내역으로 성과 지표를 계산한다."""
        if not trades:
            return self._empty_result()

        # 매수-매도 페어 매칭으로 수익률 계산
        buy_trades: dict[str, list[Trade]] = defaultdict(list)
        profits: list[float] = []

        for trade in trades:
            if trade.side == OrderSide.BUY:
                buy_trades[trade.ticker].append(trade)
            elif trade.side == OrderSide.SELL and buy_trades[trade.ticker]:
                buy_trade = buy_trades[trade.ticker].pop(0)
                profit_pct = (trade.price - buy_trade.price) / buy_trade.price
                profits.append(profit_pct)

        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p <= 0]

        # MDD 계산
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(float(np.min(drawdown))) if len(drawdown) > 0 else 0.0

        # 샤프 비율 (일간 수익률 기준, 연환산)
        if len(equity_curve) > 1:
            daily_returns = np.diff(equity_curve) / equity_curve[:-1]
            sharpe = (
                float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252))
                if np.std(daily_returns) > 0
                else 0.0
            )
        else:
            sharpe = 0.0

        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100

        return BacktestResult(
            trades=trades,
            total_return=total_return,
            win_rate=len(winning) / len(profits) * 100 if profits else 0.0,
            max_drawdown=max_drawdown * 100,
            sharpe_ratio=sharpe,
            total_trades=len(profits),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_profit_per_trade=float(np.mean(profits) * 100) if profits else 0.0,
            equity_curve=equity_curve,
        )

    def _empty_result(self) -> BacktestResult:
        """빈 결과 반환."""
        return BacktestResult(
            trades=[],
            total_return=0.0,
            win_rate=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_profit_per_trade=0.0,
            equity_curve=[],
        )
