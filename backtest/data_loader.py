import logging
import time
from datetime import date

import pandas as pd
from pykrx import stock as pykrx_stock

logger = logging.getLogger("stock-auto-trade")

MAX_RETRIES = 3
RETRY_DELAY = 1.0


class DataLoader:
    """pykrx를 이용한 KRX 주가 데이터 수집기."""

    def load_stock_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """일봉 데이터를 수집한다. 실패 시 최대 3회 재시도.

        Args:
            ticker: 종목 코드 (예: "005930")
            start_date: 시작일 (예: "20250101")
            end_date: 종료일 (예: "20251231")

        Returns:
            일봉 DataFrame (columns: Open, High, Low, Close, Volume)
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                df = pykrx_stock.get_market_ohlcv_by_date(
                    fromdate=start_date,
                    todate=end_date,
                    ticker=ticker,
                )

                if df.empty:
                    logger.warning("데이터 없음: %s (%s ~ %s)", ticker, start_date, end_date)
                    return pd.DataFrame()

                # 컬럼명 영문 통일
                df = df.rename(
                    columns={
                        "시가": "Open",
                        "고가": "High",
                        "저가": "Low",
                        "종가": "Close",
                        "거래량": "Volume",
                    }
                )

                # 필요한 컬럼만 유지
                df = df[["Open", "High", "Low", "Close", "Volume"]]

                # 거래량 0인 날 제거 (거래정지일)
                df = df[df["Volume"] > 0]

                logger.debug("데이터 로드 완료: %s (%d 거래일)", ticker, len(df))
                return df

            except Exception:
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "데이터 수집 실패 (재시도 %d/%d): %s",
                        attempt, MAX_RETRIES, ticker,
                    )
                    time.sleep(RETRY_DELAY)
                else:
                    logger.exception("데이터 수집 최종 실패: %s", ticker)

        return pd.DataFrame()

    def load_market_tickers(self, market_date: str | None = None, market: str = "KOSPI") -> list[str]:
        """시장 전체 종목 코드를 조회한다.

        Args:
            market_date: 기준일 (예: "20250101"), None이면 오늘
            market: 시장 구분 ("KOSPI" 또는 "KOSDAQ")

        Returns:
            종목 코드 리스트
        """
        if market_date is None:
            market_date = date.today().strftime("%Y%m%d")

        try:
            tickers = pykrx_stock.get_market_ticker_list(market_date, market=market)
            logger.info("%s 종목 수: %d", market, len(tickers))
            return tickers
        except Exception:
            logger.exception("종목 목록 조회 실패: %s", market)
            return []

    def get_ticker_name(self, ticker: str) -> str:
        """종목 코드로 종목명을 조회한다."""
        try:
            return pykrx_stock.get_market_ticker_name(ticker)
        except Exception:
            return ticker
