# 주식 자동매매 시스템 설계서

> **요약**: 거래량 급등 + 추세 추종 전략 기반 백테스트 엔진 및 키움 API 자동매매 시스템 설계
>
> **프로젝트**: stock-auto-trade
> **작성일**: 2026-03-05
> **상태**: Draft
> **계획서**: [stock-auto-trade.plan.md](../01-plan/features/stock-auto-trade.plan.md)

---

## 1. 개요

### 1.1 설계 목표

- 전략을 쉽게 교체/추가할 수 있는 확장 가능한 구조
- 백테스트와 실매매에서 동일한 전략 코드를 재사용
- 과거 데이터와 실시간 데이터의 인터페이스 통일

### 1.2 설계 원칙

- **전략-엔진 분리**: 전략 로직과 실행 엔진을 분리하여 독립적 테스트 가능
- **단일 책임**: 각 모듈은 하나의 역할만 담당
- **설정 외부화**: 매매 파라미터는 코드가 아닌 설정 파일로 관리

---

## 2. 아키텍처

### 2.1 시스템 구성도

```
┌──────────────────────────────────────────────────────────┐
│                     main.py (진입점)                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │ DataLoader   │───▶│   Strategy   │───▶│   Engine   │  │
│  │ (데이터 수집) │    │  (매매 전략)  │    │ (실행 엔진) │  │
│  └─────────────┘    └──────────────┘    └─────┬──────┘  │
│        │                                       │         │
│        │            ┌──────────────┐           │         │
│        │            │   Report     │◀──────────┘         │
│        │            │ (성과 분석)   │                     │
│        │            └──────────────┘                     │
│        │                                                 │
│  ┌─────▼─────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │ pykrx         │  │  pykiwoom    │  │  Telegram    │  │
│  │ (과거 데이터)   │  │ (키움 API)   │  │  (알림)      │  │
│  └───────────────┘  └──────────────┘  └─────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름

```
Phase 1 (백테스트):
  pykrx → DataLoader → DataFrame → Strategy.check_buy/sell() → BacktestEngine → Report

Phase 2 (실매매):
  키움 API → DataLoader → DataFrame → Strategy.check_buy/sell() → KiwoomBroker → 주문 → 알림
```

### 2.3 모듈 의존성

| 모듈 | 의존 대상 | 용도 |
|------|----------|------|
| `strategy/` | `pandas`, `numpy` | 매매 신호 계산 |
| `backtest/engine.py` | `strategy/`, `backtest/data_loader.py` | 시뮬레이션 실행 |
| `backtest/data_loader.py` | `pykrx` | KRX 과거 데이터 수집 |
| `backtest/report.py` | `pandas`, `matplotlib` | 성과 분석 및 시각화 |
| `broker/kiwoom.py` | `pykiwoom` | 키움 API 연동 (Phase 2) |
| `notification/telegram.py` | `python-telegram-bot` | 알림 전송 (Phase 3) |

---

## 3. 데이터 모델

### 3.1 핵심 데이터 구조

```python
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class SellReason(str, Enum):
    TAKE_PROFIT = "take_profit"   # 익절
    STOP_LOSS = "stop_loss"       # 손절
    SIGNAL = "signal"             # 전략 신호


@dataclass
class StockData:
    """일봉 주가 데이터"""
    date: date
    open: float          # 시가
    high: float          # 고가
    low: float           # 저가
    close: float         # 종가
    volume: int          # 거래량


@dataclass
class Signal:
    """매매 신호"""
    ticker: str          # 종목 코드
    side: OrderSide      # 매수/매도
    price: float         # 신호 발생 가격
    reason: str          # 신호 사유


@dataclass
class Trade:
    """체결된 거래"""
    ticker: str
    side: OrderSide
    price: float         # 체결 가격
    quantity: int        # 수량
    timestamp: datetime
    sell_reason: SellReason | None = None


@dataclass
class Position:
    """보유 포지션"""
    ticker: str
    buy_price: float     # 매수 단가
    quantity: int        # 보유 수량
    buy_date: date       # 매수일


@dataclass
class BacktestResult:
    """백테스트 결과"""
    trades: list[Trade]           # 전체 거래 내역
    total_return: float           # 총 수익률 (%)
    win_rate: float               # 승률 (%)
    max_drawdown: float           # 최대 낙폭 (%)
    sharpe_ratio: float           # 샤프 비율
    total_trades: int             # 총 거래 횟수
    winning_trades: int           # 수익 거래 수
    losing_trades: int            # 손실 거래 수
    avg_profit_per_trade: float   # 거래당 평균 수익률
