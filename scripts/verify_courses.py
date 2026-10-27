#!/usr/bin/env python3
"""병합된 구장에 검증 상태와 품질 점검 결과를 붙인다. → data/verified/courses_checked.json

검증 상태
- official_page_checked : 공식 기관 페이지를 사람이 직접 확인한 기록
- official_dataset      : 공공데이터포털 파일데이터에 있는 구장 (기관이 공개한 자료, 현장 확인은 아님)
- unverified_candidate  : parkda.v2 저장소 Excel 에만 있는 구장 (출처 기관·재이용 조건 불명)
- needs_review          : 출처 간 충돌이 있는 구장 (주소·홀수·전화·요금 중 하나)
- excluded_test         : 테스트·가상 데이터로 보이는 항목 (공개 목록에서 제외)

품질 점검 항목(flags)
address_missing, coords_missing, coords_out_of_korea, coords_region_mismatch,
holes_missing, holes_suspicious, stale_source(2년 이상 된 공공데이터), closed_suspected, conflict
"""
import json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import REGION_CENTER, TEST_PATTERN, haversine_m, to_float

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "courses_merged.json"
OUT = ROOT / "data" / "verified" / "courses_checked.json"
TODAY = date(2026, 10, 27)


def check(rec):
    flags = []
    name, addr = rec.get("name") or "", rec.get("address") or ""
    if TEST_PATTERN.search(name) or TEST_PATTERN.search(addr):
        return "excluded_test", ["test_or_dummy_data"]
    if not addr:
        flags.append("address_missing")
    la, lo = to_float(rec.get("latitude")), to_float(rec.get("longitude"))
    if la is None or lo is None:
        flags.append("coords_missing")
    elif not (33 <= la <= 39 and 124 <= lo <= 132):
        flags.append("coords_out_of_korea")
    elif rec.get("region") in REGION_CENTER and haversine_m((la, lo), REGION_CENTER[rec["region"]]) > 350_000:
        flags.append("coords_region_mismatch")
    holes = rec.get("holes")
    if holes is None:
        flags.append("holes_missing")
    elif holes < 6 or holes > 90:
        flags.append("holes_suspicious")
    if rec.get("conflicts"):
        flags.append("conflict")
    if "폐쇄" in name or "폐장" in name:
        flags.append("closed_suspected")
    srcs = rec.get("sources", [])
    pub = [s for s in srcs if s["source_type"] == "public" and s.get("dataset_updated")]
    for s in pub:
        try:
            y, m, d = [int(x) for x in s["dataset_updated"][:10].split("-")]
            if (TODAY - date(y, m, d)).days > 730:
                flags.append("stale_source")
        except ValueError:
            pass
    types = {s["source_type"] for s in srcs}
    if rec.get("conflicts"):
        status = "needs_review"
    elif "official_page" in types:
        status = "official_page_checked"
    elif "public" in types:
        status = "official_dataset"
    else:
        status = "unverified_candidate"
    return status, sorted(set(flags))


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    out = []
    for rec in data["records"]:
        status, flags = check(rec)
        rec["verification_status"] = status
        rec["flags"] = flags
        rec["verified_at"] = rec["sources"][0]["collected_at"][:10] if status in ("official_page_checked", "official_dataset") else None
        out.append(rec)
    cands = []
    for rec in data.get("candidates", []):
        status, flags = check(rec)
        if rec.get("covered_by_official"):
            status = "covered_by_official"
        elif status == "official_dataset":  # Excel 기록은 공식 출처가 아니므로 후보로 둔다
            status = "unverified_candidate"
        rec["verification_status"] = status
        rec["flags"] = flags
        rec["verified_at"] = None
        cands.append(rec)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"records": out, "candidates": cands, "review": data["review"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    print("공식 구장 상태:", dict(Counter(r["verification_status"] for r in out)))
    print("후보 상태:", dict(Counter(r["verification_status"] for r in cands)))
    fl = Counter(f for r in out for f in r["flags"])
    print("점검:", dict(fl.most_common()))
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
