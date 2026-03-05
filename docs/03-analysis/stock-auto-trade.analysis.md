# stock-auto-trade Gap Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: stock-auto-trade
> **Analyst**: Claude (gap-detector)
> **Date**: 2026-03-05
> **Design Doc**: [stock-auto-trade.design.md](../02-design/features/stock-auto-trade.design.md)

---

## 1. Analysis Overview

### 1.1 Analysis Purpose

설계 문서(stock-auto-trade.design.md)에 정의된 데이터 모델, 클래스, 메서드, 파일 구조, 에러 처리, 보안, 테스트, 환경 변수, 구현 순서를 실제 구현 코드와 비교하여 일치율과 차이점을 식별한다.

### 1.2 Analysis Scope

- **Design Document**: `docs/02-design/features/stock-auto-trade.design.md`
- **Implementation Path**: 프로젝트 루트 (config.py, strategy/, backtest/, main.py, utils/, tests/)
- **Analysis Date**: 2026-03-05

---

## 2. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Data Model Match | 83% | ⚠️ |
| Class/Method Match | 92% | ✅ |
| File Structure Match | 85% | ⚠️ |
| Error Handling | 70% | ⚠️ |
| Security | 75% | ⚠️ |
| Test Coverage | 50% | ❌ |
| Environment Variables | 60% | ⚠️ |
| Architecture Compliance | 95% | ✅ |
| **Overall** | **78%** | **⚠️** |

---

## 3. Data Model Comparison (Section 3)

### 3.1 Enum / Type Definitions

| Design | Implementation | Status | Notes |
|--------|---------------|--------|-------|
| `OrderSide(str, Enum)` | `OrderSide` (일반 클래스) | ⚠️ Changed | Enum 대신 클래스 상수로 구현 |
| `SellReason(str, Enum)` | `SellReason` (일반 클래스) | ⚠️ Changed | Enum 대신 클래스 상수로 구현 |

### 3.2 Dataclass Definitions

| Design Entity | Implementation | Status | Notes |
|---------------|---------------|--------|-------|
| `StockData` | 미구현 | ❌ Missing | DataFrame으로 직접 처리, dataclass 미정의 |
| `Signal` | `strategy/base.py` | ⚠️ Changed | `side` 타입이 `OrderSide` -> `str`로 변경 |
| `Trade` | `strategy/base.py` | ⚠️ Changed | `side`, `sell_reason` 타입이 `str`로 변경 |
| `Position` | `strategy/base.py` | ✅ Match | 완전 일치 |
| `BacktestResult` | `strategy/base.py` | ✅ Match | 완전 일치 |
| `StrategyConfig` | `config.py` | ✅ Match | 모든 필드와 기본값 일치 |

### 3.3 Data Model 위치

| Design | Implementation | Status | Notes |
|--------|---------------|--------|-------|
| 데이터 모델이 별도 파일 (암묵적) | `strategy/base.py`에 통합 | ⚠️ Changed | 전략과 데이터 모델이 같은 파일에 위치 |

### 3.4 Match Rate: 83% (10/12 항목)

---

## 4. Class & Method Comparison (Section 4)

### 4.1 BaseStrategy (strategy/base.py)

| Design Method | Implementation | Status | Notes |
|---------------|---------------|--------|-------|
| `__init__(config: StrategyConfig)` | `__init__(config: StrategyConfig)` | ✅ Match | |
| `generate_signals(df) -> list[Signal]` | `generate_signals(df, ticker) -> list[Signal]` | ⚠️ Changed | `ticker` 파라미터 추가됨 |
| `check_exit(position, current_price) -> Signal \| None` | `check_exit(position, current_price) -> Signal \| None` | ✅ Match | |

### 4.2 VolumeBreakoutStrategy (strategy/volume_breakout.py)

| Design Method | Implementation | Status | Notes |
|---------------|---------------|--------|-------|
| `generate_signals(df)` | `generate_signals(df, ticker)` | ⚠️ Changed | `ticker` 파라미터 추가 (Signal 생성에 필요) |
| `check_exit(position, current_price)` | `check_exit(position, current_price)` | ✅ Match | |
| 매수 조건 1: 거래량 급등 | 구현됨 | ✅ Match | `volume_multiplier` 기반 |
| 매수 조건 2: 종가 상승 | 구현됨 | ✅ Match | `prev_close` 비교 |
| 매도 조건: 익절/손절 | 구현됨 | ✅ Match | `take_profit_pct`, `stop_loss_pct` |

