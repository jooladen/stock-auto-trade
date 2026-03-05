import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from strategy.base import BacktestResult, OrderSide

logger = logging.getLogger("stock-auto-trade")


class BacktestReport:
    """백테스트 성과 분석 리포트."""

    def __init__(self, result: BacktestResult, initial_capital: float) -> None:
        self.result = result
        self.initial_capital = initial_capital

    def summary(self) -> dict:
        """핵심 성과 지표를 딕셔너리로 반환."""
        return {
            "총 수익률 (%)": f"{self.result.total_return:.2f}",
            "승률 (%)": f"{self.result.win_rate:.2f}",
            "최대 낙폭 MDD (%)": f"{self.result.max_drawdown:.2f}",
            "샤프 비율": f"{self.result.sharpe_ratio:.2f}",
            "총 거래 횟수": self.result.total_trades,
            "수익 거래": self.result.winning_trades,
            "손실 거래": self.result.losing_trades,
            "거래당 평균 수익률 (%)": f"{self.result.avg_profit_per_trade:.2f}",
        }

    def print_report(self) -> None:
        """CLI에 성과 리포트를 출력한다."""
        print("\n" + "=" * 50)
        print("        백테스트 성과 리포트")
        print("=" * 50)

        for key, value in self.summary().items():
            print(f"  {key}: {value}")

        print("=" * 50)

        if self.result.total_return > 0:
            print(f"  결과: 수익 (+{self.result.total_return:.2f}%)")
        else:
            print(f"  결과: 손실 ({self.result.total_return:.2f}%)")

        print(f"  초기 자본: {self.initial_capital:,.0f}원")
        final = self.initial_capital * (1 + self.result.total_return / 100)
        print(f"  최종 자산: {final:,.0f}원")
        print(f"  순이익: {final - self.initial_capital:,.0f}원")
        print("=" * 50 + "\n")

    def _get_equity(self) -> list[float]:
        """일별 자산 곡선을 반환한다."""
        if self.result.equity_curve:
            return self.result.equity_curve
        return [self.initial_capital]

    def plot_equity_curve(self, save_path: str | None = None) -> None:
        """자산 곡선 차트를 생성한다."""
        equity = self._get_equity()
        if len(equity) <= 1:
            logger.warning("자산 곡선 데이터가 없어 차트를 생성할 수 없습니다.")
            return

        plt.figure(figsize=(12, 6))
        plt.plot(equity, linewidth=1.5)
        plt.title("자산 곡선 (Equity Curve)")
        plt.xlabel("거래일")
        plt.ylabel("자산 (원)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150)
            logger.info("자산 곡선 저장: %s", save_path)
        else:
            plt.show()

        plt.close()

    def plot_drawdown(self, save_path: str | None = None) -> None:
        """낙폭 차트를 생성한다."""
        equity = self._get_equity()
        if len(equity) <= 1:
            logger.warning("자산 곡선 데이터가 없어 차트를 생성할 수 없습니다.")
            return

        equity_arr = np.array(equity)
        peak = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - peak) / peak * 100

        plt.figure(figsize=(12, 4))
        plt.fill_between(range(len(drawdown)), drawdown, 0, alpha=0.3, color="red")
        plt.plot(drawdown, color="red", linewidth=1)
        plt.title("낙폭 (Drawdown)")
        plt.xlabel("거래일")
        plt.ylabel("낙폭 (%)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150)
            logger.info("낙폭 차트 저장: %s", save_path)
        else:
            plt.show()

        plt.close()

    def export_trades_csv(self, path: str) -> None:
        """거래 내역을 CSV로 내보낸다."""
        if not self.result.trades:
            logger.warning("거래 내역이 없습니다.")
            return

        rows = []
        for trade in self.result.trades:
            rows.append({
                "시간": trade.timestamp,
                "종목": trade.ticker,
                "구분": "매수" if trade.side == OrderSide.BUY else "매도",
                "가격": trade.price,
                "수량": trade.quantity,
                "금액": trade.price * trade.quantity,
                "매도사유": trade.sell_reason or "",
            })

        df = pd.DataFrame(rows)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info("거래 내역 저장: %s (%d건)", path, len(rows))
