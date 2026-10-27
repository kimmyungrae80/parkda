#!/usr/bin/env python3
"""검증 결과를 서비스용 JSON 과 품질 보고서로 내보낸다.

- data/verified/courses.json : 앱이 읽는 구장 목록 (테스트 데이터 제외)
- data/verified/quality_report.json : 집계 수치 (보고서 생성용)
- docs/DATA_QUALITY_REPORT.md : 사람이 읽는 품질 보고서 (수치는 이 스크립트가 채움)
- id 는 지역 + 정규화 이름 + 정규화 주소의 해시 → 같은 입력이면 같은 id (재실행해도 변하지 않음)
"""
import hashlib, json, sys
from collections import Counter
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import norm_addr, norm_name

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "verified" / "courses_checked.json"
OUT = ROOT / "data" / "verified" / "courses.json"
REPORT = ROOT / "data" / "verified" / "quality_report.json"
CAND = ROOT / "data" / "processed" / "candidates_internal.json"  # 공개하지 않음 (검토 대기)
DOC = ROOT / "docs" / "DATA_QUALITY_REPORT.md"
TODAY = date(2026, 10, 27).isoformat()
REGION_ORDER = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남",
                "전북", "전남", "경북", "경남", "제주"]  # 전국 17개 시도


def stable_id(r):
    key = f"{r.get('region')}|{norm_name(r['name'])}|{norm_addr(r.get('address'))}"
    return "pg-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


GEOCACHE = ROOT / "data" / "processed" / "geocode_cache.json"


MAP_OK = ("official_coord", "name_match", "address_match")


def coord_fields(r, geo):
    """좌표와 검증 등급을 정한다.
    official_coord : 공공데이터·공식 페이지의 좌표 (지역 범위 검사 통과 시)
    name_match     : 주소 질의로 찾은 결과의 이름이 구장 이름과 일치
    address_match  : 결과 주소에 구장의 지번·도로번호가 일치
    weak_match     : 지역만 맞음 → 지도에 표시하지 않음
    none           : 좌표 없음 → 목록에는 표시, 지도에는 표시하지 않음
    """
    flags = set(r.get("flags", []))
    if r.get("latitude") is not None and r.get("longitude") is not None:
        if flags & {"coords_out_of_korea", "coords_region_mismatch"}:
            return r["latitude"], r["longitude"], "official_dataset", "좌표가 지역 범위와 맞지 않아 지도에서 제외", "failed_check"
        return r["latitude"], r["longitude"], "official_dataset", None, "official_coord"
    k = f"{r.get('region')}|{r['name']}|{r.get('address')}"
    g = geo.get(k)
    if g and g.get("status") == "ok":
        level = g.get("match_level", "weak_match")
        note = "주소 기반 자동 좌표 (OpenStreetMap). © OpenStreetMap contributors"
        if level == "weak_match":
            note += " · 지역만 일치해 지도에 표시하지 않음"
        return g["lat"], g["lng"], "osm_nominatim", note, level
    return None, None, None, None, "none"