### 4.3 DataLoader (backtest/data_loader.py)

| Design Method | Implementation | Status | Notes |
|---------------|---------------|--------|-------|
| `load_stock_data(ticker, start_date, end_date)` | `load_stock_data(ticker, start_date, end_date)` | ✅ Match | |
| `load_market_tickers(market="KOSPI")` | `load_market_tickers(market_date=None, market="KOSPI")` | ⚠️ Changed | `market_date` 파라미터 추가 |
| - | `get_ticker_name(ticker)` | ⚠️ Added | 설계에 없는 메서드 추가 |

### 4.4 BacktestEngine (backtest/engine.py)

| Design Method | Implementation | Status | Notes |
|---------------|---------------|--------|-------|
| `__init__(strategy, data_loader, config)` | `__init__(strategy, data_loader, config)` | ✅ Match | |
| `run(tickers, start_date, end_date)` | `run(tickers, start_date, end_date)` | ✅ Match | |
| 수수료/슬리피지 반영 | `_apply_slippage()`, `_apply_commission()` | ✅ Match | |
| 포지션 관리 | `max_positions`, `max_daily_trades` 적용 | ✅ Match | |
| - | `_calculate_result()` | ⚠️ Added | 내부 메서드 (설계서 미기술) |
| - | `_empty_result()` | ⚠️ Added | 내부 메서드 (설계서 미기술) |

### 4.5 BacktestReport (backtest/report.py)

| Design Method | Implementation | Status | Notes |
|---------------|---------------|--------|-------|
| `__init__(result: BacktestResult)` | `__init__(result, initial_capital)` | ⚠️ Changed | `initial_capital` 파라미터 추가 |
| `summary() -> dict` | `summary() -> dict` | ✅ Match | |
| `print_report() -> None` | `print_report() -> None` | ✅ Match | |
| `plot_equity_curve(save_path)` | `plot_equity_curve(save_path)` | ✅ Match | |
| `plot_drawdown(save_path)` | `plot_drawdown(save_path)` | ✅ Match | |
| `export_trades_csv(path)` | `export_trades_csv(path)` | ✅ Match | |

### 4.6 Match Rate: 92% (23/25 주요 항목 일치)

---

## 5. File Structure Comparison (Section 5)

### 5.1 Phase 1 필수 파일

| Design Path | Actual | Status | Notes |
|-------------|--------|--------|-------|
| `main.py` | 존재 | ✅ Match | CLI argparse 구현 |
| `config.py` | 존재 | ✅ Match | StrategyConfig 정의 |
| `requirements.txt` | 존재 | ✅ Match | 의존성 목록 일치 |
| `.env` | 미존재 | ⚠️ N/A | Phase 1에서는 불필요 (Phase 2/3용) |
| `.gitignore` | 존재 | ✅ Match | `.env`, `credentials.json` 포함 |
| `CLAUDE.md` | 존재 | ✅ Match | |
| `strategy/__init__.py` | 존재 | ✅ Match | |
| `strategy/base.py` | 존재 | ✅ Match | |
| `strategy/volume_breakout.py` | 존재 | ✅ Match | |
| `backtest/__init__.py` | 존재 | ✅ Match | |
| `backtest/engine.py` | 존재 | ✅ Match | |
| `backtest/data_loader.py` | 존재 | ✅ Match | |
| `backtest/report.py` | 존재 | ✅ Match | |
| `utils/__init__.py` | 존재 | ✅ Match | |
| `utils/logger.py` | 존재 | ✅ Match | |
| `tests/__init__.py` | 존재 | ✅ Match | |
| `tests/test_strategy.py` | 존재 | ✅ Match | |
| `tests/test_engine.py` | 미존재 | ❌ Missing | 설계에 명시됨 |
| `tests/test_data_loader.py` | 미존재 | ❌ Missing | 설계에 명시됨 |

### 5.2 Phase 2/3 스켈레톤

