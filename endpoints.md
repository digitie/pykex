# Endpoints Reference

엔드포인트별 파라미터, 응답 스키마, 호출 예시 모음.
라이브러리 메서드와 원본 OpenAPI 사이의 1:1 매핑을 담고 있습니다.

> **표기 규약**
> - **R** = Required (필수), **O** = Optional (선택)
> - 데이터 타입: `str`(문자열), `int`(정수), `code`(코드값, [codes.md](codes.md) 참조)
> - 모든 엔드포인트는 HTTP **GET**

## 목차

- [공통 사항](#공통-사항)
- [교통 (Traffic)](#교통-traffic)
  - [영업소별 교통량 (`traffic.by_ic`)](#영업소별-교통량)
  - [노선별 교통량 (`traffic.by_route`)](#노선별-교통량)
  - [실시간 소통 (`traffic.flow`)](#실시간-소통)
  - [실시간 문자정보/돌발 (`traffic.incident`)](#실시간-문자정보돌발)
  - [VDS 원시자료 (`traffic.vds_raw`)](#vds-원시자료)
  - [AVC 원시자료 (`traffic.avc_raw`)](#avc-원시자료)
- [통행료 (Tollfee)](#통행료-tollfee)
  - [영업소간 통행요금 (`tollfee.between_tollgates`)](#영업소간-통행요금)
  - [영업소 목록 (`tollfee.tollgate_list`)](#영업소-목록)
- [휴게소 (Restarea)](#휴게소-restarea)
  - [노선별 휴게시설 현황 (`restarea.route_facilities`)](#노선별-휴게시설-현황)
  - [전국 휴게소 정보 (`restarea.list_all`)](#전국-휴게소-정보)
  - [휴게소별 날씨 (`restarea.weather`)](#휴게소별-날씨)
  - [주유소별 가격·업체 현황 (`restarea.fuel_prices`)](#주유소별-가격업체-현황)
  - [노선별·방향별 휴게소 편의시설 현황 (`restarea.convenience_facilities`)](#노선별방향별-휴게소-편의시설-현황)
  - [휴게소 음식가격 (`restarea.food_price`)](#휴게소-음식가격)
  - [주차장/Wi-Fi/화장실 시설 정보](#휴게소-시설-정보)
- [영업소·시설 (Facility)](#영업소시설-facility)
  - [영업소 위치정보 (`facility.tollgate_info`)](#영업소-위치정보)
  - [졸음쉼터 (`facility.drowsy_shelter`)](#졸음쉼터)
  - [갓길차로제 (`facility.shoulder_lane`)](#갓길차로제)
- [행정·조달 (Admin)](#행정조달-admin)
  - [전자조달 계약공개 (`admin.procurement_contracts`)](#전자조달-계약공개)
- [기준정보 (Reference)](#기준정보-reference)
  - [공통코드 (`reference.common_codes`)](#공통코드)
  - [노선 (`reference.routes`)](#노선)

---

## 공통 사항

### data.ex.co.kr 공통 파라미터

| 파라미터 | 필수 | 타입 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `key` | R | `str` | — | 인증키 (포털에서 발급. URL 인코딩 X) |
| `type` | O | `str` | `xml` | 응답 형식: `xml` / `json` |
| `numOfRows` | O | `int` | `10` | 페이지당 건수 (대부분 최대 1,000) |
| `pageNo` | O | `int` | `1` | 페이지 번호 (1-based) |

### data.go.kr 공통 파라미터

| 파라미터 | 필수 | 타입 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `serviceKey` | R | `str` | — | 인증키 (디코딩된 형태로 전달) |
| `_type` | O | `str` | `xml` | 응답 형식: `xml` / `json` *(언더스코어 주의)* |
| `numOfRows` | O | `int` | `10` | 페이지당 건수 |
| `pageNo` | O | `int` | `1` | 페이지 번호 |

> 신규 "표준데이터" 계열은 `perPage` / `page` 사용. 라이브러리가 자동 변환.

---

## 교통 (Traffic)

### 영업소별 교통량

특정 영업소의 진입/진출 교통량을 시간단위 또는 15분단위로 조회합니다.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/trafficapi/trafficIc`
- **메서드**: `client.traffic.by_ic()`

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `exDivCode` | R | `code` | 도로 운영기관 (`00`=KEC, [codes.md](codes.md#도로-운영기관) 참조) |
| `unitCode` | R | `str` | 영업소 코드 (3자리 숫자) |
| `inOutType` | R | `code` | 진출입 (`0`=진입, `1`=진출) |
| `tmType` | R | `code` | 시간 단위 (`1`=1시간, `2`=15분) |
| `tcsType` | R | `code` | TCS/하이패스 (`1`=TCS, `2`=Hi-Pass) |
| `carType` | R | `code` | 차종 (`1`~`6`) |
| `numOfRows` | O | `int` | 페이지당 건수 |
| `pageNo` | O | `int` | 페이지 번호 |

**응답 필드**

| 필드 (API) | 라이브러리 필드 | 타입 | 설명 |
|-----------|----------------|------|------|
| `stdDate` / `sumDate` | `collected_date` | `date` | 집계 일자 (YYYYMMDD) |
| `stdTime` / `sumTm` | `collected_time` | `str` | 집계 시각 (HH 또는 HHMM) |
| `unitCode` | `unit_code` | `str` | 영업소 코드. 실제 응답에서 공백 suffix가 올 수 있어 strip 처리 |
| `unitName` | `unit_name` | `str` | 영업소명 |
| `inOutType` / `inoutType` | `in_out` | `IOType` | 진출입 |
| `tcsType` | `tcs_type` | `TCSType` | TCS/하이패스 |
| `carType` | `car_type` | `CarType` | 차종 |
| `trafficVol` / `trafficAmout` | `traffic_volume` | `int` | 교통량 (대). 실제 응답 typo `trafficAmout` 확인 |

**실서버 확인 메모**

- 확인일: 2026-05-01
- `data.ex.co.kr` 실제 JSON은 `list`가 아니라 `trafficIc` top-level 배열에 레코드를 담아 반환할 수 있습니다.
- `trafficIc`는 `inOutType=0`으로 요청해도 `inoutType=0`/`1` 레코드를 함께 반환하는 사례가 확인되었습니다. 호출자는 반환값의 `in_out`을 기준으로 다시 필터링할 수 있습니다.

**예시**

```python
res = client.traffic.by_ic(
    ex_div_code="00",
    unit_code="101",       # 서울TG (예시값)
    in_out=IOType.IN,
    time_unit=TimeUnit.HOUR,
    tcs_type=TCSType.HIPASS,
    car_type=CarType.LIGHT,
    num_of_rows=24,        # 24시간치
    page_no=1,
)
print(res.items[0].traffic_volume)
```

---

### 노선별 교통량

노선(고속도로) 단위 교통량 통계.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/trafficapi/trafficRoute`
- **메서드**: `client.traffic.by_route()`

> 실서버 확인(2026-05-01): 유효한 키와 파라미터에서 `{"code":"SUCCESS","count":0,"list":[]}` 형태가 반환될 수 있습니다. 라이브러리는 `total_count=0`으로 보존합니다.

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `routeNo` | R | `code` | 노선번호 (4자리, [codes.md](codes.md#노선-코드) 참조) |
| `tmType` | R | `code` | 시간 단위 |
| `dirType` | O | `code` | 방향 (`0`=상행, `1`=하행) |
| `carType` | O | `code` | 차종 |
| `stdDate` | O | `str` | 조회일 (YYYYMMDD) |

---

### 실시간 소통

도로별 통행속도, 혼잡도(원활/지체/정체) 정보.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/trafficapi/realFlow`
- **공공데이터포털 대응**: 데이터셋 ID `15076684`
- **메서드**: `client.traffic.flow()`

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `routeNo` | O | `code` | 노선번호 (생략 시 전체) |
| `conzoneId` | O | `str` | 콘존 ID (구간 ID) |
| `dirType` | O | `code` | 방향 |

**응답 필드**

| 필드 | 설명 |
|------|------|
| `conzoneId` | 구간 식별자 |
| `conzoneName` | 구간명 (예: "서울→수원") |
| `routeNo` / `routeName` | 노선 번호/명 |
| `speed` | 평균 통행속도 (km/h) |
| `tmFreeFlow` | 자유속도 |
| `congestionLevel` | `1`=원활, `2`=서행, `3`=지체, `4`=정체 |
| `updTime` | 갱신 시각 |

> **갱신 주기**: 5분. 더 빠른 폴링은 같은 데이터를 반환하므로 호출 한도만 소모.

---

### 실시간 문자정보/돌발

고속도로 사고, 공사, 통제 등 돌발 상황의 실시간 문자정보 (apiId 0611).

> 구 경로 `/openapi/trafficapi/incident`는 포털에서 제거되어 항상 HTTP 404를
> 반환한다 (2026-06-11 확인). 현행 경로는 아래와 같다.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/burstInfo/realTimeSms`
- **메서드**: `client.traffic.incident()`
- **snapshot 검증**: 정상 응답의 `realTimeSMSList`와 0 이상인 `count`가 모두
  있어야 한다. 둘 중 하나가 없는 HTTP 200 오류 본문은 빈 목록이 아니라
  `KrexParseError`로 처리하며, `count=0` + `realTimeSMSList=[]`만 명시적 빈
  snapshot으로 인정한다.

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `accTypeCode` | O | `code` | 돌발 유형 코드 (미지정 시 전체) |
| `numOfRows` | O | `int` | 페이지당 건수 |
| `pageNo` | O | `int` | 페이지 번호 |

**응답 필드** (목록 키: `realTimeSMSList`, 전체 건수 키: `count`)

| 키 | 모델 필드 | 설명 |
|------|------|------|
| `accDate` / `accHour` | `occurred_date` / `occurred_time` | 발생일 (`2023.09.27`) / 발생시각 (`09:11:24`) |
| `accType` / `accTypeCode` | `incident_type` / `incident_type_code` | 돌발 유형명 / 코드 |
| `startEndTypeCode` | `direction` | 방향 텍스트 (예: `대구방향`) |
| `smsText` | `message` | 문자정보 본문 |
| `accPointNM` | `point_name` | 발생 지점명 (공백뿐이면 `None`) |
| `nosunNM` / `roadNM` | `route_no` / `route_name` | 노선번호 (`0552`) / 도로명 (`대구부산선`) |
| `accProcessNM` / `accProcessCode` | `process_status` / `process_status_code` | 처리 상태명 / 코드 |
| `latitude` | `latitude` | 돌발시작이정위도 |
| `altitude` | `longitude` | **돌발시작이정경도** — 포털이 경도를 `altitude` 키로 내려준다 |
| `lateLength` | `congestion_length` | 정체길이 |
| `seriesNM` | `series_no` | 일련번호 |

---

### VDS 원시자료

차량검지기(VDS, Vehicle Detection System) 원시 데이터. 5분 단위.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/trafficapi/vdsRaw`
- **메서드**: `client.traffic.vds_raw()`

> **주의**: 데이터 양이 매우 많으므로 시간 범위를 좁혀 조회. 전국 1일치는 수십만 건.

---

### AVC 원시자료

자동차량분류장치(AVC) 원시자료. 차종별·차로별 통과 기록.

- **포털**: `data.ex.co.kr` / `data.go.kr` (ID `15066742`)
- **경로**: `/openapi/trafficapi/avcRaw`
- **메서드**: `client.traffic.avc_raw()`

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `vdsId` | R | `str` | VDS 식별자 |
| `stdDate` | R | `str` | 조회일 (YYYYMMDD) |

---

## 통행료 (Tollfee)

### 영업소간 통행요금

출발지·도착지 영업소 간 통행료, 거리, 소요시간 조회.

- **포털**: `data.ex.co.kr` / `data.go.kr` (ID `15111644`)
- **경로**: `/openapi/tollfee/tollFeeBetweenTcs` (data.ex.co.kr 기준)
- **메서드**: `client.tollfee.between_tollgates()`

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `startUnitCode` | R | `str` | 출발 영업소 코드 |
| `endUnitCode` | R | `str` | 도착 영업소 코드 |
| `carType` | R | `code` | 차종 |
| `discountType` | O | `code` | 할인 유형 (`0`=정상, `1`=심야, `2`=출퇴근, `3`=경차) |

**응답 필드**

| 필드 | 설명 |
|------|------|
| `startUnitCode` / `startUnitName` | 출발 영업소 |
| `endUnitCode` / `endUnitName` | 도착 영업소 |
| `routeCount` | 경로 수 |
| `totalLength` | 총 거리 (km) |
| `travelTime` | 소요시간 (분) |
| `tollFee` | 통행료 (원) |
| `tollFeeNight` | 심야 할인 요금 |
| `tollFeeRush` | 출퇴근 할인 요금 |

---

### 영업소 목록

전국 영업소 코드/명칭 목록. 코드값 동기화 시 사용.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/business/openapibusinessunit`
- **공공데이터포털 대응**: 영업소 위치정보 (ID `15076728`)
- **메서드**: `client.tollfee.tollgate_list()`

**파라미터**: 페이지네이션 파라미터만.

**응답 필드**

| 필드 | 설명 |
|------|------|
| `unitCode` | 영업소 코드 (3자리) |
| `unitName` | 영업소명 |
| `routeNo` / `routeName` | 소속 노선 |
| `exDivCode` | 운영기관 |
| `xValue` / `yValue` | 좌표 (KATEC 또는 WGS84) |
| `headOfficeCode` / `branchOfficeCode` | 본부/지사 코드 |

---

## 휴게소 (Restarea)

### 노선별 휴게시설 현황

휴게소 master성 코드/명칭/노선/방향/전화번호와 일부 대표 시설 여부를 조회한다.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/business/serviceAreaRoute`
- **메서드**: `client.restarea.route_facilities()`

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `routeName` | O | `str` | 노선명 |
| `direction` | O | `str` | 방향 |
| `serviceAreaName` | O | `str` | 휴게소명 |
| `routeCode` | O | `str` | 노선코드 |
| `serviceAreaCode` | O | `str` | 휴게소코드 |

**응답 필드**

| 원본 필드 | 모델 필드 | 타입 | 설명 |
|-----------|-----------|------|------|
| `routeCode` | `route_code` | `str | None` | 노선코드 |
| `serviceAreaCode` | `service_area_code` | `str` | 휴게소코드 |
| `serviceAreaCode2` | `service_area_code2` | `str | None` | 보조 휴게소코드 |
| `routeName` | `route_name` | `str | None` | 노선명 |
| `direction` | `direction` | `str | None` | 방향 |
| `serviceAreaName` | `service_area_name` | `str | None` | 휴게소명. 실제 응답에서 비어 있을 수 있음 |
| `telNo` | `phone_number` | `str | None` | 전화번호 |
| `svarAddr` | `address` | `str | None` | Provider 원문 주소 문자열 |
| `brand` | `brand` | `str | None` | 브랜드 매장 |
| `convenience` | `convenience` | `str | None` | 편의시설 문자열 |
| `maintenanceYn` | `has_maintenance` | `bool | None` | 경정비 가능 여부. `Y/N`과 `O/X`를 처리 |
| `truckSaYn` | `is_truck_rest_area` | `bool | None` | 화물휴게소 여부. `Y/N`과 `O/X`를 처리 |
| `batchMenu` | `representative_food` | `str | None` | 대표음식 |

---

### 전국 휴게소 정보

- **포털**: `data.ex.co.kr` / `data.go.kr` 표준 (`tn_pubr_public_rest_area_api`)
- **경로 (data.go.kr)**: `https://api.data.go.kr/openapi/tn_pubr_public_rest_area_api`
- **메서드**: `client.restarea.list_all()`

**파라미터 (data.go.kr 표준)**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `serviceKey` | R | `str` | 인증키 |
| `pageNo` | O | `int` | 페이지 |
| `numOfRows` | O | `int` | 건수 |
| `type` | O | `str` | `xml`/`json` *(언더스코어 없음, 표준데이터셋이라 `_type` 아님)* |
| `restAreaNm` | O | `str` | 휴게소명 검색 |
| `routeNm` | O | `str` | 노선명 검색 |

**응답 주요 필드**

| 필드 | 설명 |
|------|------|
| `restAreaNm` | 휴게소명 |
| `routeNm` | 노선명 |
| `directionContent` | 방향 (상/하행) |
| `lcLatitude` / `lcLongitude` | 위도/경도 |
| `gasStnYn`, `lpgStnYn`, `evChargYn` | 주유소/LPG/전기충전 여부 |
| `pharmacyYn`, `clinicYn` | 약국/의료시설 |
| `phoneNumber` | 대표전화 |
| `referenceDate` | 데이터 기준일 |

---

### 휴게소별 날씨

고속도로 휴게소별 기준 시각 날씨 정보를 조회한다. `latest_weather()`는 같은 endpoint를 최근 시간대부터 순차 조회해 비어 있지 않은 첫 페이지를 반환하는 helper다.

- **포털**: `data.ex.co.kr`
- **기관 URL**: `http://data.ex.co.kr/openapi/basicinfo/openApiInfoM?apiId=0508`
- **경로**: `/openapi/restinfo/restWeatherList`
- **메서드**: `client.restarea.weather()`, `client.restarea.latest_weather()`

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `sdate` | R | `str` / `date` / `datetime` | 기준일 (`YYYYMMDD`) |
| `stdHour` | R | `str` / `int` | 기준 시각 (`00`~`23`) |

**응답 필드**

| 원본 필드 | 모델 필드 | 타입 | 설명 |
|-----------|-----------|------|------|
| `sdate` | `sdate` | `str` | 기준일 |
| `stdHour` | `std_hour` | `str` | 기준 시각 |
| `sdate` + `stdHour` | `observed_at` | `datetime` | KST 기준 관측/제공 시각 |
| `unitCode` | `unit_code` | `str` | 휴게소 코드 |
| `unitName` | `unit_name` | `str` | 휴게소명 |
| `routeNo` | `route_no` | `str | None` | 노선번호 |
| `routeName` | `route_name` | `str | None` | 노선명 |
| `updownTypeCode` | `direction_code` | `str | None` | 방향 코드 |
| `xValue` / `yValue` | `lon` / `lat` | `float | None` | 유효한 WGS84 경도/위도 |
| `addr` | `address` | `str | None` | Provider 원문 주소 문자열. 주소 문자열만으로는 법정동코드를 추정하지 않음 |
| `measurement` | `measurement_station` | `str | None` | 관측 지점명 |
| `weatherContents` | `weather` | `str | None` | 날씨 설명 |
| `tempValue` | `temperature` | `float | None` | 기온 |
| `humidityValue` | `humidity` | `float | None` | 습도 |
| `windValue` | `wind_speed` | `float | None` | 풍속 |
| `windContents` | `wind_direction_code` | `str | None` | 풍향 코드 |
| `rainfallValue` | `rainfall` | `float | None` | 강수량 |
| `rainfallstrengthValue` | `rainfall_strength` | `float | None` | 강수강도 |
| `newsnowValue` | `new_snow` | `float | None` | 신적설 |
| `snowValue` | `snow` | `float | None` | 적설 |
| `cloudValue` | `cloud` | `float | None` | 운량 |
| `dewValue` | `dew_point` | `float | None` | 이슬점 |

`-99`, `-99.0`, `-99.000000` 계열 결측값은 typed 필드에서 `None`으로 정규화하고 원문은 `raw`에 보존한다.

---

### 주유소별 가격·업체 현황

고속도로 휴게소 내 주유소의 정유사와 유종별 가격을 조회한다.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/business/curStateStation`
- **메서드**: `client.restarea.fuel_prices()`

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `routeName` | O | `str` | 노선명 |
| `direction` | O | `str` | 방향 |
| `oilCompany` | O | `str` | 정유사 |
| `serviceAreaName` | O | `str` | 휴게소명 |
| `routeCode` | O | `str` | 노선코드 |
| `serviceAreaCode` | O | `str` | 휴게소코드 |

**응답 필드**

| 원본 필드 | 모델 필드 | 타입 | 설명 |
|-----------|-----------|------|------|
| `routeCode` | `route_code` | `str | None` | 노선코드 |
| `serviceAreaCode` | `service_area_code` | `str` | 휴게소코드 |
| `serviceAreaCode2` | `service_area_code2` | `str | None` | 보조 휴게소코드 |
| `routeName` | `route_name` | `str | None` | 노선명 |
| `direction` | `direction` | `str | None` | 방향 |
| `oilCompany` | `oil_company` | `str | None` | 정유사 |
| `lpgYn` | `has_lpg` | `bool | None` | LPG 여부. `Y/N`과 `O/X`를 처리 |
| `serviceAreaName` | `service_area_name` | `str | None` | 휴게소/주유소명 |
| `telNo` | `phone_number` | `str | None` | 전화번호 |
| `svarAddr` | `address` | `str | None` | Provider 원문 주소 문자열 |
| `gasolinePrice` | `gasoline_price` | `int | None` | 휘발유 가격. `1,994원` 같은 단위 suffix를 처리 |
| `diselPrice` / `dieselPrice` | `diesel_price` | `int | None` | 경유 가격 |
| `lpgPrice` | `lpg_price` | `int | None` | LPG 가격 |

---

### 노선별·방향별 휴게소 편의시설 현황

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/business/conveniServiceArea`
- **메서드**: `client.restarea.convenience_facilities()`

응답 필드는 포털 문서와 실제 응답 간 차이가 있을 수 있어 현재는 `Page[dict]`로 반환한다.

**파라미터**

| 이름 | 필수 | 타입 | 설명 |
|------|------|------|------|
| `direction` | O | `str` | 방향 |
| `serviceAreaName` | O | `str` | 휴게소명 |
| `routeCode` | O | `str` | 노선코드 |
| `serviceAreaCode` | O | `str` | 휴게소코드 |

---

### 휴게소 음식가격

EX-FOOD 가격 정보. 휴게소·매장·메뉴별 가격.

- **포털**: `data.ex.co.kr`
- **경로**: `/openapi/restinfo/restMenuList` (대표 명칭, 실 경로는 포털에서 확인)
- **메서드**: `client.restarea.food_price()`

**응답 필드**

| 필드 | 설명 |
|------|------|
| `serviceAreaCode` | 휴게소 코드 |
| `serviceAreaName` | 휴게소명 |
| `storeCode` / `storeName` | 매장 |
| `foodCode` / `foodName` | 음식명 |
| `price` | 가격 (원) |
| `recommendYn` | 대표 메뉴 여부 |

---

### 휴게소 시설 정보

여러 시설 정보 엔드포인트는 모두 비슷한 패턴.

| 메서드 | 원본 엔드포인트 (data.ex.co.kr) | 주요 응답 필드 |
|--------|-------------------------------|----------------|
| `restarea.parking()` | `/openapi/restinfo/restParking` | `total`, `large`, `small`, `disabled` (대수) |
| `restarea.wifi()` | `/openapi/restinfo/restWifi` | `wifiYn` (제공 여부) |
| `restarea.restroom()` | `/openapi/restinfo/restRestroom` | `maleStool`, `femaleStool` (변기 수) |
| `restarea.disabled_facility()` | `/openapi/restinfo/restDisabled` | `parking`, `tactile`, `lounge` |
| `restarea.bus_transit()` | `/openapi/restinfo/restBus` | `routeName`, `operatingHours` |

공통 파라미터: 페이지네이션. `serviceAreaName`으로 필터링 가능.

---

## 영업소·시설 (Facility)

### 영업소 위치정보

좌표를 포함한 영업소 상세 정보. `tollgate_list()`보다 풍부한 메타데이터.

- **포털**: `data.go.kr` (ID `15076728`)
- **메서드**: `client.facility.tollgate_info()`

---

### 졸음쉼터

고속도로 졸음쉼터 설치 현황.

- **포털**: `data.ex.co.kr` / `data.go.kr`
- **경로**: `/openapi/restinfo/drowsyShelter` (대표)
- **메서드**: `client.facility.drowsy_shelter()`

**응답 필드**

| 필드 | 설명 |
|------|------|
| `seq` | 일련번호 |
| `installYear` | 설치년도 |
| `routeName` | 노선명 |
| `mileage` | 이정 (km) |
| `direction` | 방향 |
| `name` | 졸음쉼터명 |

---

### 갓길차로제

차로제어 시스템(LCS) 시행 구간.

- **포털**: `data.go.kr` (ID `15001283`)
- **메서드**: `client.facility.shoulder_lane()`

**응답 필드**

| 필드 | 설명 |
|------|------|
| `divCd` / `divNm` | 구분 코드/명 |
| `section` | 구간 (예: "양재IC ~ 신갈JCT") |
| `direction` | 방향 |
| `length` | 연장 (km) |
| `laneOperation` | 차로 운영 형태 |

---

## 행정·조달 (Admin)

### 전자조달 계약공개

한국도로공사 전자조달 계약 현황.

- **포털**: `data.go.kr` (ID `15128076`)
- **메서드**: `client.admin.procurement_contracts()`

**응답 필드**

| 필드 | 설명 |
|------|------|
| `noticeDivCode` / `noticeDivName` | 공고 구분 |
| `noticeNo` | 공고번호 |
| `contractName` | 계약명 |
| `contractMethod` | 계약방법 |
| `bizRegNo` | 사업자등록번호 |
| `contractorName` | 계약업체명 |
| `contractAmount` | 계약금액 |
| `contractDept` / `mainDept` | 계약/주관 부서 |
| `contractDate` | 계약체결일자 |

---

## 기준정보 (Reference)

### 공통코드

DSRC, TCS, HIPASS, VDS, RSE 등 공통코드 일괄 조회.

- **포털**: `data.go.kr` (ID `15042751` — 파일데이터 형식, OpenAPI 미제공 시 라이브러리 내장 코드 사용)
- **메서드**: `client.reference.common_codes()`

### 노선

전국 고속도로 노선 마스터.

- **포털**: `data.go.kr` (ID `15087178` 기준자료)
- **메서드**: `client.reference.routes()`

**응답 필드**

| 필드 | 설명 |
|------|------|
| `routeNo` | 노선번호 (4자리) |
| `routeName` | 도로명 |
| `roadGradeCode` | 도로등급구분코드 |
| `startNodeId` / `endNodeId` | 시작/종료 노드 ID |
| `shortName` / `displayName` | 단축명/표출명 |
| `startName` / `endName` | 시점명/종점명 |
| `freeFlowSpeed` | 소통원활 기준속도 |
| `congestionSpeed` | 정체 기준속도 |

---

## 검증되지 않은 경로에 대한 참고

본 문서의 일부 엔드포인트 경로(`/openapi/restinfo/restWifi` 등)는
포털의 JavaScript 기반 UI 특성상 외부 문서로부터 100% 검증이 어려웠습니다.
실제 라이브러리 구현 시에는 다음 절차로 확인을 권장합니다.

1. <https://data.ex.co.kr/dataset/datasetList/list?pn=1>에서 해당 데이터셋 페이지 진입
2. **OpenAPI 보기** 버튼으로 호출 URL 확인
3. **미리보기** 기능으로 응답 구조 확인
4. 결과를 `tests/fixtures/`에 저장하고 모델/테스트 작성

엔드포인트 URL이 변경되었거나 추가된 경우 PR을 환영합니다.
