#!/usr/bin/env python3
"""데이터 출처 문서(docs/DATA_SOURCES.md)를 수집 메타데이터와 분류 결과에서 생성한다."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
cls = json.loads((ROOT / "data/processed/dataset_classification.json").read_text(encoding="utf-8"))
import collections
cnt = collections.Counter(r["outcome"] for r in cls)
L = ["# 데이터 출처 (DATA_SOURCES)", "",
     "구장·대회 데이터의 출처와 재이용 조건. 수집 `scripts/collect_public_data.py` → 분류 `scripts/classify_datasets.py` → 정제 `scripts/normalize_*.py` → 중복 제거 `scripts/deduplicate_courses.py` → 검증 `scripts/verify_courses.py` → 내보내기 `scripts/export_courses.py`.", "",
     "## 1. 공공데이터포털 (data.go.kr) 파일데이터", "",
     f"수집 후보 {len(cls)}개: 구장 레코드 생성 **{cnt['success']}** · 관련 없음 **{cnt['unrelated']}** · 실패 **{cnt['failed']}**. 상세 분류: `docs/DATASET_CLASSIFICATION.md`.", "",
     "- 로그인·CAPTCHA·활용신청이 필요한 자료는 받지 않았고 우회하지 않았습니다.",
     "- 이용허락 문구는 각 상세 페이지에 적힌 값을 그대로 기록했습니다 (`data/raw/public/<id>.meta.json`).", "",
     "| 데이터셋 | 제공기관 | 자료 수정일 | 이용허락 | 수집일 | 결과 |", "|---|---|---|---|---|---|"]
for r in sorted(cls, key=lambda x: (x["outcome"], x.get("publisher") or "")):
    if r["outcome"] != "success":
        continue
    m = json.loads((ROOT / "data/raw/public" / f"{r['id']}.meta.json").read_text(encoding="utf-8"))
    L.append(f"| [{r['title'][:50]}]({r.get('source_url') or ''}) | {r.get('publisher') or '-'} | {m.get('dataset_updated') or '-'} | {m.get('source_license') or '-'} | {(r.get('collected_at') or '')[:10]} | {r['reason']} |")
L += ["", "## 2. 공식 페이지 직접 확인", "",
      "| 구장 | 출처 URL | 확인일 | 확인 항목 |", "|---|---|---|---|",
      "| 대저생태공원 파크골프장 | https://www.busan.go.kr/parkgolf/parkgolf03 | 2026-10-27 | 주소, 90홀, 무료, 운영시간, 휴장일, 전화 |",
      "| 화명생태공원 파크골프장 | https://www.busan.go.kr/parkgolf/parkgolf02 | 2026-10-27 | 주소, 45홀, 무료, 운영시간, 휴장일, 전화 |", "",
      "## 3. 주소 기반 자동 지오코딩 (좌표만)", "",
      "- 서비스: OpenStreetMap Nominatim · 라이선스 ODbL 1.0 · 표시: © OpenStreetMap contributors",
      "- 결과 등급: `name_match`(구장명 일치) · `address_match`(지번·도로번호 일치) · `weak_match`(지역만 일치, 지도 미표시)",
      "- 같은 시도 밖의 결과는 버림. 자동 좌표임을 화면에 표시.", "",
      "## 4. 지도·라이브러리", "",
      "- Leaflet 1.9.4 (cdnjs, BSD-2-Clause) · 지도 타일 OpenStreetMap (© OpenStreetMap contributors)", "",
      "## 5. 유튜브 (YouTube Data API v3)", "",
      "- 서버 함수 `api/youtube.js` 가 호출, 6시간 캐시. 키는 환경변수에만 있음. 채널·제목·링크 표시.", "",
      "## 6. 카카오 로컬 API (음식점·카페·주소 검색)", "",
      "- 서버 함수 `api/food.js`, `api/geocode.js`. 키 `KAKAO_REST_KEY`(환경변수). 광고·제휴 구분 정보 없음을 화면에 표시.", "",
      "## 7. 저장소 Excel 자료 (parkda.v2) — 공개하지 않음", "",
      "- 출처: https://github.com/kimmyungrae80/parkda.v2 (`park_data.xlsx`, `경기장_정보.xlsx`, 같은 내용 383행)",
      "- 라이선스 파일이 없어 재이용 조건을 확인할 수 없습니다. 공개 목록에 넣지 않습니다.", "",
      "## 8. 제외한 자료", "",
      "- 사진DB, 골프장 내장객, 동호회·클럽, 강좌·교실, 사업자 현황, 대회 유치 현황 등 구장 목록이 아닌 자료 (구장 레코드 0건).",
      "- 인증이 필요한 자료는 공식 페이지 링크만 기록하고 받지 않았습니다.", ""]
(ROOT / "docs/DATA_SOURCES.md").write_text("\n".join(L), encoding="utf-8")
print("DATA_SOURCES.md written")