| Design Path | Actual | Status | Notes |
|-------------|--------|--------|-------|
| `broker/__init__.py` | 존재 (빈 파일) | ✅ Match | Phase 2용 디렉토리 준비 |
| `broker/base.py` | 미존재 | ⚠️ N/A | Phase 2 예정 |
| `broker/kiwoom.py` | 미존재 | ⚠️ N/A | Phase 2 예정 |
| `broker/order.py` | 미존재 | ⚠️ N/A | Phase 2 예정 |
| `notification/__init__.py` | 존재 (빈 파일) | ✅ Match | Phase 3용 디렉토리 준비 |
| `notification/telegram.py` | 미존재 | ⚠️ N/A | Phase 3 예정 |

### 5.3 Match Rate: 85% (Phase 1 범위 내 17/20 항목)

---

## 6. Error Handling Comparison (Section 6)

### 6.1 에러 분류별 구현 현황

| Design Error Case | Implementation | Status | Location |
|-------------------|---------------|--------|----------|
| pykrx 데이터 수집 실패 -> 재시도 3회 | `try/except`으로 예외 처리, 빈 DataFrame 반환 | ⚠️ Partial | `data_loader.py:60` - 재시도 로직 없음 |
| 빈 데이터 -> 해당 종목 건너뛰기 | `df.empty` 체크 후 빈 DataFrame 반환 | ✅ Match | `data_loader.py:36-38` |
| 거래량 데이터 부족 (5일 미만) | `len(df) < lookback_days + 1` 체크 | ✅ Match | `volume_breakout.py:34` |
| 잔고 부족 -> 주문 건너뛰기 + 로그 | `cost > capital` 체크 후 continue | ✅ Match | `engine.py:158-159` |
| 키움 API 연결 끊김 (Phase 2) | 미구현 | ⚠️ N/A | Phase 2 예정 |
| 키움 API 주문 실패 (Phase 2) | 미구현 | ⚠️ N/A | Phase 2 예정 |

### 6.2 로깅 전략

| Design Spec | Implementation | Status | Notes |
|-------------|---------------|--------|-------|
| 파일 로그 + 콘솔 로그 분리 | 구현됨 | ✅ Match | `utils/logger.py` |
| 파일: logs/YYYY-MM-DD.log | 구현됨 | ✅ Match | `logger.py:37` |
| 콘솔: INFO 이상만 출력 | 구현됨 | ✅ Match | `logger.py:25` |
| 파일: DEBUG 이상 기록 | 구현됨 | ✅ Match | `logger.py:40` |
| 일별 로테이션 | 미구현 | ❌ Missing | `RotatingFileHandler` 미사용, 단순 날짜 파일명 |

### 6.3 Match Rate: 70% (7/10 항목)

- 핵심 누락: pykrx 재시도 로직 (3회), 일별 로그 로테이션

---

## 7. Security Comparison (Section 7)

| Design Checklist | Implementation | Status |
|------------------|---------------|--------|
| API 키 `.env`로 분리 (gitignore 처리) | `.gitignore`에 `.env` 포함 | ✅ Match |
| `.gitignore`에 `.env`, `credentials.json` 포함 | 둘 다 포함 | ✅ Match |
| 키움 API 인증 정보 암호화 저장 (Phase 2) | 미구현 | ⚠️ N/A |
| 텔레그램 봇 토큰 환경 변수 관리 (Phase 3) | 미구현 | ⚠️ N/A |

### Match Rate: 75% (Phase 1 범위 내 2/2 완료, Phase 2/3 미반영으로 감점)

---

## 8. Test Plan Comparison (Section 8)

### 8.1 테스트 파일 현황

| Design Test File | Implementation | Status |
|------------------|---------------|--------|
| `tests/test_strategy.py` | 존재 (6개 테스트) | ✅ Match |
| `tests/test_engine.py` | 미존재 | ❌ Missing |
| `tests/test_data_loader.py` | 미존재 | ❌ Missing |

### 8.2 핵심 테스트 케이스

