# Error Codes Reference

API 호출 시 만날 수 있는 모든 에러 코드와 라이브러리 예외 매핑.

## 목차

- [예외 계층 구조](#예외-계층-구조)
- [data.ex.co.kr 에러 코드](#dataexcokr-에러-코드)
- [data.go.kr 에러 코드](#datagokr-에러-코드)
- [HTTP 상태 코드](#http-상태-코드)
- [네트워크 에러](#네트워크-에러)
- [라이브러리 자체 에러](#라이브러리-자체-에러)
- [에러별 디버깅 가이드](#에러별-디버깅-가이드)

---

## 예외 계층 구조

```
KrexError                          # 모든 라이브러리 예외의 부모
├── KrexAuthError                  # 인증 관련 (키 무효/만료/미등록)
├── KrexQuotaExceededError         # 호출 한도 초과
├── KrexBadRequestError            # 파라미터 누락/오류
│   ├── KrexMissingParameterError  # 필수 파라미터 누락
│   └── KrexInvalidParameterError  # 파라미터 값 오류
├── KrexNotFoundError              # 데이터 없음
├── KrexServerError                # 5xx 서버 오류
│   └── KrexServiceUnavailableError # 일시적 서비스 중단
├── KrexParseError                 # 응답 파싱 실패
│   ├── KrexXMLParseError
│   └── KrexJSONParseError
├── KrexNetworkError               # 네트워크 연결 문제
│   ├── KrexTimeoutError
│   └── KrexConnectionError
└── KrexConfigError                # 클라이언트 설정 오류
```

모든 예외는 다음 속성을 가집니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `.code` | `str` | 원본 에러 코드 (제공자 발신) |
| `.message` | `str` | 사람이 읽을 수 있는 설명 |
| `.response` | `dict / None` | 원본 응답 본문 (가능한 경우) |
| `.url` | `str / None` | 호출한 URL (인증키 마스킹 처리) |
| `.params` | `dict / None` | 전달한 파라미터 |
| `.http_status` | `int / None` | HTTP 상태 코드 |
| `.retry_after` | `int / None` | 재시도 권장 대기 시간(초) |

---

## data.ex.co.kr 에러 코드

응답 본문의 `code` 필드 값입니다.

| 코드 | 메시지 (예시) | 라이브러리 예외 | 재시도? |
|------|--------------|----------------|---------|
| `SUCCESS` | 인증키가 유효합니다. | (정상) | — |
| `INVALID_KEY` | 등록되지 않은 인증키입니다. | `KrexAuthError` | ❌ |
| `EXPIRED_KEY` | 만료된 인증키입니다. | `KrexAuthError` | ❌ |
| `NO_REGISTERED_KEY` | 등록되지 않은 인증키입니다. | `KrexAuthError` | ❌ |
| `EXCEEDED_LIMIT` | 일일 호출 한도를 초과하였습니다. | `KrexQuotaExceededError` | ⏳ (다음 날) |
| `INVALID_REQUEST_PARAMETER` | 필수 파라미터가 누락되었습니다. | `KrexBadRequestError` | ❌ |
| `INVALID_PARAMETER_VALUE` | 파라미터 값이 올바르지 않습니다. | `KrexInvalidParameterError` | ❌ |
| `NO_DATA` | 조회된 데이터가 없습니다. | `KrexNotFoundError` *([주의](#no_data-주의)) | ❌ |
| `SYSTEM_ERROR` | 시스템 오류가 발생하였습니다. | `KrexServerError` | ✅ (자동) |
| `SERVICE_TIMEOUT` | 응답 시간이 초과되었습니다. | `KrexServiceUnavailableError` | ✅ (자동) |
| `SERVICE_UNAVAILABLE` | 일시적으로 서비스를 이용할 수 없습니다. | `KrexServiceUnavailableError` | ✅ (자동) |

### `NO_DATA` 주의

`NO_DATA`는 기본적으로 예외로 변환되지만, 옵션으로 빈 결과를 허용할 수 있습니다.

```python
client = KrexClient(empty_as_none=True)   # NO_DATA → 빈 list 반환
# 또는 호출 단위로
res = client.traffic.by_ic(unit_code="999", on_no_data="empty")
```

기본값(`raise_on_no_data=True`)은 누락 데이터를 silent fail로 만들지 않기 위함입니다.

---

## data.go.kr 에러 코드

`response.header.resultCode` (XML/JSON 공통). 2자리 숫자 형식.

### 정상

| 코드 | 메시지 | 라이브러리 동작 |
|------|--------|----------------|
| `00` | NORMAL SERVICE | 정상 처리 |

### 애플리케이션 에러 (00번대)

| 코드 | 메시지 | 라이브러리 예외 |
|------|--------|----------------|
| `01` | APPLICATION ERROR | `KrexServerError` |
| `02` | DB ERROR | `KrexServerError` |
| `03` | NODATA_ERROR | `KrexNotFoundError` |
| `04` | HTTP ERROR | `KrexServerError` |
| `05` | SERVICE TIMEOUT | `KrexServiceUnavailableError` |

### 요청 파라미터 에러 (10번대)

| 코드 | 메시지 | 라이브러리 예외 |
|------|--------|----------------|
| `10` | INVALID REQUEST PARAMETER ERROR | `KrexInvalidParameterError` |
| `11` | NO MANDATORY REQUEST PARAMETERS ERROR | `KrexMissingParameterError` |
| `12` | NO OPENAPI SERVICE ERROR | `KrexBadRequestError` |

### 서비스 권한/한도 에러 (20번대)

| 코드 | 메시지 | 라이브러리 예외 |
|------|--------|----------------|
| `20` | SERVICE ACCESS DENIED ERROR | `KrexAuthError` |
| `21` | TEMPORARILY DISABLE THE SERVICEKEY ERROR | `KrexAuthError` |
| `22` | LIMITED NUMBER OF SERVICE REQUESTS EXCEEDS ERROR | `KrexQuotaExceededError` |

### 인증키 에러 (30번대)

| 코드 | 메시지 | 라이브러리 예외 |
|------|--------|----------------|
| `30` | SERVICE KEY IS NOT REGISTERED ERROR | `KrexAuthError` |
| `31` | DEADLINE HAS EXPIRED ERROR | `KrexAuthError` |
| `32` | UNREGISTERED IP ERROR | `KrexAuthError` |
| `33` | UNSIGNED CALL ERROR | `KrexAuthError` |

### 기타 (99)

| 코드 | 메시지 | 라이브러리 예외 |
|------|--------|----------------|
| `99` | UNKNOWN ERROR | `KrexError` |

> **함정**: data.go.kr는 위 에러 상황에서도 **HTTP 200 OK**를 반환합니다.
> HTTP 상태 코드만 보고 성공으로 판단하지 마세요. 본문의 `resultCode`를 반드시 확인.

---

## HTTP 상태 코드

전송 계층 또는 게이트웨이 단계에서 발생.

| 상태 코드 | 의미 | 라이브러리 동작 |
|-----------|------|----------------|
| `200 OK` | 성공 (단, 본문에 에러 코드 가능) | 본문 검사 후 분기 |
| `400 Bad Request` | 잘못된 요청 (URL/헤더 단계) | `KrexBadRequestError` |
| `401 Unauthorized` | 인증 실패 | `KrexAuthError` |
| `403 Forbidden` | 접근 권한 없음 | `KrexAuthError` |
| `404 Not Found` | 엔드포인트 없음 | `KrexBadRequestError` *(경로 오류일 가능성 높음)* |
| `429 Too Many Requests` | 레이트 리밋 | `KrexQuotaExceededError` |
| `500 Internal Server Error` | 서버 오류 | `KrexServerError` (재시도) |
| `502 Bad Gateway` | 게이트웨이 오류 | `KrexServerError` (재시도) |
| `503 Service Unavailable` | 서비스 중단 | `KrexServiceUnavailableError` (재시도) |
| `504 Gateway Timeout` | 게이트웨이 타임아웃 | `KrexTimeoutError` (재시도) |

### 자동 재시도 정책

기본 설정으로 다음을 자동 재시도합니다.

- `500`, `502`, `503`, `504` HTTP 상태
- `SYSTEM_ERROR`, `SERVICE_TIMEOUT`, `SERVICE_UNAVAILABLE` 코드
- 연결 타임아웃 / 읽기 타임아웃

```python
# 재시도 비활성화
client = KrexClient(max_retries=0)

# 더 적극적인 재시도
client = KrexClient(max_retries=5, backoff_factor=1.0)
# 백오프: 1s, 2s, 4s, 8s, 16s
```

---

## 네트워크 에러

라이브러리가 직접 발생시키는 네트워크 계층 예외.

| 예외 | 발생 조건 |
|------|-----------|
| `KrexTimeoutError` | 연결/읽기 타임아웃. 기본 30초 |
| `KrexConnectionError` | DNS 실패, 호스트 거부, TLS 실패 |
| `KrexNetworkError` | 위 둘의 부모. 분기 처리에 사용 |

```python
from krex.exceptions import KrexNetworkError

try:
    client.traffic.flow()
except KrexNetworkError as e:
    log.warning(f"일시적 네트워크 문제: {e}")
    # 큐에 다시 넣어 나중에 처리
```

---

## 라이브러리 자체 에러

API 응답과 무관하게 라이브러리 사용 중 발생.

| 예외 | 발생 조건 |
|------|-----------|
| `KrexConfigError` | API 키 미설정, 잘못된 클라이언트 옵션 |
| `KrexParseError` | 응답이 예상한 XML/JSON 구조가 아님 |
| `KrexXMLParseError` | XML 파싱 실패 (응답이 HTML 에러 페이지였던 경우 흔함) |
| `KrexJSONParseError` | JSON 파싱 실패 |

`KrexParseError`는 응답이 HTML(에러 페이지)이거나 빈 본문일 때뿐 아니라, HTTP 200
JSON이 endpoint의 필수 envelope를 충족하지 않을 때도 발생한다. 예를 들어
`traffic.incident()`는 `realTimeSMSList`와 0 이상인 `count`가 모두 있어야 빈 목록을
정상 snapshot으로 인정한다. 가능한 경우 `e.response`에서 원본 응답을 확인한다.

---

## 에러별 디버깅 가이드

### "INVALID_KEY" / "30 SERVICE_KEY_IS_NOT_REGISTERED_ERROR"

**원인**

1. 인증키 오타/잘림
2. data.go.kr에서 키를 인코딩된 형태로 사용
3. 활용신청 후 즉시 호출 (data.go.kr는 약 1~2시간 후 활성화)
4. 잘못된 포털의 키 사용 (data.ex.co.kr 키를 data.go.kr에 사용 등)

**조치**

```python
# 1) 키 출력하여 확인 (앞뒤 공백 점검)
print(repr(os.getenv("DATA_GO_KR_SERVICE_KEY")))

# 2) 인코딩된 키를 디코딩
from urllib.parse import unquote
key = unquote(encoded_key)

# 3) 활용신청 후 1-2시간 대기
```

---

### "EXCEEDED_LIMIT" / "22 LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"

**원인**

- 일일 호출 한도 초과 (개발계정: 1,000회/일이 일반적)
- 운영계정도 무제한이 아님

**조치**

1. 호출 빈도 점검 — 캐싱 활용
   ```python
   client = KrexClient(cache=True, cache_ttl=300)  # 5분 캐싱
   ```
2. 실시간 데이터는 5분 미만 폴링 무의미 (원본 갱신 주기가 5분)
3. 운영계정 신청
4. 한도 추적 활성화
   ```python
   client = KrexClient(rate_limit_per_day=1000, rate_limit_strict=True)
   # 한도 도달 시 KrexQuotaExceededError를 사전에 발생
   ```

---

### "INVALID_REQUEST_PARAMETER" / 10번대 에러

**원인**

- 필수 파라미터 누락
- 코드값 오타 (예: `carType=10`)
- 날짜 형식 오류 (`stdDate=2024-01-01` ← 하이픈 X, `20240101` ✓)

**조치**

```python
# enum 사용으로 매직넘버 제거
client.traffic.by_ic(car_type=CarType.LIGHT)  # ✓
client.traffic.by_ic(car_type="A")            # ✗ KrexInvalidParameterError

# 디버그 로깅으로 실제 전송된 파라미터 확인
import logging
logging.getLogger("krex").setLevel(logging.DEBUG)
```

---

### "NO_DATA" / "03 NODATA_ERROR"

**원인**

- 조건에 맞는 데이터가 실제로 없음
- 영업소 코드/노선 코드가 폐지됨
- 조회 범위 시점에 데이터 미수집

**조치**

```python
from krex.exceptions import KrexNotFoundError

try:
    res = client.traffic.by_ic(unit_code="101", std_date="20200101")
except KrexNotFoundError:
    print("해당 일자 데이터 없음")

# 또는 빈 결과로 받기
res = client.traffic.by_ic(unit_code="101", on_no_data="empty")
if not res.items:
    print("데이터 없음")
```

---

### `KrexParseError` (응답이 HTML)

**증상**

```
KrexXMLParseError: not well-formed (invalid token): line 1, column 0
e.raw_body[:200] == "<!DOCTYPE html><html>...에러 페이지..."
```

**원인 후보**

1. 엔드포인트 경로 오타 → 포털 메인의 404 페이지가 반환됨
2. 인증 실패 → 로그인 페이지로 리다이렉트
3. 포털 점검 중 → 점검 안내 HTML

**조치**

```python
# 마지막 호출 정보 검사
print(client.last_request_url)
print(client.last_response.status_code)
print(client.last_response.text[:500])

# 브라우저로 동일 URL 열어서 확인
```

---

## 에러 처리 권장 패턴

### 광범위 캐치는 피하라

```python
# ❌ 나쁜 예
try:
    res = client.traffic.flow()
except Exception as e:
    print("에러")  # 정보 손실, 디버깅 불가

# ✅ 좋은 예
try:
    res = client.traffic.flow()
except KrexAuthError:
    raise   # 설정 문제. 호출자에게 전파
except KrexQuotaExceededError as e:
    schedule_retry_at(e.retry_after or 86400)
except KrexServerError:
    schedule_retry_at(60)   # 1분 뒤 재시도
except KrexNotFoundError:
    return []   # 빈 결과로 처리
```

### 컨텍스트 매니저로 자원 정리

```python
with AsyncKrexClient() as client:
    try:
        res = await client.traffic.flow()
    except KrexError as e:
        log.error(f"호출 실패: code={e.code}, msg={e.message}")
        raise
```

### 재시도 가능 여부를 예외에서 판단

```python
def with_retry(func, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return func()
        except KrexError as e:
            if not e.is_retryable or attempt == max_attempts - 1:
                raise
            time.sleep(e.retry_after or (2 ** attempt))
```

`is_retryable`은 `KrexServerError`, `KrexNetworkError`, `KrexQuotaExceededError`에서
`True`이며 그 외에는 `False`입니다.