```

### 3.2 설정 데이터

```python
@dataclass
class StrategyConfig:
    """전략 파라미터 설정"""
    # 매수 조건
    volume_multiplier: float = 2.0       # 거래량 배수 (5일 평균 대비)
    volume_lookback_days: int = 5        # 거래량 비교 기간

    # 매도 조건
    take_profit_pct: float = 0.03        # 익절 비율 (3%)
    stop_loss_pct: float = 0.02          # 손절 비율 (2%)

    # 리스크 관리
    max_daily_trades: int = 2            # 하루 최대 진입 횟수
    max_positions: int = 5               # 동시 보유 종목 수
    position_size_pct: float = 0.2       # 종목당 투자 비중 (20%)

    # 백테스트
    initial_capital: float = 10_000_000  # 초기 자본금 (1천만원)
    commission_rate: float = 0.00015     # 수수료율 (0.015%)
    slippage_pct: float = 0.001          # 슬리피지 (0.1%)
```

---

## 4. 핵심 클래스 설계

### 4.1 Strategy (전략 베이스 클래스)

```python
# strategy/base.py
from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """매매 전략 추상 클래스"""

    def __init__(self, config: StrategyConfig):
        self.config = config

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        """주가 데이터로부터 매매 신호 생성"""
        pass

    @abstractmethod
    def check_exit(self, position: Position, current_price: float) -> Signal | None:
        """보유 포지션의 청산 조건 확인 (익절/손절)"""
        pass
```

### 4.2 VolumeBreakoutStrategy (거래량 급등 전략)

```python
# strategy/volume_breakout.py

class VolumeBreakoutStrategy(BaseStrategy):
    """거래량 급등 + 추세 추종 전략"""

    def generate_signals(self, df: pd.DataFrame) -> list[Signal]:
        """
        매수 조건:
        1. 오늘 거래량 > 5일 평균 거래량 × volume_multiplier
        2. 오늘 종가 > 전일 종가
        """
        pass

    def check_exit(self, position: Position, current_price: float) -> Signal | None:
        """
        매도 조건:
        - 익절: 매수가 대비 +take_profit_pct 이상
        - 손절: 매수가 대비 -stop_loss_pct 이하
        """
        pass
```

### 4.3 DataLoader (데이터 수집)

```python
# backtest/data_loader.py

class DataLoader:
    """주가 데이터 수집기"""

    def load_stock_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """pykrx로 일봉 데이터 수집"""
        pass

    def load_market_tickers(self, market: str = "KOSPI") -> list[str]:
        """시장 전체 종목 코드 조회"""
        pass
```

### 4.4 BacktestEngine (백테스트 엔진)

```python
# backtest/engine.py

class BacktestEngine:
    """백테스트 시뮬레이션 엔진"""

    def __init__(
        self,
        strategy: BaseStrategy,
        data_loader: DataLoader,
        config: StrategyConfig,
    ):
        self.strategy = strategy
        self.data_loader = data_loader
        self.config = config

    def run(
        self,
        tickers: list[str],
        start_date: str,
        end_date: str,
    ) -> BacktestResult:
        """
        백테스트 실행 흐름:
        1. 각 종목별 과거 데이터 로드
        2. 날짜별 순회하며 전략 신호 체크
        3. 매수/매도 시뮬레이션 (수수료, 슬리피지 반영)
        4. 포지션 관리 (동시 보유 제한, 일일 거래 제한)
        5. 결과 집계
        """
        pass
```

### 4.5 Report (성과 분석)

```python
# backtest/report.py

class BacktestReport:
    """백테스트 성과 분석 리포트"""

    def __init__(self, result: BacktestResult):
        self.result = result

    def summary(self) -> dict:
        """핵심 성과 지표 요약"""
        pass

    def print_report(self) -> None:
        """CLI에 성과 리포트 출력"""
        pass

    def plot_equity_curve(self, save_path: str | None = None) -> None:
        """자산 곡선 차트 생성"""
        pass

    def plot_drawdown(self, save_path: str | None = None) -> None:
        """낙폭 차트 생성"""
        pass

    def export_trades_csv(self, path: str) -> None:
        """거래 내역 CSV 내보내기"""
        pass
```

---

## 5. 파일 구조

```
stock-auto-trade/
├── main.py                      # 진입점 (CLI)
├── config.py                    # StrategyConfig, 환경 설정
├── requirements.txt             # 의존성
├── .env                         # API 키 (gitignore)
├── .gitignore
├── CLAUDE.md
│
├── strategy/
│   ├── __init__.py
│   ├── base.py                  # BaseStrategy 추상 클래스
│   └── volume_breakout.py       # 거래량 급등 전략
│
├── backtest/
│   ├── __init__.py
│   ├── engine.py                # 백테스트 엔진
│   ├── data_loader.py           # pykrx 데이터 수집
│   └── report.py                # 성과 분석 리포트
│
├── broker/                      # (Phase 2)
│   ├── __init__.py
│   ├── base.py                  # BaseBroker 추상 클래스
│   ├── kiwoom.py                # 키움 API 연동
│   └── order.py                 # 주문 관리
│
├── notification/                # (Phase 3)
│   ├── __init__.py
│   └── telegram.py              # 텔레그램 알림
│
├── utils/
│   ├── __init__.py
│   └── logger.py                # 로깅 설정
│
└── tests/
    ├── __init__.py
    ├── test_strategy.py         # 전략 단위 테스트
    ├── test_engine.py           # 백테스트 엔진 테스트
    └── test_data_loader.py      # 데이터 수집 테스트