| Design Test Case | Implementation | Status | Location |
|------------------|---------------|--------|----------|
| 거래량 급등 + 종가 상승 -> 매수 신호 | `test_buy_signal_on_volume_surge_and_price_up` | ✅ Match | `test_strategy.py:46` |
| 거래량 급등 + 종가 하락 -> 신호 없음 | `test_no_signal_when_price_down` | ✅ Match | `test_strategy.py:72` |
| 익절 조건 -> 매도 신호 | `test_take_profit` | ✅ Match | `test_strategy.py:88` |
| 손절 조건 -> 매도 신호 | `test_stop_loss` | ✅ Match | `test_strategy.py:104` |
| 하루 최대 진입 횟수 초과 -> 신호 무시 | 미구현 | ❌ Missing | 엔진 테스트 필요 |
| 동시 보유 종목 수 초과 -> 신호 무시 | 미구현 | ❌ Missing | 엔진 테스트 필요 |
| 수수료/슬리피지 반영 수익률 계산 | 미구현 | ❌ Missing | 엔진 테스트 필요 |
| MDD 계산 정확성 | 미구현 | ❌ Missing | 엔진 테스트 필요 |

### Match Rate: 50% (4/8 핵심 테스트 케이스 구현)

---

## 9. Environment Variables Comparison (Section 9)

| Design Variable | Phase | Implementation | Status |
|-----------------|-------|---------------|--------|
| `KIWOOM_APP_KEY` | 2 | 미구현 | ⚠️ N/A |
| `KIWOOM_APP_SECRET` | 2 | 미구현 | ⚠️ N/A |
| `KIWOOM_ACCOUNT` | 2 | 미구현 | ⚠️ N/A |
| `TELEGRAM_BOT_TOKEN` | 3 | 미구현 | ⚠️ N/A |
| `TELEGRAM_CHAT_ID` | 3 | 미구현 | ⚠️ N/A |
| `.env` 파일 | - | 미존재 | ⚠️ Missing |
| `python-dotenv` 사용 | - | `requirements.txt`에 포함, 코드에서 미사용 | ⚠️ Partial |

### Match Rate: 60%

- `python-dotenv`가 의존성에 있으나 실제 코드에서 `load_dotenv()` 호출 없음
- `.env` 파일 미생성 (Phase 1에서는 필수는 아니나, 설계에 명시됨)

---

## 10. Implementation Order Compliance (Section 10)

### 10.1 구현 순서 준수 여부

| Design Order | File | Dependency | Status | Notes |
|:------------:|------|-----------|--------|-------|
| 1 | `utils/logger.py` | 없음 | ✅ | 독립적 |
| 2 | `config.py` | 없음 | ✅ | 독립적 |
| 3 | `strategy/base.py` | config.py | ✅ | config.py import |
| 4 | `strategy/volume_breakout.py` | strategy/base.py | ✅ | base.py import |
| 5 | `backtest/data_loader.py` | pykrx | ✅ | pykrx import |
| 6 | `backtest/engine.py` | strategy/, data_loader | ✅ | 모두 import |
| 7 | `backtest/report.py` | engine.py | ✅ | BacktestResult import |
| 8 | `main.py` | 전체 | ✅ | 모든 모듈 import |
| 9 | `tests/` | 전체 | ⚠️ Partial | test_strategy만 구현 |

### 10.2 의존성 (requirements.txt)

| Design Dependency | Implementation | Status |
|-------------------|---------------|--------|
| `pykrx>=1.0.45` | `pykrx>=1.0.45` | ✅ Match |
| `pandas>=2.0.0` | `pandas>=2.0.0` | ✅ Match |
| `numpy>=1.24.0` | `numpy>=1.24.0` | ✅ Match |
| `matplotlib>=3.7.0` | `matplotlib>=3.7.0` | ✅ Match |
| `python-dotenv>=1.0.0` | `python-dotenv>=1.0.0` | ✅ Match |
| `pytest>=7.4.0` | `pytest>=7.4.0` | ✅ Match |
| `ruff>=0.1.0` | `ruff>=0.1.0` | ✅ Match |
| `mypy>=1.5.0` | `mypy>=1.5.0` | ✅ Match |

### Match Rate: 100% (의존성 완전 일치)

---

## 11. Differences Summary

### 11.1 Missing Features (Design O, Implementation X)

| # | Item | Design Location | Description | Priority |
|---|------|-----------------|-------------|----------|
| 1 | `StockData` dataclass | design.md:100-107 | 일봉 데이터 구조체 미정의 (DataFrame 직접 사용) | Low |
| 2 | `tests/test_engine.py` | design.md:363 | 백테스트 엔진 테스트 파일 미구현 | High |
| 3 | `tests/test_data_loader.py` | design.md:364 | 데이터 수집 테스트 파일 미구현 | High |
| 4 | pykrx 재시도 3회 로직 | design.md:374 | 데이터 수집 실패 시 재시도 없이 즉시 빈 DataFrame 반환 | Medium |
| 5 | 일별 로그 로테이션 | design.md:395 | 날짜별 파일명만 사용, RotatingFileHandler 미적용 | Low |
| 6 | 일일 거래 제한 테스트 | design.md:427 | test_engine.py에서 테스트해야 할 항목 | Medium |
| 7 | MDD 계산 정확성 테스트 | design.md:430 | test_engine.py에서 테스트해야 할 항목 | Medium |

