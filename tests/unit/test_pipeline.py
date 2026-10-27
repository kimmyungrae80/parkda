"""데이터 파이프라인 검증 (표준 라이브러리 + 프로젝트 스크립트만 사용). 실행: python3 tests/unit/test_pipeline.py"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import common, deduplicate_courses as dd, verify_courses as vc, collect_public_data as cpd

passed = failed = 0
def check(name, cond, detail=""):
    global passed, failed
    if cond: passed += 1
    else: failed += 1
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

# 1) 지역 판별
check("지역: 경상남도 → 경남", common.region_of("경상남도 밀양시 가곡동 743-2") == "경남")
check("지역: 전남광주통합특별시 광주 → 광주", common.region_of("전남광주통합특별시 광주광역시 남구 x") == "광주")
check("지역: 전남광주통합특별시 나주 → 전남", common.region_of("전남광주통합특별시 나주시 y") == "전남")
check("지역: 주소 없음 → None", common.region_of(None) is None)

# 2) 병합 규칙
base = {"name": "가상파크골프장", "region": "경남", "address": "경남 가상시 가상동 1-1", "latitude": 35.0, "longitude": 128.0}
same = dict(base, address="경남 가상시 가상동 1-1")
far = dict(base, latitude=35.02, longitude=128.0, address="경남 가상시 다른동 9")
noinfo_a = {"name": "가상파크골프장", "region": "경남", "address": None, "latitude": None, "longitude": None}
noinfo_b = dict(noinfo_a)
check("병합: 같은 이름·같은 주소 → 같은 구장", dd.compatible(base, same)[0] is True)
ok, reason = dd.compatible(base, far)
check("병합: 2km 떨어진 같은 이름 → 병합 안 함 + 사유", ok is False and reason is not None, str(reason))
check("병합: 정보 부족(주소·좌표 없음) → 단정하지 않고 병합 안 함", dd.compatible(noinfo_a, noinfo_b)[0] is False)

# 3) 검증 규칙
rec = {"name": "테스트파크골프장", "region": "경남", "address": "경남 테스트시", "sources": [{"source_type": "public", "dataset_updated": "2026-01-01", "collected_at": "2026-10-27T00:00:00+09:00", "source_key": "x", "source_name": "n", "source_url": "u", "source_license": "l"}], "conflicts": []}
status, flags = vc.check(rec)
check("검증: 테스트 이름은 제외", status == "excluded_test", status)
rec2 = {"name": "나다라구장", "region": "경남", "address": None, "latitude": None, "longitude": None, "holes": 300,
        "sources": [{"source_type": "public", "dataset_updated": "2019-01-01", "collected_at": "2026-10-27T00:00:00+09:00", "source_key": "y", "source_name": "n", "source_url": "u", "source_license": "l"}], "conflicts": []}
status2, flags2 = vc.check(rec2)
check("검증: 주소·좌표 없음 표시", {"address_missing", "coords_missing"} <= set(flags2), str(flags2))
check("검증: 홀 수 비정상 표시", "holes_suspicious" in flags2)
check("검증: 2년 넘은 공공데이터 표시", "stale_source" in flags2)

# 4) 공개 데이터 무결성
pub = json.loads((ROOT / "data/verified/courses.json").read_text(encoding="utf-8"))
ids = [r["id"] for r in pub]
check("공개 목록: id 중복 없음", len(ids) == len(set(ids)))
check("공개 목록: 모든 구장에 출처 URL", all(r["source_url"] and r["source_url"].startswith("http") for r in pub))
check("공개 목록: 공식 출처만 (공공데이터·공식 페이지)", all(s["source_type"] in ("public", "official_page") for r in pub for s in r["sources"]))
check("공개 목록: 허용된 검증 상태만", all(r["verification_status"] in ("official_dataset", "official_page_checked") for r in pub))
check("공개 목록: 저장소 Excel 출처 흔적 없음", "parkda.v2" not in json.dumps(pub, ensure_ascii=False))
check("공개 목록: 테스트 이름 없음", not any(common.TEST_PATTERN.search(r["name"]) for r in pub))
check("공개 목록: 좌표 출처가 표시된 항목은 OSM 출처 표기 포함",
      all(r.get("coordinate_note") for r in pub if r.get("coordinate_source") == "osm_nominatim"))
check("공개 목록: 좌표가 있으면 출처 표시", all(r.get("coordinate_source") for r in pub if r["latitude"] is not None))
check("공개 목록: 공식 확인 구장 2곳 (부산 대저·화명)", sum(1 for r in pub if r["verification_status"] == "official_page_checked") == 2)
tours = json.loads((ROOT / "data/verified/tournaments.json").read_text(encoding="utf-8"))
check("대회: 모든 항목에 출처와 라이선스", all(t["source_url"] and t["source_license"] for t in tours))
check("대회: 개최일 기록 있음", all(t["date_start"] for t in tours))

# 5) 수집 파서
html = '<strong class="key">제공기관</strong> <div class="value"><a href="x">가평군시설관리공단</a></div>' \
       '<strong class="key">수정일</strong> <div class="value">2026-07-21</div>' \
       '<strong class="key">이용허락범위</strong> <div class="value">이용허락범위 제한 없음</div>' \
       '<a href="/cmm/cmm/fileDownload.do?atchFileId=FILE_1&amp;fileDetailSn=1">x</a>'
m = cpd.parse_detail(html)
check("수집: 제공기관·수정일·이용허락 파싱", m["publisher"] == "가평군시설관리공단" and m["updated"] == "2026-07-21" and "제한 없음" in m["license"], str(m))
check("수집: 파일 ID 파싱", m["file"] == ("FILE_1", "1"))

print(f"\npipeline tests: PASS {passed} / FAIL {failed}")
sys.exit(1 if failed else 0)
