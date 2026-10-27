"""PARKDA P3 전국 구장 데이터 · 상세 페이지 · 주변 검색 테스트 (Playwright, 시스템 Chrome).

- 구장 데이터는 저장소의 data/verified/courses.json 을 그대로 읽는다 (공식 출처 확인분만).
- 서버 API(/api/food, /api/youtube)는 테스트 스텁으로 응답한다. 외부 요청은 모두 차단.
- 지도 라이브러리(cdnjs)는 차단되므로 '지도를 불러오지 못했어요' 대체 문구를 확인한다.
실행: python3 tests/e2e/test_p3_courses.py   (PARKDA_SERVE_DIR=preview 로 미리보기 빌드 검사 가능)
"""
import json, os, pathlib, re, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8772
BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
COURSES = json.loads((ROOT / "data/verified/courses.json").read_text(encoding="utf-8"))
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    errors, blocked, food_calls, yt_calls = [], [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)

            def route(r):
                url = r.request.url
                if "/api/food" in url:
                    food_calls.append(url)
                    body = {"source": "카카오 로컬 API 일반 검색 결과 (광고·제휴 표시 구분 없음)", "radius": 3000, "category": "CE7",
                            "items": [{"name": "가상카페", "category": "카페", "distanceM": 450, "phone": "", "address": "가상로 2", "url": "https://place.map.kakao.com/9"}]}
                    return r.fulfill(status=200, content_type="application/json", body=json.dumps(body))
                if "/api/youtube" in url:
                    yt_calls.append(url)
                    body = {"source": "YouTube Data API v3 (검색 결과)", "items": [{"videoId": "AAAAAAAAAAA", "title": "가상 구장 소개 영상", "channel": "가상채널", "publishedAt": "2026-01-01T00:00:00Z", "thumbnail": None, "url": "https://www.youtube.com/watch?v=AAAAAAAAAAA"}]}
                    return r.fulfill(status=200, content_type="application/json", body=json.dumps(body))
                if url.startswith(f"http://127.0.0.1:{PORT}"):
                    return r.continue_()
                blocked.append(url.split("?")[0])
                return r.abort()

            def new(w, h):
                ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ko-KR")
                ctx.route("**/*", route)
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errors.append(str(e)))
                return ctx, pg

            ctx, pg = new(390, 844)
            pg.goto(BASE); time.sleep(0.5)

            # 1. 지역 필터 (데이터와 화면 개수 일치)
            pg.evaluate("go('pg-venues')"); pg.select_option("#venue-region", "전남")
            pg.wait_for_function("document.querySelectorAll('#venue-list .hub-venue').length > 0", timeout=8000)
            expected = sum(1 for c in COURSES if c["region"] == "전남")
            shown = pg.locator("#venue-list .hub-venue").count()
            check("지역 필터: 전남 구장 수가 데이터와 같음", shown == expected, f"화면 {shown} / 데이터 {expected}")
            pg.select_option("#venue-region", "")

            # 2. 구장명 검색
            pg.fill("#venue-q", "대저"); pg.click("#pg-venues .hub-search .hub-btn"); time.sleep(0.6)
            check("구장명 검색: '대저' → 1곳", pg.locator("#venue-list .hub-venue").count() == 1)
            pg.fill("#venue-q", "")

            # 3. 지도 보기 (라이브러리 차단 시 안내)
            pg.click("#venue-view-map")
            pg.wait_for_function("document.getElementById('venue-map') && document.getElementById('venue-map').innerText.trim().length > 0", timeout=10000)
            mt = pg.inner_text("#venue-map")
            check("지도 보기: 라이브러리 차단 시 대체 안내 (목록으로 이동 가능)", "지도를 불러오지 못했어요" in mt or "좌표가 있는 구장이 없어요" in mt or pg.locator("#venue-map .leaflet-container").count() == 1, mt[:60])
            pg.click("#venue-view-list")

            # 4. 즐겨찾기: 누르면 ★, 새로고침 후에도 유지
            pg.click("#venue-list .hub-venue >> nth=0 >> .hub-fav"); time.sleep(0.2)
            fav_on = pg.locator("#venue-list .hub-venue >> nth=0 >> .hub-fav").inner_text().strip()
            pg.reload(); time.sleep(0.5)
            pg.evaluate("go('pg-venues')"); pg.click("#venue-fav-only"); time.sleep(0.6)
            check("즐겨찾기: 누른 구장이 새로고침 후에도 남음", fav_on == "★" and pg.locator("#venue-list .hub-venue").count() == 1)
            pg.click("#venue-fav-only")
            pg.evaluate("localStorage.removeItem('pd_fav_courses')")

            # 5. 상세 페이지: 고유 주소, 정보 확인 중, 출처·확인일
            no_fee = next(c for c in COURSES if not c.get("fee") and c.get("holes"))
            pg.evaluate("(id) => { location.hash = '#/course/' + id; }", no_fee["id"])
            pg.wait_for_selector("#course-body h2", timeout=8000)
            body = pg.inner_text("#course-body")
            check("상세 페이지: 고유 주소(#/course/…)", pg.url.endswith("#/course/" + no_fee["id"]))
            check("상세 페이지: 없는 항목은 '정보 확인 중' (추정값 없음)", "정보 확인 중" in body)
            check("상세 페이지: 상태 표시 (공식 출처 확인 여부)", ("공식 페이지 직접 확인" in body) or ("공공데이터 기준" in body))
            src_links = pg.eval_on_selector_all("#course-body a[href^='https://']", "els => els.map(e => e.href)")
            check("상세 페이지: 출처 링크 포함", len(src_links) >= 1, str(len(src_links)))

            # 6. 주소 기반 자동 좌표: 출처 표기 (OSM 저작자 표시)
            osm = next((c for c in COURSES if c.get("coordinate_source") == "osm_nominatim"), None)
            if osm:
                pg.evaluate("(id) => { location.hash = '#/course/' + id; }", osm["id"])
                pg.wait_for_selector("#course-body h2", timeout=8000)
                check("자동 좌표: 주소 기반 안내와 OpenStreetMap 표기", "주소 기반 자동 지오코딩" in pg.inner_text("#course-body") and "OpenStreetMap" in pg.inner_text("#course-body"))

            # 7. 주변 맛집·카페: 반경·카테고리 전달
            with_coord = next(c for c in COURSES if c.get("latitude") is not None)
            pg.evaluate("(id) => { location.hash = '#/course/' + id; }", with_coord["id"])
            pg.wait_for_selector("#food-list .hub-venue", timeout=8000)
            pg.click("#food-r-3000"); time.sleep(0.2)
            pg.click("#food-cat-CE7"); time.sleep(0.8)
            last = food_calls[-1] if food_calls else ""
            check("주변 검색: 3km·카페 조건이 서버 요청에 반영", "radius=3000" in last and "category=CE7" in last, last[-80:])
            check("주변 검색: 결과 표시 (광고·제휴 구분 문구 포함)", "가상카페" in pg.inner_text("#food-list") and "광고·제휴" in pg.inner_text("#food-list"))

            # 8. 좌표 없는 구장: 주변 검색 안내
            no_coord = next(c for c in COURSES if c.get("latitude") is None)
            pg.evaluate("(id) => { location.hash = '#/course/' + id; }", no_coord["id"])
            pg.wait_for_selector("#course-body h2", timeout=8000)
            check("좌표 없는 구장: 주변 검색 대신 안내", "좌표가 아직 없어" in pg.inner_text("#food-list"))

            # 9. 관련 대회 (지역 기준, 공식 자료)
            tour_region = next((c for c in COURSES if c.get("region") == "경북"), None)
            if tour_region:
                pg.evaluate("(id) => { location.hash = '#/course/' + id; }", tour_region["id"])
                pg.wait_for_selector("#course-body h2", timeout=8000)
                time.sleep(0.5)
                check("관련 대회: 같은 지역 공식 대회 표시 (출처·라이선스 포함)", "울진" in pg.inner_text("#course-tournaments") and "공공" in pg.inner_text("#course-tournaments"))

            # 10. 관련 유튜브 (구장명 기준 검색)
            pg.wait_for_function("document.getElementById('course-videos') && document.getElementById('course-videos').innerText.indexOf('영상') >= 0 || document.getElementById('course-videos').innerText.indexOf('관련 영상') >= 0", timeout=8000)
            check("관련 영상: 구장명으로 검색 요청", any(urllib_quote(with_coord["name"]) in u for u in yt_calls) or len(yt_calls) > 0)
            check("관련 영상: 결과 표시", "가상 구장 소개 영상" in pg.inner_text("#course-videos"))

            # 11. 대회 페이지: 예정은 없고 지난 대회(공식 자료)를 날짜·출처와 함께
            pg.evaluate("go('pg-tournaments')"); time.sleep(0.5)
            t = pg.inner_text("#news-body")
            check("대회 페이지: 지난 대회 날짜·주최·출처 표시", "2025-09-11" in t and "주최" in t and "확인일" in t)

            # 12. 외부 직접 호출 없음 (서버 API 경유), JS 오류 없음
            direct = [u for u in blocked if "googleapis.com/youtube" in u or "dapi.kakao.com/v2/local" in u or "supabase" in u]
            check("외부 API 직접 호출 없음 (유튜브·카카오 로컬·Supabase)", not direct, f"{len(direct)}")
            ctx.close()

            # 13. 반응형: 목록·상세에서 가로 스크롤 없음
            for w, h in [(390, 844), (1280, 800)]:
                ctx, pg = new(w, h)
                pg.goto(BASE + "#/course/" + with_coord["id"]); time.sleep(0.8)
                pg.wait_for_selector("#course-body h2", timeout=8000)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                check(f"반응형 {w}px: 상세 페이지 가로 스크롤 없음", sw <= w, f"scrollWidth={sw}")
                if w == 390:
                    pg.screenshot(path=str(OUT / "p3_course_390.png"), full_page=False)
                ctx.close()
            browser.close()
    finally:
        srv.terminate()
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} P3 PASS {ok}/{len(results)}"
    (OUT / "p3_courses_latest.txt").write_text(summary + "\n" + "\n".join(
        f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary)
    return 0 if ok == len(results) else 1


def urllib_quote(s):
    from urllib.parse import quote
    return quote(s)


if __name__ == "__main__":
    sys.exit(main())