```

---

## 6. 에러 처리

### 6.1 에러 분류

| 분류 | 에러 | 처리 방법 |
|------|------|----------|
| 데이터 | pykrx 데이터 수집 실패 | 재시도 3회, 실패 시 해당 종목 건너뛰기 + 로그 |
| 데이터 | 빈 데이터 (상장폐지 등) | 해당 종목 건너뛰기 |
| 전략 | 거래량 데이터 부족 (5일 미만) | 신호 생성 건너뛰기 |
| 주문 | 잔고 부족 | 주문 건너뛰기 + 로그 |
| API | 키움 API 연결 끊김 (Phase 2) | 재연결 3회, 실패 시 텔레그램 알림 |
| API | 키움 API 주문 실패 (Phase 2) | 재시도 2회, 실패 시 알림 |

### 6.2 로깅 전략

```python
# utils/logger.py
import logging

# 로그 레벨별 용도
# DEBUG   : 상세 데이터 (개별 종목 신호, 가격)
# INFO    : 매수/매도 체결, 백테스트 진행률
# WARNING : 데이터 누락, 건너뛴 종목
# ERROR   : API 에러, 연결 실패
# CRITICAL: 시스템 중단 수준 오류

# 파일 로그 + 콘솔 로그 분리
# 파일: logs/YYYY-MM-DD.log (일별 로테이션)
# 콘솔: INFO 이상만 출력
```

---

## 7. 보안 고려사항

- [x] API 키 `.env`로 분리 (gitignore 처리)
- [x] `.gitignore`에 `.env`, `credentials.json` 포함
- [ ] 키움 API 인증 정보 암호화 저장 (Phase 2)
- [ ] 텔레그램 봇 토큰 환경 변수 관리 (Phase 3)

---

## 8. 테스트 계획

### 8.1 테스트 범위

| 유형 | 대상 | 도구 |
|------|------|------|
| 단위 테스트 | 전략 신호 생성, 익절/손절 로직 | pytest |
| 단위 테스트 | 성과 지표 계산 (수익률, 승률, MDD) | pytest |
| 통합 테스트 | 백테스트 엔진 전체 흐름 | pytest |
| 데이터 테스트 | pykrx 데이터 수집 정합성 | pytest (mock) |

### 8.2 핵심 테스트 케이스

- [ ] 거래량 급등 조건 충족 시 매수 신호 생성
- [ ] 거래량 급등이지만 종가 하락 시 매수 신호 없음
- [ ] 익절 조건 도달 시 매도 신호 생성
- [ ] 손절 조건 도달 시 매도 신호 생성
- [ ] 하루 최대 진입 횟수 초과 시 신호 무시
- [ ] 동시 보유 종목 수 초과 시 신호 무시
- [ ] 수수료/슬리피지 반영된 수익률 계산
- [ ] MDD 계산 정확성

---

## 9. 환경 변수

| 변수 | 용도 | Phase | 예시 |
|------|------|-------|------|
| `KIWOOM_APP_KEY` | 키움 API 앱 키 | 2 | `PSxxxxx` |
| `KIWOOM_APP_SECRET` | 키움 API 시크릿 | 2 | `xxxxxxxxx` |
| `KIWOOM_ACCOUNT` | 키움 계좌번호 | 2 | `5000000000` |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 | 3 | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID | 3 | `123456789` |

---

## 10. 구현 순서 (Phase 1 상세)

### 10.1 Phase 1 구현 단계

| 순서 | 파일 | 작업 내용 | 의존성 |
|------|------|----------|--------|
| 1 | `utils/logger.py` | 로깅 설정 | 없음 |
| 2 | `config.py` | StrategyConfig 정의 | 없음 |
| 3 | `strategy/base.py` | BaseStrategy 추상 클래스 | config.py |
| 4 | `strategy/volume_breakout.py` | 거래량 급등 전략 구현 | strategy/base.py |
| 5 | `backtest/data_loader.py` | pykrx 데이터 수집 | pykrx |
| 6 | `backtest/engine.py` | 백테스트 엔진 구현 | strategy/, data_loader |
| 7 | `backtest/report.py` | 성과 분석 리포트 | engine.py |
| 8 | `main.py` | CLI 진입점 | 전체 |
| 9 | `tests/` | 테스트 코드 | 전체 |

### 10.2 의존성 (requirements.txt)

```
pykrx>=1.0.45
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
python-dotenv>=1.0.0
pytest>=7.4.0
ruff>=0.1.0
mypy>=1.5.0
```

---

## 버전 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 0.1 | 2026-03-05 | 초안 작성 | Claude |