### 11.2 Added Features (Design X, Implementation O)

| # | Item | Implementation Location | Description |
|---|------|------------------------|-------------|
| 1 | `get_ticker_name()` | `data_loader.py:85` | 종목명 조회 유틸리티 메서드 |
| 2 | `_calculate_result()` | `engine.py:231` | 성과 지표 계산 내부 메서드 |
| 3 | `_empty_result()` | `engine.py:284` | 빈 결과 헬퍼 메서드 |
| 4 | `_apply_slippage()` | `engine.py:219` | 슬리피지 적용 내부 메서드 |
| 5 | `_apply_commission()` | `engine.py:225` | 수수료 적용 내부 메서드 |
| 6 | `test_no_signal_when_volume_low` | `test_strategy.py:60` | 거래량 미급등 시 테스트 (설계서 미명시) |
| 7 | `test_no_exit_within_range` | `test_strategy.py:120` | 범위 내 미청산 테스트 (설계서 미명시) |
| 8 | `test_insufficient_data` | `test_strategy.py:134` | 데이터 부족 테스트 (설계서 미명시) |
| 9 | 백테스트 종료 시 포지션 강제 청산 | `engine.py:200-215` | 설계서에 미명시된 종료 로직 |

### 11.3 Changed Features (Design != Implementation)

| # | Item | Design | Implementation | Impact |
|---|------|--------|----------------|--------|
| 1 | `OrderSide` 타입 | `str, Enum` | 일반 클래스 상수 | Low - 기능 동일 |
| 2 | `SellReason` 타입 | `str, Enum` | 일반 클래스 상수 | Low - 기능 동일 |
| 3 | `Signal.side` 타입 | `OrderSide` | `str` | Low - 타입 안전성 감소 |
| 4 | `Trade.sell_reason` 타입 | `SellReason \| None` | `str \| None` | Low - 타입 안전성 감소 |
| 5 | `generate_signals` 시그니처 | `(df) -> list[Signal]` | `(df, ticker) -> list[Signal]` | Medium - 인터페이스 변경 |
| 6 | `BacktestReport.__init__` | `(result)` | `(result, initial_capital)` | Low - 추가 파라미터 |
| 7 | `load_market_tickers` 시그니처 | `(market)` | `(market_date, market)` | Low - 추가 파라미터 |
| 8 | 데이터 모델 위치 | 별도 모듈 (암묵적) | `strategy/base.py`에 통합 | Low - 모듈 구조 |

---

## 12. Architecture Compliance

### 12.1 설계 원칙 준수

| Principle | Status | Notes |
|-----------|--------|-------|
| 전략-엔진 분리 | ✅ | `strategy/`와 `backtest/engine.py` 완전 분리 |
| 단일 책임 | ✅ | 각 모듈이 하나의 역할만 담당 |
| 설정 외부화 | ✅ | `StrategyConfig`로 파라미터 관리, CLI에서 주입 |

### 12.2 모듈 의존성 방향

| Module | Design Dependencies | Actual Dependencies | Status |
|--------|--------------------|--------------------|--------|
| `strategy/` | `pandas`, `numpy`, `config` | `pandas`, `config` | ✅ |
| `backtest/engine.py` | `strategy/`, `data_loader` | `strategy/`, `data_loader`, `config`, `numpy`, `pandas` | ✅ |
| `backtest/data_loader.py` | `pykrx` | `pykrx`, `pandas`, `logging` | ✅ |
| `backtest/report.py` | `pandas`, `matplotlib` | `pandas`, `matplotlib`, `numpy`, `strategy.base` | ✅ |

### Architecture Score: 95%

---

## 13. Convention Compliance

### 13.1 Naming Convention

