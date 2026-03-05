"""데이터 수집 단위 테스트 (mock 기반)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backtest.data_loader import DataLoader


@pytest.fixture
def data_loader() -> DataLoader:
    return DataLoader()


class TestDataLoader:
    """DataLoader 테스트."""

    @patch("backtest.data_loader.pykrx_stock")
    def test_load_stock_data_success(
        self, mock_pykrx: MagicMock, data_loader: DataLoader
    ) -> None:
        """정상 데이터 수집 시 영문 컬럼 DataFrame을 반환한다."""
        mock_df = pd.DataFrame(
            {
                "시가": [10000, 10100],
                "고가": [10200, 10300],
                "저가": [9900, 10000],
                "종가": [10100, 10200],
                "거래량": [100000, 200000],
            },
            index=pd.date_range("2025-01-01", periods=2),
        )
        mock_pykrx.get_market_ohlcv_by_date.return_value = mock_df

        result = data_loader.load_stock_data("005930", "20250101", "20250102")

        assert not result.empty
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert len(result) == 2

    @patch("backtest.data_loader.pykrx_stock")
    def test_load_stock_data_empty(
        self, mock_pykrx: MagicMock, data_loader: DataLoader
    ) -> None:
        """빈 데이터 수집 시 빈 DataFrame을 반환한다."""
        mock_pykrx.get_market_ohlcv_by_date.return_value = pd.DataFrame()

        result = data_loader.load_stock_data("999999", "20250101", "20250102")

        assert result.empty

    @patch("backtest.data_loader.pykrx_stock")
    def test_load_stock_data_filters_zero_volume(
        self, mock_pykrx: MagicMock, data_loader: DataLoader
    ) -> None:
        """거래량 0인 날을 필터링한다."""
        mock_df = pd.DataFrame(
            {
                "시가": [10000, 10100, 10200],
                "고가": [10200, 10300, 10400],
                "저가": [9900, 10000, 10100],
                "종가": [10100, 10200, 10300],
                "거래량": [100000, 0, 200000],  # 두 번째 날 거래 없음
            },
            index=pd.date_range("2025-01-01", periods=3),
        )
        mock_pykrx.get_market_ohlcv_by_date.return_value = mock_df

        result = data_loader.load_stock_data("005930", "20250101", "20250103")

        assert len(result) == 2  # 거래량 0인 날 제거

    @patch("backtest.data_loader.pykrx_stock")
    def test_load_stock_data_retries_on_failure(
        self, mock_pykrx: MagicMock, data_loader: DataLoader
    ) -> None:
        """API 실패 시 재시도 후 빈 DataFrame을 반환한다."""
        mock_pykrx.get_market_ohlcv_by_date.side_effect = Exception("API 에러")

        result = data_loader.load_stock_data("005930", "20250101", "20250102")

        assert result.empty
        # 3회 재시도 확인
        assert mock_pykrx.get_market_ohlcv_by_date.call_count == 3

    @patch("backtest.data_loader.pykrx_stock")
    def test_load_market_tickers_success(
        self, mock_pykrx: MagicMock, data_loader: DataLoader
    ) -> None:
        """종목 목록 조회 성공."""
        mock_pykrx.get_market_ticker_list.return_value = ["005930", "000660"]

        result = data_loader.load_market_tickers(market_date="20250101")

        assert result == ["005930", "000660"]

    @patch("backtest.data_loader.pykrx_stock")
    def test_load_market_tickers_failure(
        self, mock_pykrx: MagicMock, data_loader: DataLoader
    ) -> None:
        """종목 목록 조회 실패 시 빈 리스트."""
        mock_pykrx.get_market_ticker_list.side_effect = Exception("에러")

        result = data_loader.load_market_tickers()

        assert result == []
