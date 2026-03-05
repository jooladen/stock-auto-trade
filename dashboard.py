"""Streamlit 백테스트 학습 대시보드.

실행: streamlit run dashboard.py
"""

import logging
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from backtest.data_loader import DataLoader
from backtest.engine import BacktestEngine
from config import StrategyConfig
from strategy.base import BacktestResult, OrderSide, Trade
from strategy.volume_breakout import VolumeBreakoutStrategy

logger = logging.getLogger("stock-auto-trade")

POPULAR_TICKERS: dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035720": "카카오",
    "035420": "네이버",
    "005380": "현대차",
    "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스",
    "000270": "기아",
    "068270": "셀트리온",
    "105560": "KB금융",
}

st.set_page_config(page_title="백테스트 학습 대시보드", layout="wide")
st.title("백테스트 학습 대시보드")


# --- 사이드바: 파라미터 조절 ---
st.sidebar.header("종목 설정")

ticker_options = [f"{code} ({name})" for code, name in POPULAR_TICKERS.items()]
selected_tickers = st.sidebar.multiselect(
    "종목 선택",
    options=ticker_options,
    default=[ticker_options[0]],
    help="여러 종목을 동시에 선택할 수 있습니다.",
)

custom_tickers = st.sidebar.text_input(
    "직접 입력 (쉼표 구분)",
    placeholder="예: 005930,000660,035720",
    help="목록에 없는 종목은 여기에 코드를 직접 입력하세요.",
)

st.sidebar.header("기간 설정")
col_start, col_end = st.sidebar.columns(2)
start_date = col_start.date_input("시작일", value=date(2025, 1, 1))
end_date = col_end.date_input("종료일", value=date(2025, 12, 31))

st.sidebar.header("전략 파라미터")
volume_multiplier = st.sidebar.slider("거래량 배수", 1.0, 5.0, 2.0, 0.1)
take_profit_pct = st.sidebar.slider("익절 %", 1.0, 10.0, 3.0, 0.5) / 100
stop_loss_pct = st.sidebar.slider("손절 %", 1.0, 10.0, 2.0, 0.5) / 100
initial_capital = st.sidebar.number_input(
    "초기 자본금 (원)", value=10_000_000, step=1_000_000, min_value=1_000_000
)
max_daily_trades = st.sidebar.number_input(
    "일일 최대 거래 횟수", value=2, min_value=1, max_value=10
)

st.sidebar.header("차트 설정")
chart_type = st.sidebar.radio("차트 유형", ["캔들스틱", "종가선"], horizontal=True)

run_button = st.sidebar.button("백테스트 실행", type="primary", use_container_width=True)


def _parse_tickers() -> list[str]:
    """선택된 종목과 직접 입력 종목을 합쳐 코드 리스트를 반환한다."""
    codes: list[str] = []

    for item in selected_tickers:
        code = item.split(" ")[0]
        codes.append(code)

    if custom_tickers.strip():
        for code in custom_tickers.split(","):
            code = code.strip()
            if code and code not in codes:
                codes.append(code)

    return codes


def _pair_trades(trades: list[Trade]) -> list[dict]:
    """매수-매도 페어를 매칭하여 거래 상세 리스트를 반환한다."""
    pairs: list[dict] = []
    buy_queue: dict[str, list[Trade]] = {}

    for trade in trades:
        if trade.side == OrderSide.BUY:
            buy_queue.setdefault(trade.ticker, []).append(trade)
        elif trade.side == OrderSide.SELL and buy_queue.get(trade.ticker):
            buy_trade = buy_queue[trade.ticker].pop(0)
            profit_pct = (trade.price - buy_trade.price) / buy_trade.price
            profit_amount = (trade.price - buy_trade.price) * trade.quantity
            pairs.append(
                {
                    "ticker": trade.ticker,
                    "buy_date": buy_trade.timestamp.strftime("%Y-%m-%d"),
                    "buy_price": buy_trade.price,
                    "sell_date": trade.timestamp.strftime("%Y-%m-%d"),
                    "sell_price": trade.price,
                    "quantity": trade.quantity,
                    "profit_pct": profit_pct,
                    "profit_amount": profit_amount,
                    "sell_reason": trade.sell_reason or "",
                }
            )
    return pairs


