#!/usr/bin/env python3
"""원본 자료(공공데이터 CSV, Excel)를 공통 스키마로 정규화한다. → data/processed/courses_normalized.jsonl

- 공공데이터: 열 이름이 기관마다 달라서 별칭 목록으로 찾는다. 파크골프 구장 행만 남긴다.
- 스크린골프·대회·동호회·강좌·골프장 내장객 등 구장이 아닌 자료는 제외한다.
- 좌표·주소는 원본 값을 그대로 쓰고, 범위·형식 검사는 verify_courses.py 에서 한다.
- 추정으로 값을 채우지 않는다. 없는 값은 None 으로 둔다.
"""
import csv, datetime as dt, io, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import CITY_REGION, clean, region_of, to_float, to_int_holes

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "data" / "raw" / "public"
EXCEL = ROOT / "data" / "processed" / "excel_records.json"
OUT = ROOT / "data" / "processed" / "courses_normalized.jsonl"

ALIASES = {
    "name": ["파크골프장명", "시설명", "시 설 명", "명칭", "구장명", "장소명", "name"],
    "address": ["소재지지번주소", "지번 주소", "소재지 지번주소", "소재지도로명주소", "주소", "위치", "address"],
    "road": ["소재지도로명주소", "소재지도로명주소 "],
    "lat": ["위도"], "lng": ["경도"],
    "holes": ["홀수", "홀 수", "규모(홀)", "홀"], "courses": ["코스수"],
    "area": ["면적", "면적(제곱미터)", "면적(미터제곱)", "규모(제곱미터)", "규모(미터제곱)", "부지면적", "규모", "면적(미터제곱) "],
    "phone": ["전화번호", "연락처", "예약 문의 전화번호"],
    "operator": ["운영기관", "관리기관", "관리기관명", "관리주체", "운영주체"],
    "city": ["시군", "시군구"],
    "closed": ["휴무일", "휴장일"], "fee": ["이용요금", "이용료"],
    "reservation": ["예약방식"], "reservation_url": ["예약페이지 링크"],
    "sport": ["종목"],
}
EXCLUDE_TITLE = re.compile(r"스크린|골프장_내장객|대회|동호회|강좌|사진DB|이용자")


def read_csv(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0] if rows else [], rows[1:]


def col(header, names):
    h = [str(x).strip() for x in header]
    for n in names:
        if n in h:
            return h.index(n)
    for n in names:  # 공백 차이 허용
        for i, x in enumerate(h):
            if x.replace(" ", "") == n.replace(" ", ""):
                return i
    return None


def base(source_type, source_name, source_url, publisher, dataset_updated, collected_at, license_):
    return {"source_type": source_type, "source_name": source_name, "source_url": source_url,
            "publisher": publisher, "dataset_updated": dataset_updated, "collected_at": collected_at,
            "source_license": license_}


def city_region(address):
    """시도 표기가 없는 주소: 주소 안의 시·군 이름으로 시도를 정한다 (고정 대응표)."""
    for token in (address or "").split():
        if token in CITY_REGION:
            return CITY_REGION[token]
    return None


def from_public():
    out = []
    for meta_path in sorted(PUB.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("status") != "ok":
            continue
        title = meta.get("source_name", "")
        if EXCLUDE_TITLE.search(title):
            continue
        header, rows = read_csv(ROOT / meta["file"])
        idx = {k: col(header, v) for k, v in ALIASES.items()}
        if idx["name"] is None and idx["address"] is None:
            continue
        month_cols = [i for i, h in enumerate(header) if "운영시간" in h]      # 예: "5월 운영시간"
        facility_i = col(header, ["편의 부대시설", "편의부대시설", "부대시설", "보유시설"])
        for n, r in enumerate(rows, start=2):
            def g(k):
                i = idx.get(k)
                return clean(r[i]) if i is not None and i < len(r) else None
            hours = None
            if month_cols:  # 월별 운영시간을 같은 값끼리 묶어 한 줄로 (원문 그대로)
                parts = []
                for i in month_cols:
                    v = clean(r[i]) if i < len(r) else None
                    if v:
                        label = header[i].replace("운영시간", "").strip()
                        parts.append(f"{label} {v}".strip())
                if parts:
                    hours = "운영시간: " + ", ".join(parts)
            facilities = clean(r[facility_i]) if facility_i is not None and facility_i < len(r) else None
            parking = ("있음 (편의시설 기재)" if facilities and "주차" in facilities else None)
            restroom = ("있음 (편의시설 기재)" if facilities and "화장실" in facilities else None)
            name = g("name")
            if not name:
                continue
            if g("sport") and "파크골프" not in g("sport"):
                continue
            if "파크골프" not in name and not (idx["sport"] is not None or "파크골프" in title):
                continue
            if "스크린" in name:
                continue
            addr = g("address") or g("road")
            rec = base("public", title, meta["source_url"], meta.get("publisher"), meta.get("dataset_updated"),
                       meta["collected_at"], meta.get("source_license"))
            rec.update({
                "source_key": f"public:{meta['id']}:{n}",
                "name": name, "address": addr, "road_address": g("road"),
                "region": region_of(addr) or region_of(meta.get("publisher") or "") or city_region(addr),
                "city": g("city"),
                "latitude": to_float(g("lat")), "longitude": to_float(g("lng")),
                "holes": to_int_holes(g("holes")), "course_count": to_int_holes(g("courses")),
                "area_m2": g("area"),
                "fee": g("fee"), "closed_days": g("closed"), "reservation_method": g("reservation"),
                "reservation_url": g("reservation_url"), "phone": g("phone"), "operator": g("operator") or meta.get("publisher"),
                "opening_hours": hours, "parking": parking, "restroom": restroom, "website": None,
                "kpga_id": None,
            })
            out.append(rec)
    return out


def from_excel():
    out = []
    data = json.loads(EXCEL.read_text(encoding="utf-8"))
    for r in data:
        name = clean(r.get("name"))
        if not name:
            continue
        addr = clean(r.get("address"))
        lat = lng = None
        gps = clean(r.get("gps"))
        if gps and "/" in gps:
            a, b = gps.split("/", 1)
            lat, lng = to_float(a), to_float(b)  # 형식: 위도/경도
        rec = base("excel", r["source_name"], r["source_url"], "parkda.v2 저장소 (출처 기관 미기재)", None,
                   r["collected_at"], r["source_license"])
        rec.update({
            "source_key": f"excel:{r['origin_file']}:{r['origin_row']}",
            "name": name, "address": addr, "road_address": None, "region": region_of(addr),
            "city": None, "latitude": lat, "longitude": lng,
            "holes": to_int_holes(r.get("holes")), "course_count": None, "area_m2": clean(r.get("size")),
            "fee": None, "closed_days": None, "reservation_method": None, "reservation_url": None,
            "phone": None, "operator": None, "opening_hours": None, "parking": None, "restroom": None,
            "website": None, "kpga_id": clean(r.get("kpga_id")),
        })
        out.append(rec)
    return out


def from_manual():
    """사람이 공식 페이지를 직접 확인해 옮긴 기록 (data/raw/manual/*.json)."""
    out = []
    for path in sorted((ROOT / "data" / "raw" / "manual").glob("*.json")):
        out.extend(json.loads(path.read_text(encoding="utf-8")))
    return out


def main():
    recs = from_public() + from_excel() + from_manual()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = {}
    for r in recs:
        by[r["source_type"]] = by.get(r["source_type"], 0) + 1
    print(f"정규화 {len(recs)}건 {by} → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
