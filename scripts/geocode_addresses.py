#!/usr/bin/env python3
"""좌표가 없는 공식 구장을 주소로 지오코딩한다 (OpenStreetMap Nominatim, ODbL).

규칙
- 질의: 도로명주소 → 지번주소 → (주소 + 구장명) 순서로 시도한다.
- 결과 검증
  * 응답 주소가 구장의 시도 이름을 포함해야 한다 (다른 지역 오인 방지).
  * 응답 이름에 구장 이름의 핵심어가 있으면 'name_match' (구장 자체를 찾은 것으로 봄).
  * 핵심어가 없으면 'address_only' (주소 수준 일치). 이 경우 지도에 확정 위치로 표시하지 않는다.
- 결과는 원본 좌표와 구분해 coordinate_source='osm_nominatim' 으로 저장한다.
- 1.1초 간격, 식별 가능한 User-Agent, 결과 캐시 (재실행 시 같은 질의는 다시 보내지 않음).
사용법: python3 scripts/geocode_addresses.py
"""
import json, re, sys, time, urllib.parse
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "verified" / "courses_checked.json"
CACHE = ROOT / "data" / "processed" / "geocode_cache.json"
UA = "PARKDA-data-pipeline/1.0 (contact: kimmyungrae80@gmail.com)"
REGION_NAMES = {"서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"], "광주": ["광주"], "대전": ["대전"],
                "울산": ["울산"], "세종": ["세종"], "경기": ["경기"], "강원": ["강원"], "충북": ["충청북도", "충북"],
                "충남": ["충청남도", "충남"], "전북": ["전북", "전라북도"], "전남": ["전라남도", "전남"],
                "경북": ["경상북도", "경북"], "경남": ["경상남도", "경남"], "제주": ["제주"]}
GENERIC = {"파크골프장", "파크골프", "공원", "체육공원", "구장"}


def key_of(r):
    return f"{r.get('region')}|{r['name']}|{r.get('address')}"


def core_tokens(name):
    t = re.sub(r"\(.*?\)", "", name or "")
    t = t.replace("파크골프장", "").replace("파크골프", "").strip()
    return [w for w in re.split(r"[\s·]+", t) if len(w) >= 2 and w not in GENERIC]


def query(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 3, "countrycodes": "kr", "addressdetails": 1})
    time.sleep(1.1)
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ko"}, timeout=30)
    r.raise_for_status()
    return r.json()


def try_queries(r):
    names = REGION_NAMES.get(r.get("region"), [])
    candidates = []
    for q in [r.get("road_address"), (r.get("address") or "").split(",")[0], f"{r['name']} {(r.get('address') or '').split(',')[0]}"]:
        if q and q.strip() and q not in candidates:
            candidates.append(q.strip())
    tokens = core_tokens(r["name"])
    for q in candidates:
        try:
            hits = query(q)
        except requests.RequestException as e:
            return {"status": "error", "error": str(e)[:120]}
        for hit in hits:
            disp = hit.get("display_name", "")
            if not any(n in disp for n in names):
                continue
            name_match = any(t in (hit.get("name") or "") + disp for t in tokens) if tokens else False
            nums = re.findall(r"\d+(?:-\d+)?", (r.get("address") or r.get("road_address") or ""))
            addr_match = any(n in disp for n in nums) if nums else False
            level = "name_match" if name_match else ("address_match" if addr_match else "weak_match")
            return {"status": "ok", "lat": float(hit["lat"]), "lng": float(hit["lon"]),
                    "match_level": level,
                    "query": q, "matched": disp[:120], "osm_class": hit.get("class"), "osm_type": hit.get("type")}
    return {"status": "no_match"}


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    targets = [r for r in data["records"]
               if r["verification_status"] in ("official_dataset", "official_page_checked")
               and (r.get("latitude") is None or r.get("longitude") is None) and r.get("address")]
    for i, r in enumerate(targets, 1):
        k = key_of(r)
        if k not in cache or cache[k].get("status") == "error" or (cache[k].get("status") == "ok" and "match_level" not in cache[k]):
            cache[k] = try_queries(r)
        if i % 25 == 0:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    c = Counter((v.get("status"), v.get("match_level")) for v in cache.values())
    print(f"대상 {len(targets)}곳 · 결과 {dict(c)} → {CACHE.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
