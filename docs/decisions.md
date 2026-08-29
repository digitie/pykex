# decisions.md — 의사결정 기록

이 문서는 이 프로젝트의 구조적 결정을 결정 시점 순서로 누적한다.
결정이 뒤집힐 때는 새 항목을 추가하고, 옛 항목은 지우지 않은 채
(supersedes: 위 항목)으로 표시한다.

## D-001: `strict_no_data`로 `NO_DATA` 처리 방식을 선택하게 한다

- 상태: accepted
- 날짜: 2026-04-30

### 컨텍스트

`data.ex.co.kr`/`data.go.kr`는 조회 결과가 없을 때도 HTTP 200을 반환하고, envelope 안에서만
`NO_DATA`류 코드를 알려준다. 이를 빈 결과로 조용히 넘기면 파라미터 오류나 실제 데이터
없음을 구분하지 못하는 호출부가 생기고, 반대로 항상 예외로 던지면 "결과가 없을 수 있음"을
전제로 순회하는 배치 코드가 매 호출을 `try/except`로 감싸야 한다.

### 결정

`KrexClient(strict_no_data=True)`를 기본값으로 하여 `NO_DATA`를 `KrexNotFoundError`로 던진다.
`strict_no_data=False`로 생성한 클라이언트는 같은 상황에서 예외 대신 빈 `Page`를 반환한다.
이 분기는 `KrexClient._page_ex`/`_page_go`와 비동기 버전 `_apage_ex`/`_apage_go`에 동일하게
구현되어 있다(`src/krex/client.py`).

### 근거

기본값을 엄격하게 두면 새 endpoint를 추가할 때 파라미터 실수를 "빈 리스트"로 착각해
넘어가는 실수를 막을 수 있다. 반면 최근 N일 조회처럼 데이터가 없는 구간이 정상적으로
존재하는 호출부는 명시적으로 `strict_no_data=False`를 선택해 예외 처리 없이 순회할 수
있다. 기본값과 옵트아웃을 분리하면 두 사용 패턴을 모두 깨끗하게 지원한다.

### 결과

`AGENTS.md`의 DO-NOT 목록에 "`NO_DATA`는 기본적으로 `KrexNotFoundError`"라는 규칙으로
반영되어 있다. 새 namespace를 추가할 때도 이 두 helper를 통해서만 페이지를 만들어야
일관성이 유지된다.

## D-002: `KrexClient`를 동기 우선으로 두고 `AsyncKrexClient`는 `asyncio.to_thread` 파사드로 감싼다

- 상태: accepted
- 날짜: 2026-05-19

### 컨텍스트

httpx는 동기/비동기 클라이언트를 모두 제공하지만, 두 구현을 처음부터 각각 손으로
관리하면 namespace 메서드(`traffic.flow()` 등)가 늘어날 때마다 동기/비동기 버전을 매번
같이 작성하고 테스트해야 한다. 반대로 비동기만 제공하면 스크립트/배치 코드에서 매번
`asyncio.run()`을 강제하게 된다.

### 결정

`KrexClient`(동기)를 유일한 실제 구현으로 유지하고, `KrexClient.aio()`가 반환하는
`AsyncKrexClient`는 각 namespace를 `_AsyncServiceProxy`로 감싸 모든 호출을
`asyncio.to_thread(sync_method, *args, **kwargs)`로 위임한다(`src/krex/client.py`).
HTTP 계층(`KrexHttp`)만 `get_ex`/`aget_ex`처럼 진짜 동기/비동기 구현을 각각 갖는다.

### 근거

Namespace 메서드 자체(파라미터 정리, enum 변환, 모델 파싱)는 동기든 비동기든 로직이
같으므로 이중 구현할 이유가 없다. `asyncio.to_thread` 파사드를 쓰면 새 endpoint를
`KrexClient`에만 추가해도 `AsyncKrexClient`에서 자동으로 `await` 가능해지고, 두 진입점의
동작이 갈라질 여지가 줄어든다.

### 결과

README의 대표 사용 예제는 `KrexClient.aio()` 기반 `async def main()`이고, 동기 사용법은
보조 예제로 제공한다. 새 endpoint를 추가할 때 별도의 async 메서드를 작성할 필요는 없다.

## D-003: `traffic.incident()`를 존재하지 않는 경로에서 실시간 문자정보 API로 repoint한다

- 상태: accepted
- 날짜: 2026-06-11

### 컨텍스트

`traffic.incident()`는 원래 `/openapi/trafficapi/incident`를 호출했지만, live 검증 결과
이 경로는 항상 404를 반환해 실제로 존재하지 않는 endpoint였다. 사고 정보 자체는
`data.ex.co.kr`가 실시간 문자정보(apiId 0611) `/openapi/burstInfo/realTimeSms`로만
제공하고 있었다.

### 결정

`traffic.incident()`가 `/openapi/burstInfo/realTimeSms`를 호출하도록 repoint하고,
파라미터를 `acc_type_code` 선택값으로 교체했다. `Incident` 모델 필드도 live 응답 shape
(`accDate`, `accHour`, `accType`, `smsText`, `startEndTypeCode`, 위경도 등)에 맞춰
재정렬했다. 이 포털의 응답에서 경도는 `lon`이 아니라 `altitude` 키로 오므로, 파싱 시
이를 명시적으로 처리한다. 목록은 `realTimeSMSList` 키에서 추출한다.

### 근거

존재하지 않는 경로를 계속 노출하면 모든 호출이 항상 실패하는 죽은 기능을 유지하는
셈이다. 실측 가능한 대체 endpoint로 옮기는 편이 "미구현으로 명시"보다 사용자에게
유용하고, `API_COVERAGE.md`의 live 검증 원칙(실제 provider 호출로 확인된 것만 "Live
검증됨"으로 표시)과도 맞는다.

### 결과

`API_COVERAGE.md`에 2026-06-11 live 검증(count=190)으로 기록되어 있다. `altitude` 키
매핑과 `realTimeSMSList` 추출은 회귀 테스트와 `tests/fixtures/`의 fixture로 고정되어
있으므로, 포털이 필드명을 다시 바꾸지 않는 한 이 매핑을 그대로 유지한다.
