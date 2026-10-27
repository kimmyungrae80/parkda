#!/usr/bin/env python3
"""공공데이터 대회 자료에서 파크골프 대회만 골라 data/verified/tournaments.json 으로 낸다.

- 대상: 공공데이터포털 파일데이터 중 '대회명'·'주최' 열이 있는 자료 (현재 15027852: 경상북도 울진군 자료, 공공저작물 출처표시 제1유형).
- 공식 주최 기관명, 개최일, 장소, 문의처를 원문 그대로 옮기고 출처와 라이선스를 붙인다.
- 개최 종료일이 기준일보다 이전이면 '지난 대회'로 분류한다. 추정으로 일정을 만들지 않는다.
"""
import csv, datetime as dt, io, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import CITY_REGION, region_of

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "data" / "raw" / "public"
OUT = ROOT / "data" / "verified" / "tournaments.json"
TODAY = dt.date(2026, 10, 27)


def read_text(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")  # 깨진 바이트가 있어도 가능한 만큼 읽음


def main():
    out = []
    for meta_path in sorted(PUB.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("status") != "ok":
            continue
        rows = list(csv.reader(io.StringIO(read_text(ROOT / meta["file"]), newline="")))
        if not rows or "대회명" not in rows[0]:
            continue
        h = {x.strip(): i for i, x in enumerate(rows[0])}
        for n, r in enumerate(rows[1:], start=2):
            title = r[h["대회명"]].strip()
            if "파크골프" not in title:
                continue
            start = r[h["대회시작일"]].strip() if "대회시작일" in h else ""
            end = r[h["대회종료일"]].strip() if "대회종료일" in h else start
            try:
                d_end = dt.date.fromisoformat(end or start)
                period = "지난 대회" if d_end < TODAY else "예정 대회"
            except ValueError:
                period = "일정 확인 중"
            out.append({
                "id": f"tour-{meta['id']}-{n}", "title": title,
                "venue": r[h["상세장소"]].strip() if "상세장소" in h else None,
                "date_start": start or None, "date_end": end or None, "period": period,
                "organizer": r[h["주최"]].strip() if "주최" in h else None,
                "co_organizer": r[h["주관"]].strip() if "주관" in h else None,
                "contact": r[h["문의처"]].strip() if "문의처" in h else None,
                "apply_url": None, "result_url": None,
                "source_name": meta["source_name"], "source_url": meta["source_url"],
                "publisher": meta.get("publisher"), "region": region_of(meta.get("publisher") or "") or next(
                    (CITY_REGION[w] for w in (meta.get("publisher") or "").split() if w in CITY_REGION), None),
                "dataset_updated": meta.get("dataset_updated"),
                "checked_at": meta["collected_at"][:10], "source_license": meta.get("source_license"),
                "verification_status": "official_dataset",
            })
    out.sort(key=lambda t: (t["date_start"] or ""), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"파크골프 대회 {len(out)}건 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
