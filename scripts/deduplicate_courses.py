#!/usr/bin/env python3
"""같은 구장을 여러 출처에서 찾았을 때 하나로 병합한다. → data/processed/courses_merged.json

규칙
- 같은 시도 + 이름(정규화) 이고, 좌표가 300m 이내이거나 주소(정규화)가 같으면 같은 구장으로 본다.
- 좌표가 500m 넘게 떨어지거나, 주소가 서로 다르면 '충돌'로 표시하고 병합하지 않는다 (검토 대상).
- 병합 시 값은 출처 우선순위(공식 페이지 > 공공데이터 > Excel)로 채운다. 값이 충돌하면 기록을 남긴다.
- 여러 번 실행해도 결과는 같다 (입력이 같으면 출력이 같음).
"""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import haversine_m, norm_addr, norm_name

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "courses_normalized.jsonl"
OUT = ROOT / "data" / "processed" / "courses_merged.json"
PRIORITY = {"official_page": 0, "public": 1, "excel": 2}
FIELDS = ["name", "region", "city", "district", "address", "road_address", "latitude", "longitude", "holes",
          "course_count", "area_m2", "fee", "opening_hours", "closed_days", "reservation_method", "reservation_url",
          "phone", "operator", "parking", "restroom", "website", "kpga_id"]


def compatible(a, b):
    """두 기록이 같은 구장인지 판단. (같음, 충돌사유) 반환."""
    if a["region"] != b["region"] or norm_name(a["name"]) != norm_name(b["name"]):
        return False, None
    la, lo = a.get("latitude"), a.get("longitude")
    lb, lob = b.get("latitude"), b.get("longitude")
    dist = haversine_m((la, lo), (lb, lob)) if None not in (la, lo, lb, lob) else None
    same_addr = norm_addr(a.get("address")) and norm_addr(a.get("address")) == norm_addr(b.get("address"))
    if dist is not None and dist <= 300:
        return True, None
    if same_addr:
        return True, None
    if dist is not None and dist > 500:
        return False, f"좌표 차이 {int(dist)}m (같은 이름, 다른 위치)"
    if norm_addr(a.get("address")) and norm_addr(b.get("address")) and not same_addr:
        return False, "같은 이름, 다른 주소"
    return False, None  # 정보가 부족하면 같은 구장으로 단정하지 않는다


def merge(group):
    group = sorted(group, key=lambda r: PRIORITY.get(r["source_type"], 9))
    primary = dict(group[0])
    conflicts = []
    for other in group[1:]:
        for f in FIELDS:
            pv, ov = primary.get(f), other.get(f)
            if pv in (None, "") and ov not in (None, ""):
                primary[f] = ov
            elif ov not in (None, "") and pv != ov and f in ("holes", "address", "phone", "fee"):
                conflicts.append({"field": f, "values": [str(pv), str(ov)], "sources": [primary["source_key"], other["source_key"]]})
    primary["sources"] = [{"source_key": r["source_key"], "source_type": r["source_type"], "source_name": r["source_name"],
                           "source_url": r["source_url"], "publisher": r.get("publisher"),
                           "dataset_updated": r.get("dataset_updated"), "collected_at": r["collected_at"],
                           "source_license": r["source_license"]} for r in group]
    primary["conflicts"] = conflicts
    return primary


def cluster(items, review):
    buckets = defaultdict(list)
    for r in items:
        buckets[(r.get("region") or "", norm_name(r["name"]))].append(r)
    out = []
    for key, group in buckets.items():
        clusters = []
        for r in group:
            placed = False
            for c in clusters:
                ok, reason = compatible(c[0], r)
                if ok:
                    c.append(r); placed = True; break
                if reason:
                    review.append({"name": r["name"], "region": r.get("region"), "reason": reason,
                                   "a": c[0]["source_key"], "b": r["source_key"]})
            if not placed:
                clusters.append([r])
        out.extend(clusters)
    return out


def main():
    """공식 출처(공공데이터·공식 페이지)끼리만 병합한다. 저장소 Excel 은 필드를 빌려주지 않는다 (라이선스 불명).
    Excel 전용 구장은 후보로만 남기고, 공식 구장과 같은 곳이면 '공식 구장에 포함됨'으로 표시한다."""
    recs = [json.loads(l) for l in IN.open(encoding="utf-8")]
    official = [r for r in recs if r["source_type"] in ("public", "official_page")]
    excel = [r for r in recs if r["source_type"] == "excel"]
    review = []
    off_clusters = cluster(official, review)
    merged = [merge(c) for c in off_clusters]
    cands = []
    for c in cluster(excel, review):
        rep = c[0]
        covered = None
        for m in merged:
            if m["region"] == rep["region"] and norm_name(m["name"]) == norm_name(rep["name"]):
                ok, _ = compatible(m, rep)
                if ok:
                    covered = m["name"]
                    break
        item = merge(c)
        item["covered_by_official"] = covered
        cands.append(item)
    merged.sort(key=lambda m: (m.get("region") or "", m["name"]))
    cands.sort(key=lambda m: (m.get("region") or "", m["name"]))
    OUT.write_text(json.dumps({"records": merged, "candidates": cands, "review": review}, ensure_ascii=False, indent=2), encoding="utf-8")
    multi = sum(1 for m in merged if len(m["sources"]) > 1)
    covered = sum(1 for c in cands if c.get("covered_by_official"))
    print(f"공식 출처 구장 {len(merged)}곳 (여러 출처 병합 {multi}곳) · Excel 후보 {len(cands)}곳 "
          f"(공식 구장과 같은 곳 {covered}곳 제외 대상) · 검토 {len(review)}건 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