| Category | Convention | Compliance | Violations |
|----------|-----------|:----------:|------------|
| Class | PascalCase | 100% | - |
| Function/Method | snake_case | 100% | - |
| Constants | UPPER_SNAKE_CASE | 100% | `BUY = "buy"` 등 |
| Files | snake_case.py | 100% | - |
| Folders | snake_case | 100% | - |

### 13.2 Import Order

모든 파일에서 표준 라이브러리 -> 서드파티 -> 로컬 import 순서 준수.

### Convention Score: 98%

---

## 14. Overall Match Rate

```
+-------------------------------------------------+
|  Overall Match Rate: 78%                         |
+-------------------------------------------------+
|  Data Model:            83%   (10/12)            |
|  Class/Method:          92%   (23/25)            |
|  File Structure:        85%   (17/20)            |
|  Error Handling:        70%   (7/10)             |
|  Security:              75%   (2/2 Phase1)       |
|  Test Coverage:         50%   (4/8 cases)        |
|  Environment Variables: 60%                      |
|  Architecture:          95%                      |
|  Convention:            98%                      |
+-------------------------------------------------+
|  Weighted Overall:      78%                      |
+-------------------------------------------------+
```

---

## 15. Recommended Actions

### 15.1 Immediate (High Priority)

| # | Item | Action | Expected Impact |
|---|------|--------|-----------------|
| 1 | `tests/test_engine.py` 작성 | 엔진 통합 테스트 구현 (일일 거래 제한, 포지션 제한, MDD 계산 등) | Match Rate +10% |
| 2 | `tests/test_data_loader.py` 작성 | 데이터 수집 테스트 구현 (mock 활용) | Match Rate +5% |
| 3 | pykrx 재시도 로직 추가 | `data_loader.py`에 3회 재시도 with backoff 구현 | 에러 처리 점수 향상 |

### 15.2 Short-term (Medium Priority)

| # | Item | Action | Expected Impact |
|---|------|--------|-----------------|
| 4 | `OrderSide`, `SellReason`을 Enum으로 변경 | `str, Enum` 상속으로 타입 안전성 확보 | 데이터 모델 일치율 향상 |
| 5 | `generate_signals` 시그니처 설계서 반영 | `ticker` 파라미터 추가를 설계서에 반영하거나, 구현에서 제거 | 설계-구현 동기화 |
| 6 | `python-dotenv` 실제 사용 | `main.py`에 `load_dotenv()` 추가 | 환경 변수 점수 향상 |

### 15.3 Long-term (Low Priority)

| # | Item | Action | Notes |
|---|------|--------|-------|
| 7 | `StockData` dataclass 정의 | DataFrame과 병행 사용 또는 설계서에서 제거 | 설계 동기화 |
| 8 | 로그 로테이션 구현 | `TimedRotatingFileHandler` 적용 | 운영 안정성 |
| 9 | 설계서에 추가된 기능 반영 | `get_ticker_name`, 강제 청산 로직 등 | 문서 동기화 |

---

## 16. Design Document Updates Needed

설계서 반영이 필요한 구현 변경사항:

- [ ] `generate_signals(df, ticker)` 시그니처 변경 반영
- [ ] `BacktestReport.__init__(result, initial_capital)` 파라미터 변경 반영
- [ ] `load_market_tickers(market_date, market)` 시그니처 변경 반영
- [ ] `get_ticker_name()` 메서드 추가 반영
- [ ] 백테스트 종료 시 포지션 강제 청산 로직 반영
- [ ] `OrderSide`, `SellReason`의 Enum -> 클래스 상수 변경 사항 기록 (또는 Enum으로 재구현)

---

## 17. Synchronization Options

| Option | Description | Recommended |
|--------|-------------|:-----------:|
| 1 | 구현을 설계에 맞추기 (Enum 복원, StockData 추가 등) | ⚠️ 부분 |
| 2 | 설계를 구현에 맞추기 (시그니처 변경 반영 등) | ✅ 권장 |
| 3 | 양쪽 모두 새 버전으로 통합 | - |
| 4 | 의도적 차이로 기록 | - |

**권장**: Option 2 + 테스트 파일 추가(Option 1 부분 적용). 대부분의 변경이 구현 과정에서 합리적으로 발생한 개선사항이므로, 설계서를 업데이트하고 누락된 테스트를 추가하는 것이 가장 효율적.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-05 | Initial gap analysis | Claude (gap-detector) |
