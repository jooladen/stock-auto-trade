# Stock Auto Trade - 개발 워크플로우

## 응답 규칙
- 항상 대답은 한글로 한다

## 기술 스택
- **언어**: Python 3.10+
- **패키지 매니저**: pip (`pip install -r requirements.txt`)
- **가상환경**: venv (`python -m venv venv`)

## 개발 명령어
1. 의존성 설치: `pip install -r requirements-dev.txt`
2. 애플리케이션 실행: `python main.py`
3. 테스트 실행: `pytest`
4. 린트 검사: `ruff check .`
5. 코드 포맷팅: `ruff format .`
6. 타입 체크: `mypy .`

## 프로젝트 구조
```
stock-auto-trade/
  main.py              # 진입점
  config.py            # 설정 (API 키, 환경설정)
  requirements.txt     # 의존성 목록
  tests/               # 테스트 파일
```

## 코딩 컨벤션
- 모든 함수 시그니처에 타입 힌트 사용
- 함수/변수는 `snake_case`, 클래스는 `PascalCase` 사용
- 데이터 구조는 `dataclass` 또는 `pydantic.BaseModel` 사용 권장
- 출력은 `print()` 대신 `logging` 모듈 사용
- 경로 처리는 `os.path` 대신 `pathlib.Path` 사용
- 코드 스니펫 대신 `파일:라인번호` 참조 방식 사용

## 보안 규칙
- 소스 코드에 API 키나 시크릿을 절대 하드코딩하지 않는다
- 인증 정보는 `.env` 파일에 저장 (gitignore 처리)
- 설정값은 `python-dotenv` 또는 환경 변수로 관리
- `.env`, `credentials.json` 등 비밀 정보가 담긴 파일은 절대 커밋하지 않는다

## 금지 사항
- 로깅에 `print()` 사용 금지 (`logging` 모듈 사용)
- `*` 임포트 금지 (명시적 임포트 사용)
- 함수 시그니처에 가변 기본 인자 사용 금지
- `any` 타입 사용 금지

## 테스트 작성 규칙 (Do 단계 체크리스트)
- assertion은 구체적 값으로 검증 (`>= 0`, `is not None` 같은 약한 assertion 금지)
- mock 데이터는 최소 20행 이상 사용 (실제 전략이 동작할 수 있는 충분한 길이)
- 구현 완료 후 `python main.py`로 실제 데이터 1회 실행하여 동작 확인
