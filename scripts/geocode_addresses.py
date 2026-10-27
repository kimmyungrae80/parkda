#!/usr/bin/env python3
"""좌표가 없는 공식 구장의 주소를 OpenStreetMap Nominatim 으로 지오코딩한다.

- 결과는 공식 기관 좌표가 아니므로 coordinate_source='osm_nominatim' 으로 따로 표시한다.
- 응답의 주소(표시 이름)에 구장의 시도 이름이 없으면 버린다 (다른 지역으로 잘못 찾은 경우 방지).
- 요청은 1.1초 간격, User-Agent 명시. 결과는 캐시에 저장해 재실행 시 다시 요청하지 않는다.
- 이용 조건: ODbL — 화면에 "© OpenStreetMap contributors" 를 표시해야 한다.
사용법: python3 scripts/geocode_addresses.py
"""
import json, sys, time, urllib.parse
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


def key_of(r):
    return f"{r.get('region')}|{r['name']}|{r.get('address')}"


def query(address):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": address, "format": "json", "limit": 1, "countrycodes": "kr", "addressdetails": 1})
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ko"}, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    targets = [r for r in data["records"]
               if r["verification_status"] in ("official_dataset", "official_page_checked")
               and (r.get("latitude") is None or r.get("longitude") is None) and r.get("address")]
    done = 0
    for r in targets:
        k = key_of(r)
        if k in cache:
            continue
        address = r["address"].split(",")[0].strip()
        try:
            hits = query(address)
            time.sleep(1.1)
        except requests.RequestException as e:
            cache[k] = {"status": "error", "error": str(e)[:120]}
            continue
        names = REGION_NAMES.get(r.get("region"), [])
        hit = hits[0] if hits else None
        if hit and any(n in hit.get("display_name", "") for n in names):
            cache[k] = {"status": "ok", "lat": float(hit["lat"]), "lng": float(hit["lon"]),
                        "matched": hit["display_name"][:120], "osm_class": hit.get("class"), "osm_type": hit.get("type")}
            done += 1
        else:
            cache[k] = {"status": "no_match"}
        if (done and done % 25 == 0):
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for v in cache.values() if v.get("status") == "ok")
    print(f"대상 {len(targets)}곳 · 캐시 {len(cache)}건 · 좌표 확보 {ok}건 → {CACHE.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