def _render_metrics(result: BacktestResult) -> None:
    """성과 요약 카드 렌더링."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("총수익률", f"{result.total_return:+.2f}%")
    c2.metric("승률", f"{result.win_rate:.1f}%")
    c3.metric("MDD", f"{result.max_drawdown:.2f}%")
    c4.metric("샤프비율", f"{result.sharpe_ratio:.2f}")
    c5.metric("총 거래", f"{result.total_trades}건")
    c6.metric("평균 수익", f"{result.avg_profit_per_trade:+.2f}%")


def _render_price_chart(
    df: pd.DataFrame,
    trades: list[Trade],
    pairs: list[dict],
    ticker: str,
    use_candlestick: bool,
    vol_mult: float,
) -> None:
    """주가 + 매매 포인트 + 거래량 연동 차트."""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=["주가 차트", "거래량"],
    )

    # 주가 차트: 캔들스틱 or 종가선
    if use_candlestick:
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
                increasing_line_color="#EF5350",
                decreasing_line_color="#1976D2",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Close"],
                mode="lines",
                name="종가",
                line={"color": "#636EFA"},
            ),
            row=1,
            col=1,
        )

    # 이 종목의 거래만 필터
    ticker_trades = [t for t in trades if t.ticker == ticker]
    ticker_pairs = [p for p in pairs if p["ticker"] == ticker]

    # 보유 구간 하이라이트
    for pair in ticker_pairs:
        buy_dt = pd.Timestamp(pair["buy_date"])
        sell_dt = pd.Timestamp(pair["sell_date"])
        color = "rgba(0,200,0,0.1)" if pair["profit_pct"] > 0 else "rgba(200,0,0,0.1)"
        fig.add_vrect(
            x0=buy_dt,
            x1=sell_dt,
            fillcolor=color,
            layer="below",
            line_width=0,
            row=1,
            col=1,
        )

    # 매수 마커
    buy_trades = [t for t in ticker_trades if t.side == OrderSide.BUY]
    if buy_trades:
        buy_hovers = []
        for t in buy_trades:
            cost = t.price * t.quantity
            hover = (
                f"<b>매수 신호</b><br>"
                f"──────────<br>"
                f"날짜: {t.timestamp.strftime('%Y-%m-%d')}<br>"
                f"매수가: {t.price:,.0f}원<br>"
                f"수량: {t.quantity:,}주<br>"
                f"투자금: {cost:,.0f}원<br>"
                f"──────────<br>"
                f"<b>사유:</b> {t.reason or '신호 발생'}"
            )
            buy_hovers.append(hover)

        fig.add_trace(
            go.Scatter(
                x=[t.timestamp for t in buy_trades],
                y=[t.price for t in buy_trades],
                mode="markers",
                name="매수",
                marker={"symbol": "triangle-up", "size": 14, "color": "green"},
                hovertext=buy_hovers,
                hoverinfo="text",
            ),
            row=1,
            col=1,
        )

    # 매도 마커 (페어 정보로 수익률 포함)
    sell_trades = [t for t in ticker_trades if t.side == OrderSide.SELL]
    if sell_trades:
        # 매도 거래에 대응하는 페어 매칭 (수익률 표시용)
        pair_by_sell_date: dict[str, dict] = {}
        for p in ticker_pairs:
            pair_by_sell_date[p["sell_date"]] = p

        sell_hovers = []
        for t in sell_trades:
            sell_date_str = t.timestamp.strftime("%Y-%m-%d")
            pair = pair_by_sell_date.get(sell_date_str)
            amount = t.price * t.quantity

            hover = (
                f"<b>매도 체결</b><br>"
                f"──────────<br>"
                f"날짜: {sell_date_str}<br>"
                f"매도가: {t.price:,.0f}원<br>"
                f"수량: {t.quantity:,}주<br>"
                f"매도금: {amount:,.0f}원<br>"
            )
            if pair:
                hover += (
                    f"──────────<br>"
                    f"매수가: {pair['buy_price']:,.0f}원 ({pair['buy_date']})<br>"
                    f"<b>수익률: {pair['profit_pct']:+.2%}</b><br>"
                    f"<b>손익: {pair['profit_amount']:+,.0f}원</b><br>"
                )
            hover += (
                f"──────────<br>"
                f"<b>사유:</b> {t.reason or t.sell_reason or ''}"
            )
            sell_hovers.append(hover)

        fig.add_trace(
            go.Scatter(
                x=[t.timestamp for t in sell_trades],
                y=[t.price for t in sell_trades],
                mode="markers",
                name="매도",
                marker={"symbol": "triangle-down", "size": 14, "color": "red"},
                hovertext=sell_hovers,
                hoverinfo="text",
            ),
            row=1,
            col=1,
        )

    # --- 거래량 차트 ---
    vol_ma5 = df["Volume"].rolling(5).mean()
    is_surge = df["Volume"] > vol_ma5 * vol_mult
    bar_colors = ["#EF5350" if s else "#B0BEC5" for s in is_surge]

    # 거래량 바 호버 텍스트
    vol_hovers = []
    for dt in df.index:
        vol = df.loc[dt, "Volume"]
        ma_val = vol_ma5.loc[dt]
        close = df.loc[dt, "Close"]
        date_str = dt.strftime("%Y-%m-%d")
        hover = f"<b>{date_str}</b><br>거래량: {int(vol):,}"
        if pd.notna(ma_val) and ma_val > 0:
            ratio = vol / ma_val
            hover += f"<br>5일 평균: {int(ma_val):,}<br>배수: {ratio:.1f}배"
            threshold = ma_val * vol_mult
            if vol > threshold:
                hover += (
                    f"<br>──────────<br>"
                    f"<b>급등 감지!</b><br>"
                    f"기준({vol_mult}배): {int(threshold):,}<br>"
                    f"종가: {close:,.0f}원"
                )
            else:
                hover += f"<br>기준({vol_mult}배): {int(threshold):,}"
        vol_hovers.append(hover)

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="거래량",
            marker_color=bar_colors,
            opacity=0.7,
            hovertext=vol_hovers,
            hoverinfo="text",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=vol_ma5,
            mode="lines",
            name="5일 평균",
            line={"color": "orange", "width": 1.5},
        ),
        row=2,
        col=1,
    )

    # 급등일에 배수 기준선 추가
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=vol_ma5 * vol_mult,
            mode="lines",
            name=f"기준선 ({vol_mult}배)",
            line={"color": "red", "width": 1, "dash": "dash"},
        ),
        row=2,
        col=1,
    )

    # 급등일 주석 (최대 10개)
    surge_dates = df.index[is_surge]
    for dt in surge_dates[:10]:
        vol = df.loc[dt, "Volume"]
        ma_val = vol_ma5.loc[dt]
        if pd.notna(ma_val) and ma_val > 0:
            ratio = vol / ma_val
            fig.add_annotation(
                x=dt,
                y=vol,
                text=f"{ratio:.1f}배",
                showarrow=True,
                arrowhead=2,
                font={"size": 10, "color": "red"},
                row=2,
                col=1,
            )

    fig.update_layout(
        height=700,
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(title_text="가격 (원)", row=1, col=1)
    fig.update_yaxes(title_text="거래량", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)


def _render_trade_table(pairs: list[dict], ticker_names: dict[str, str]) -> None:
    """거래 상세 테이블."""
    if not pairs:
        st.info("거래 내역이 없습니다.")
        return

    rows = []
    for i, p in enumerate(pairs, 1):
        name = ticker_names.get(p["ticker"], p["ticker"])
        rows.append(
            {
                "#": i,
                "종목": f"{name} ({p['ticker']})",
                "매수일": p["buy_date"],
                "매수가": f"{p['buy_price']:,.0f}",
                "매도일": p["sell_date"],
                "매도가": f"{p['sell_price']:,.0f}",
                "수익률": f"{p['profit_pct']:+.2%}",
                "손익금액": f"{p['profit_amount']:+,.0f}",
                "매도사유": p["sell_reason"],
            }
        )

    table_df = pd.DataFrame(rows)

    def _highlight_row(row: pd.Series) -> list[str]:
        pct_str = row["수익률"]
        val = float(pct_str.replace("%", "").replace("+", "").replace(",", "")) / 100
        if val > 0:
            return ["background-color: rgba(0,200,0,0.15)"] * len(row)
        if val < 0:
            return ["background-color: rgba(200,0,0,0.15)"] * len(row)
        return [""] * len(row)

    styled = table_df.style.apply(_highlight_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_equity_chart(result: BacktestResult) -> None:
    """자산 곡선 차트."""
    equity = result.equity_curve
    if not equity or len(equity) <= 1:
        return

    eq_min = min(equity)
    eq_max = max(equity)
    margin = (eq_max - eq_min) * 0.15 or eq_max * 0.01

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            y=equity,
            mode="lines",
            name="자산",
            line={"color": "#636EFA", "width": 2},
        )
    )
    fig.update_layout(
        height=300,
        title="자산 곡선 (Equity Curve)",
        yaxis_title="자산 (원)",
        yaxis_range=[eq_min - margin, eq_max + margin],
        xaxis_title="거래일",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 메인 실행 ---
if run_button:
    tickers = _parse_tickers()

    if not tickers:
        st.error("종목을 1개 이상 선택하거나 입력해 주세요.")
    elif start_date >= end_date:
        st.error("시작일은 종료일보다 이전이어야 합니다.")
    else:
        config = StrategyConfig(
            volume_multiplier=volume_multiplier,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            initial_capital=initial_capital,
            max_daily_trades=max_daily_trades,
        )

        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        with st.spinner("데이터 로딩 중..."):
            data_loader = DataLoader()
            stock_data: dict[str, pd.DataFrame] = {}
            ticker_names: dict[str, str] = {}
            for t in tickers:
                df = data_loader.load_stock_data(t, start_str, end_str)
                if not df.empty:
                    stock_data[t] = df
                    ticker_names[t] = data_loader.get_ticker_name(t)
                else:
                    st.warning(f"종목 {t}의 데이터를 가져올 수 없습니다.")

        if not stock_data:
            st.error("유효한 데이터가 없습니다.")
        else:
            with st.spinner("백테스트 실행 중..."):
                strategy = VolumeBreakoutStrategy(config)
                engine = BacktestEngine(strategy, data_loader, config)
                result = engine.run(list(stock_data.keys()), start_str, end_str)

            # 1. 성과 요약
            st.markdown("### 성과 요약")
            _render_metrics(result)

            # 2. 자산 곡선
            st.markdown("### 자산 곡선")
            _render_equity_chart(result)

            # 3. 종목별 차트 (탭)
            pairs = _pair_trades(result.trades)
            use_candle = chart_type == "캔들스틱"

            if len(stock_data) == 1:
                t = list(stock_data.keys())[0]
                name = ticker_names.get(t, t)
                st.markdown(f"### {name} ({t})")
                _render_price_chart(
                    stock_data[t], result.trades, pairs, t, use_candle, volume_multiplier
                )
            else:
                st.markdown("### 종목별 차트")
                tab_labels = [
                    f"{ticker_names.get(t, t)} ({t})" for t in stock_data
                ]
                tabs = st.tabs(tab_labels)
                for tab, t in zip(tabs, stock_data):
                    with tab:
                        _render_price_chart(
                            stock_data[t], result.trades, pairs, t, use_candle, volume_multiplier
                        )

            # 4. 거래 상세 테이블
            st.markdown("### 거래 상세")
            _render_trade_table(pairs, ticker_names)
else:
    st.info("사이드바에서 종목과 파라미터를 설정하고 '백테스트 실행' 버튼을 눌러주세요.")