def public_row(r, geo=None):
    primary = r["sources"][0]
    official = [s for s in r["sources"] if s["source_type"] in ("public", "official_page")]
    lat, lng, csrc, cnote, cmatch = coord_fields(r, geo or {})
    return {
        "id": stable_id(r), "name": r["name"], "region": r.get("region"), "city": r.get("city"),
        "district": r.get("district"), "address": r.get("address"), "road_address": r.get("road_address"),
        "latitude": lat, "longitude": lng, "coordinate_source": csrc, "coordinate_note": cnote,
        "coordinate_match": cmatch, "map_visible": bool(lat is not None and cmatch in MAP_OK),
        "holes": r.get("holes"),
        "course_count": r.get("course_count"), "fee": r.get("fee"), "opening_hours": r.get("opening_hours"),
        "closed_days": r.get("closed_days"), "reservation_method": r.get("reservation_method"),
        "reservation_url": r.get("reservation_url"), "phone": r.get("phone"), "operator": r.get("operator"),
        "parking": r.get("parking"), "restroom": r.get("restroom"), "website": r.get("website"),
        "source_url": (official[0] if official else primary)["source_url"],
        "source_name": (official[0] if official else primary)["source_name"],
        "source_license": (official[0] if official else primary)["source_license"],
        "verified_at": r.get("verified_at"), "verification_status": r["verification_status"],
        "flags": r["flags"], "conflicts": r.get("conflicts", []),
        "sources": [{"source_type": s["source_type"], "source_name": s["source_name"], "source_url": s["source_url"],
                     "collected_at": s["collected_at"][:10], "dataset_updated": s.get("dataset_updated")} for s in r["sources"]],
    }


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    # 공개 목록: 공식 출처로 확인된 구장만. 나머지는 내부 후보 파일에 둔다 (라이선스 불명 자료 공개 금지)
    public_status = ("official_dataset", "official_page_checked")
    recs = [r for r in data["records"] if r["verification_status"] in public_status]
    internal = [r for r in data["records"] + data.get("candidates", []) if r["verification_status"] not in public_status]
    CAND.write_text(json.dumps([{"id": stable_id(r), "name": r["name"], "region": r.get("region"), "address": r.get("address"),
                                 "verification_status": r["verification_status"], "flags": r["flags"],
                                 "sources": [{"source_type": x["source_type"], "source_name": x["source_name"]} for x in r["sources"]]}
                                for r in internal], ensure_ascii=False, indent=2), encoding="utf-8")
    recs.sort(key=lambda r: r["sources"][0]["source_key"])  # 입력 순서가 같으면 suffix 도 같음
    geo = json.loads(GEOCACHE.read_text(encoding="utf-8")) if GEOCACHE.exists() else {}
    rows = [public_row(r, geo) for r in recs]
    seen = Counter(r["id"] for r in rows)
    taken = Counter()
    for r in rows:
        if seen[r["id"]] > 1:  # 정보 부족으로 병합하지 않은 같은 이름 구장: 번호를 붙이고 중복 가능성 표시
            taken[r["id"]] += 1
            r["id"] = f"{r['id']}-{taken[r['id']]}"
            r["flags"] = sorted(set(r["flags"]) | {"possible_duplicate"})
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "id 충돌 해결 실패"
    rows.sort(key=lambda r: (r["region"] or "", r["name"], r["id"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    status = Counter(r["verification_status"] for r in rows)
    flags = Counter(f for r in rows for f in r["flags"])
    by_region = Counter(r["region"] or "미상" for r in rows)
    srcs = Counter(s["source_type"] for r in rows for s in r["sources"])
    raw_n = sum(1 for x in (ROOT / "data/processed/courses_normalized.jsonl").read_text(encoding="utf-8").splitlines() if '"source_type": "public"' in x or '"source_type": "official_page"' in x)
    report = {
        "generated_for_date": TODAY, "total_venues": len(rows), "by_status": dict(status),
        "unknown_region": sum(1 for r in rows if not r["region"]),
        "raw_public_rows": sum(1 for x in (ROOT / "data/processed/courses_normalized.jsonl").read_text(encoding="utf-8").splitlines() if '"public"' in x or '"official_page"' in x),
        "duplicates_removed": max(0, raw_n - len(rows)),
        "by_region": dict(by_region.most_common()), "quality_flags": dict(flags.most_common()),
        "source_records": dict(srcs), "review_items": len(data.get("review", [])),
        "internal_not_public": len(internal), "internal_by_status": dict(Counter(r["verification_status"] for r in internal)),
        "excluded_test": sum(1 for r in data["records"] if r["verification_status"] == "excluded_test"),
        "possible_duplicates": sum(1 for r in rows if "possible_duplicate" in r["flags"]),
        "with_coordinates": sum(1 for r in rows if r["latitude"] is not None and r["longitude"] is not None),
        "coordinate_sources": dict(Counter(r["coordinate_source"] for r in rows if r["coordinate_source"])),
        "coordinate_match": dict(Counter(r["coordinate_match"] for r in rows)),
        "map_visible": sum(1 for r in rows if r["map_visible"]),
        "with_phone": sum(1 for r in rows if r["phone"]), "with_fee": sum(1 for r in rows if r["fee"]),
        "with_hours": sum(1 for r in rows if r["opening_hours"]),
        "by_region_detail": {reg: {
            "venues": sum(1 for r in rows if r["region"] == reg),
            "map_visible": sum(1 for r in rows if r["region"] == reg and r["map_visible"]),
            "with_hours": sum(1 for r in rows if r["region"] == reg and r["opening_hours"]),
            "with_fee": sum(1 for r in rows if r["region"] == reg and r["fee"]),
            "with_phone": sum(1 for r in rows if r["region"] == reg and r["phone"]),
        } for reg in REGION_ORDER},
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(render_doc(report, data.get("review", [])), encoding="utf-8")
    print(f"구장 {len(rows)}곳 내보냄 → {OUT.relative_to(ROOT)}")
    print(json.dumps({k: report[k] for k in ("by_status", "with_coordinates", "with_phone", "with_fee", "possible_duplicates")}, ensure_ascii=False))


def render_doc(rep, review):
    s = rep["by_status"]
    lines = [
        "# 구장 데이터 품질 보고서", "",
        f"기준일: {rep['generated_for_date']} · 이 문서는 `scripts/export_courses.py` 가 생성한 수치를 담습니다.", "",
        "## 요약", "",
        f"- 구장 총계: **{rep['total_venues']}곳** (테스트 데이터 제외 {rep['excluded_test']}건)",
        f"- 공식 페이지 직접 확인: **{s.get('official_page_checked', 0)}곳**",
        f"- 공공데이터포털 공개 자료 기준: **{s.get('official_dataset', 0)}곳** (기관이 공개한 자료, 현장 확인 전)",
        f"- 공개하지 않은 내부 후보: **{rep['internal_not_public']}건** (parkda.v2 Excel 기반 미검증 후보 등, 출처 확인 전까지 비공개)",
        f"- 병합 검토 목록: {rep['review_items']}건",
        f"- 좌표 있음: {rep['with_coordinates']}곳 (좌표 등급: {rep['coordinate_match']}) · 전화번호: {rep['with_phone']}곳 · 이용료: {rep['with_fee']}곳 · 운영시간: {rep['with_hours']}곳",
        f"- 지도에 표시 가능한 구장 (검증된 좌표): **{rep['map_visible']}곳** / 목록에 보이는 전체: **{rep['total_venues']}곳**",
        f"- 같은 이름이지만 병합하지 않은 중복 가능 구장: {rep['possible_duplicates']}곳 (정보 부족, 검토 필요)", "",
        "## 지역별 구장 수", "",
        "| 지역 | 구장 수 |", "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in rep["by_region"].items()]
    lines += ["", "## 품질 점검 결과", "", "| 항목 | 건수 | 의미 |", "|---|---|---|"]
    meaning = {
        "coords_missing": "좌표 없음 (추정하지 않음, 화면에는 '정보 확인 중')",
        "holes_missing": "홀 수 없음", "address_missing": "주소 없음 (지도 연결 불가)",
        "conflict": "출처 간 값 충돌 (검토 필요)", "stale_source": "공공데이터 수정일이 2년 이상 지남",
        "holes_suspicious": "홀 수가 비정상 범위", "coords_out_of_korea": "한국 밖 좌표",
        "coords_region_mismatch": "시도 중심과 350km 이상 차이", "closed_suspected": "폐쇄 가능성 표기",
    }
    for k, v in rep["quality_flags"].items():
        lines.append(f"| {k} | {v} | {meaning.get(k, '')} |")
    lines += ["", "## 출처별 기록 수", "", "| 출처 유형 | 기록 수 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in rep["source_records"].items()]
    tot = rep["total_venues"] or 1
    lines += ["", "## 확보율", "",
              f"- 좌표 확보율: {rep['with_coordinates']}/{tot} ({rep['with_coordinates']*100//tot}%) · 지도 표시 가능: {rep['map_visible']}곳 ({rep['map_visible']*100//tot}%)",
              f"- 운영시간 확보율: {rep['with_hours']}/{tot} ({rep['with_hours']*100//tot}%)",
              f"- 이용료 확보율: {rep['with_fee']}/{tot} ({rep['with_fee']*100//tot}%)",
              f"- 전화번호 확보율: {rep['with_phone']}/{tot} ({rep['with_phone']*100//tot}%)",
              f"- 중복 제거: 원본 {rep['raw_public_rows']}행 → {rep['total_venues']}곳 (중복 {rep['duplicates_removed']}건 병합)",
              "", "## 시도별 구장 수와 확보 현황", "",
              "| 시도 | 구장 | 지도 표시 | 운영시간 | 이용료 | 전화 |", "|---|---|---|---|---|---|"]
    for reg, v in rep["by_region_detail"].items():
        lines.append(f"| {reg} | {v['venues']} | {v['map_visible']} | {v['with_hours']} | {v['with_fee']} | {v['with_phone']} |")
    lines += ["", f"- 지역 정보가 없는 구장: {rep['unknown_region']}곳", ""]
    lines += ["", "## 병합 검토", "", f"- 같은 이름이지만 위치·주소가 달라 병합하지 않은 항목: {len(review)}건 (세부 목록은 내부 파일에만 있음)"]
    lines += ["", "## 한계", "",
              "- 공공데이터의 운영시간·이용료·전화번호는 해당 기관이 공개한 값이며, 최신 여부는 방문 전 확인이 필요합니다.",
              "- Excel 후보의 출처 기관과 재이용 조건은 확인되지 않았습니다. 공개 전에 출처 확인이 필요합니다.",
              "- 좌표가 없는 구장은 지도에 표시하지 않고 주소 링크만 제공합니다.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
