"""주식 자동매매 시스템 - 백테스트 CLI."""

import argparse
import logging

from backtest.data_loader import DataLoader
from backtest.engine import BacktestEngine
from backtest.report import BacktestReport
from config import StrategyConfig
from strategy.volume_breakout import VolumeBreakoutStrategy
from utils.logger import setup_logger

logger = logging.getLogger("stock-auto-trade")


def run_backtest(args: argparse.Namespace) -> None:
    """백테스트를 실행한다."""
    config = StrategyConfig(
        volume_multiplier=args.volume_mult,
        take_profit_pct=args.take_profit / 100,
        stop_loss_pct=args.stop_loss / 100,
        initial_capital=args.capital,
        max_daily_trades=args.max_trades,
    )

    strategy = VolumeBreakoutStrategy(config)
    data_loader = DataLoader()
    engine = BacktestEngine(strategy, data_loader, config)

    # 종목 리스트 결정
    if args.tickers:
        tickers = args.tickers.split(",")
    else:
        logger.info("%s 전체 종목 조회 중...", args.market)
        tickers = data_loader.load_market_tickers(market=args.market)
        if args.limit:
            tickers = tickers[: args.limit]

    logger.info("백테스트 대상: %d 종목", len(tickers))
    logger.info("기간: %s ~ %s", args.start, args.end)
    logger.info("전략 설정: 거래량 배수=%.1f, 익절=%.1f%%, 손절=%.1f%%",
                config.volume_multiplier,
                config.take_profit_pct * 100,
                config.stop_loss_pct * 100)

    result = engine.run(tickers, args.start, args.end)

    report = BacktestReport(result, config.initial_capital)
    report.print_report()

    if args.save_chart:
        report.plot_equity_curve(save_path="output/equity_curve.png")
        report.plot_drawdown(save_path="output/drawdown.png")

    if args.save_csv:
        report.export_trades_csv("output/trades.csv")


def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="주식 자동매매 백테스트 시스템",
    )

    parser.add_argument("--start", required=True, help="시작일 (예: 20250101)")
    parser.add_argument("--end", required=True, help="종료일 (예: 20251231)")
    parser.add_argument("--tickers", help="종목 코드 (쉼표 구분, 예: 005930,000660)")
    parser.add_argument("--market", default="KOSPI", choices=["KOSPI", "KOSDAQ"], help="시장 (기본: KOSPI)")
    parser.add_argument("--limit", type=int, help="종목 수 제한")
    parser.add_argument("--capital", type=float, default=10_000_000, help="초기 자본금 (기본: 1천만원)")
    parser.add_argument("--volume-mult", type=float, default=2.0, help="거래량 배수 (기본: 2.0)")
    parser.add_argument("--take-profit", type=float, default=3.0, help="익절 비율 %% (기본: 3.0)")
    parser.add_argument("--stop-loss", type=float, default=2.0, help="손절 비율 %% (기본: 2.0)")
    parser.add_argument("--max-trades", type=int, default=2, help="일일 최대 거래 (기본: 2)")
    parser.add_argument("--save-chart", action="store_true", help="차트 이미지 저장")
    parser.add_argument("--save-csv", action="store_true", help="거래 내역 CSV 저장")

    args = parser.parse_args()

    setup_logger()
    run_backtest(args)


if __name__ == "__main__":
    main()
