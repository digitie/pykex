# WSL kor-travel-geo 디버그 UI 메모

> **이름 변경**: 이 문서는 `python-kraddr-geo`/`kraddr_geo_api`/`pykraddr` 경로명으로 작성됐지만,
> 그 프로젝트는 `kor-travel-geo`(Python 패키지 `kortravelgeo`)로 리네임됐고 SpatiaLite/SQLite 기반
> 구현도 PostgreSQL + PostGIS로 재구현됐습니다. 아래의 옛 경로·모듈명·명령은 더 이상 유효하지
> 않습니다. 이 저장소(`python-krex-api`)는 `kor-travel-geo`를 import하지 않으므로 이 노트를
> 정본으로 유지하지 않습니다.
>
> `kor-travel-geo`의 로컬 디버그 UI를 WSL에서 띄우는 현재 방법은 그 저장소 자신의 문서
> (`docs/agent-guide.md`, `docs/adr/065-linux-only-development-environment.md` 등)를 확인하세요.
> 제공 표면은 README 기준으로 REST API `uvicorn kortravelgeo.api.app:app`, 관리 UI는 별도 Next.js
> 패키지 `kor-travel-geo-ui`입니다 — 정확한 포트/플래그는 그쪽 문서에서 확인해야 이 저장소가 다시
> 오래된 정보를 복제하지 않습니다.

---

아래는 리네임 이전에 작성된 원문(참고용, 유효하지 않음)입니다.

이 provider를 `python-kraddr-geo` 또는 `python-krtour-map`과 함께 검증할 때는 WSL에서 Linux 실행 파일을 사용하고 host binding을 명시해 로컬 지오코딩 디버그 스택을 실행한다.

```bash
cd /mnt/f/dev/pykraddr
KRADDR_GEO_SPATIALITE_PATH=/mnt/f/dev/pykraddr/.codex_tmp/debug-kraddr.sqlite   .venv/bin/python -m uvicorn kraddr_geo_api.main:app   --app-dir backend --host 0.0.0.0 --port 3011

cd /mnt/f/dev/pykraddr/web
PATH=/mnt/f/dev/pykraddr/.wsl-node/node-v22.21.1-linux-x64/bin:$PATH NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:3011   npm run dev -- --hostname 0.0.0.0 --port 3010
```

WSL 내부에서는 `http://127.0.0.1:3010`을 사용한다. Windows에서 접근할 때는 먼저 `http://localhost:3010`을 시도하고, localhost forwarding이 동작하지 않으면 `hostname -I`로 확인한 WSL 주소를 사용한다.

이 흐름에서는 WSL에서 Windows `node.exe`/`npx`를 호출하지 않는다. pykraddr 저장소 안의 `.wsl-node` Linux Node 경로가 확인된 실행 경로다. 2026-05-20 warm smoke 기준 웹 페이지는 약 100 ms, `/addresses`는 29 ms, `/reverse-geocode`는 24 ms 수준이었다.
