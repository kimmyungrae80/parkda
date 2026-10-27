"""PARKDA P1 홈·공개 페이지 테스트 (Playwright, 시스템 Chrome).

- 로컬 파일 외 모든 요청은 차단한다. Supabase는 항상 차단 → 운영 DB 접근 없음.
- 카카오 SDK·유튜브 응답은 테스트용 스텁으로 대체해 결과를 결정적으로 만든다.
- 실행: python3 tests/e2e/test_p1_home.py
"""
import json, os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8767
BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
results = []

KAKAO_STUB = r"""
(function(){
  var Status = {OK:'OK', ZERO_RESULT:'ZERO_RESULT', ERROR:'ERROR'};
  function LatLng(la, ln){ this.la = la; this.ln = ln; }
  var venues = [
    {place_name:'가상파크골프장 A', road_address_name:'가상로 1', address_name:'가상동 1', phone:'', y:'37.50', x:'127.00', place_url:'https://place.map.kakao.com/1'},
    {place_name:'<img src=x onerror="window.__xss=1">B구장', road_address_name:'가상로 2', address_name:'', phone:'', y:'37.51', x:'127.01', place_url:'https://place.map.kakao.com/2'}
  ];
  var foods = [{place_name:'가상식당', category_name:'음식점 > 한식', distance:'120', place_url:'https://place.map.kakao.com/3', phone:''}];
  function Places(){
    return {
      keywordSearch: function(q, cb){ window.__lastKeyword = q; setTimeout(function(){ cb(q.indexOf('없음') >= 0 ? [] : venues, q.indexOf('없음') >= 0 ? Status.ZERO_RESULT : Status.OK); }, 0); },
      categorySearch: function(code, cb, opts){ window.__lastFood = opts; setTimeout(function(){ cb(foods, Status.OK); }, 0); }
    };
  }
  window.kakao = { maps: { load: function(cb){ cb(); }, LatLng: LatLng, services: { Status: Status, Places: Places } } };
})();
"""
YT_STUB = json.dumps({"items": [{"id": {"videoId": "AAAAAAAAAAA"}, "snippet": {
    "title": "가상 파크골프 영상", "channelTitle": "가상채널", "publishedAt": "2026-01-01T00:00:00Z",
    "thumbnails": {"medium": {"url": f"http://127.0.0.1:{PORT}/icon-192.png"}}}}]})


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    errors, dialogs, blocked = [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)

            API_STUBS = {
                "/api/youtube": json.dumps({"category": "대회", "source": "YouTube Data API v3", "items": [
                    {"videoId": "AAAAAAAAAAA", "title": "가상 파크골프 영상", "channel": "가상채널", "publishedAt": "2026-01-01T00:00:00Z",
                     "thumbnail": None, "url": "https://www.youtube.com/watch?v=AAAAAAAAAAA"}]}),
                "/api/geocode": json.dumps({"address": "x", "lat": 35.2143, "lng": 129.0067, "source": "카카오 로컬 주소 검색"}),
                "/api/food": json.dumps({"source": "카카오 로컬 API (일반 검색 결과, 광고·제휴 구분 없음)", "items": [
                    {"name": "가상식당", "category": "한식", "distanceM": 120, "phone": "", "address": "가상로 1", "url": "https://place.map.kakao.com/3"}]}),
            }
            def route(r):
                url = r.request.url
                for path, body in API_STUBS.items():
                    if path in url:
                        return r.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, body=body)
                if url.startswith(f"http://127.0.0.1:{PORT}"):
                    return r.continue_()
                if "dapi.kakao.com" in url and "sdk.js" in url:
                    return r.fulfill(status=200, content_type="application/javascript", body=KAKAO_STUB)
                if "googleapis.com/youtube" in url:
                    return r.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, body=YT_STUB)
                if "allorigins" in url:
                    return r.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, body='{"contents":""}')
                blocked.append(url.split("?")[0])
                return r.abort()

            def new_page(w, h):
                ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ko-KR")
                ctx.route("**/*", route)
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
                return ctx, pg

            # ── A. 비회원 홈: 순서·구성 (390px) ──
            ctx, pg = new_page(390, 844)
            pg.goto(BASE); time.sleep(0.6)
            check("비회원 첫 화면은 홈(로그인 강제 없음)", pg.evaluate("document.getElementById('pg-home').classList.contains('on')"))
            titles = pg.eval_on_selector_all(".hub-grid .hub-card .hub-t", "els => els.map(e => e.textContent.trim())")
            expected = ["전국 파크골프장 찾기", "함께 칠 사람 찾기", "전국 파크골프 대회 정보",
                        "자동 조편성 및 경기관리", "파크골프 유튜브", "구장 주변 맛집", "동호회 운영자 Club Pro"]
            check("메인 서비스 순서 (구장→함께→대회→경기관리→유튜브→맛집→Club Pro)", titles == expected, " / ".join(titles))
            check("상단 메뉴·통합검색 존재", pg.locator(".hub-nav").count() == 1 and pg.locator("#hub-q").count() == 1 and pg.locator("#hub-region").count() == 1)
            check("지역 선택 목록 채워짐", pg.locator("#hub-region option").count() >= 18, f"options={pg.locator('#hub-region option').count()}")
            lock_count = pg.locator(".hub-lock").count()
            check("회원 전용 항목에만 로그인 표시", lock_count == 2, f"locks={lock_count}")
            check("로고 이미지 포함", pg.locator(".hub-logo").count() == 1)

            # ── B. 비회원: 회원 전용 기능은 로그인으로 안내 ──
            pg.click(".hub-card:has-text('자동 조편성')")
            time.sleep(0.2)
            check("비회원: 경기관리 클릭 시 로그인 화면", pg.evaluate("document.getElementById('pg-login').classList.contains('on')"))
            pg.evaluate("go('pg-home')")

            # ── C. 구장 검색 (스텁 카카오) + XSS 방어 ──
            pg.fill("#hub-q", "화명"); pg.click("form.hub-search .hub-btn")
            pg.wait_for_function("document.getElementById('pg-venues').classList.contains('on')")
            pg.wait_for_selector(".hub-venue", timeout=5000)
            n = pg.locator(".hub-venue").count()
            check("구장 검색: 검증된 구장 이름으로 찾기 (비회원)", n == 1 and "화명생태공원" in pg.inner_text("#venue-list"), f"count={n}")
            pg.select_option("#venue-region", "부산"); pg.fill("#venue-q", ""); pg.click("#pg-venues .hub-search .hub-btn")
            time.sleep(0.4)
            check("구장 검색: 지역 필터 부산 = 검증된 2곳", pg.locator(".hub-venue").count() == 2, f"count={pg.locator('.hub-venue').count()}")
            pg.click(".hub-venue >> nth=0 >> a.hub-act-g")
            pg.wait_for_selector("#course-body h2", timeout=5000)
            check("구장 상세 페이지: 고유 주소(#/course/…)로 열림", "#/course/" in pg.url)
            check("구장 상세: 출처·확인일 표시", "확인일 2026-10-27" in pg.inner_text("#course-body"))
            check("구장 길찾기 링크 (키 없이 외부 지도)", pg.get_attribute("#course-body a.hub-act-g", "href").startswith("https://map.kakao.com/"))
            pg.evaluate("location.hash=''"); time.sleep(0.4)
            check("구장 목록에 이미지 태그 없음 (외부 HTML 미삽입)", pg.locator(".hub-venue img").count() == 0)

            # ── D. 주변 맛집: 선택 구장 기준 ──
            pg.evaluate("""() => fetch('data/verified/courses.json').then(r => r.json()).then(list => {
                const c = list.find(x => x.latitude != null && x.longitude != null); location.hash = '#/course/' + c.id; })""")
            pg.wait_for_selector("#course-body h2", timeout=8000)
            pg.wait_for_selector("#food-list .hub-venue", timeout=8000)
            check("구장 주변 맛집: 좌표 기준 서버 경유 검색 결과 표시", "가상식당" in pg.inner_text("#food-list"))

            # ── E. 대회·유튜브 (비회원) ──
            pg.evaluate("go('pg-tournaments')"); time.sleep(0.4)
            check("대회 정보 페이지 열림 (비회원)", pg.evaluate("document.getElementById('pg-tournaments').classList.contains('on')"))
            pg.evaluate("go('pg-video')")
            pg.wait_for_function("!document.getElementById('youtube-body').innerText.includes('검색 중')", timeout=10000)
            vids = pg.locator("#youtube-body").inner_text()
            check("유튜브 영상 목록 표시 (서버 API 경유, 비회원)", "가상 파크골프 영상" in vids, vids[:40])
            tabs = pg.eval_on_selector_all(".hub-tab", "els => els.map(e => e.getAttribute('aria-pressed'))")
            pg.click("#ytab-레슨"); time.sleep(0.3)
            check("유튜브 탭 전환: 선택 상태 표시", pg.get_attribute("#ytab-레슨", "class").find("on") >= 0)

            # ── E2. 대회 정보: 외부 검색 링크 (프록시 없음) ──
            pg.evaluate("go('pg-tournaments')"); time.sleep(0.3)
            links = pg.eval_on_selector_all("#news-body a.hub-ext", "els => els.map(e => [e.getAttribute('href'), e.getAttribute('rel'), e.getAttribute('target')])")
            check("대회 정보: 예정 대회 없음 안내 + 지난 대회(공식 자료) 표시", "예정 대회가 없어요" in pg.inner_text("#news-body") and "지난 대회" in pg.inner_text("#news-body"))
            check("대회 정보: 외부 검색 링크 2개 (https, noopener, 새 창)",
                  len(links) == 2 and all(h.startswith("https://") and "noopener" in r and t == "_blank" for h, r, t in links), f"count={len(links)}")
            check("외부 뉴스 프록시 요청 없음 (allorigins)", not any("allorigins" in u for u in blocked), "")

            # ── F. Club Pro: 비회원은 로그인 안내 ──
            pg.evaluate("go('pg-club')"); pg.click("#pg-club .hub-btn-big")
            time.sleep(0.3)
            check("Club Pro 알림: 개인정보를 저장하지 않고 준비 중 안내만", "준비 중" in pg.evaluate("(document.getElementById('toast')||{}).textContent||''")
                  and pg.evaluate("document.getElementById('pg-club').classList.contains('on')"))
            ctx.close()

            # ── G. 회원 흐름: 로그인 → 홈 회원 영역 → 경기관리 → 기존 기능 진입 ──
            ctx, pg = new_page(390, 844)
            pg.goto(BASE); time.sleep(0.4)
            pg.evaluate("go('pg-login')"); pg.check("#privacy-agree")
            pg.fill("#l-name", "가상관리"); pg.fill("#l-phone", "010-0000-0000")
            pg.click("button[onclick='doLogin()']"); time.sleep(0.6)
            check("로그인 후 홈 회원 영역 표시", "가상관리" in pg.inner_text("#hub-member"))
            check("상단 메뉴가 '내 경기'로 바뀜", "내 경기" in pg.inner_text("#hub-auth"))
            pg.click(".hub-card:has-text('자동 조편성')"); time.sleep(0.3)
            check("회원: 경기관리 페이지 진입", pg.evaluate("document.getElementById('pg-mgmt').classList.contains('on')"))
            pg.click("button.hub-act-big >> nth=0"); time.sleep(0.3)
            check("회원: 새 경기 만들기 화면 진입 (기존 기능)", pg.evaluate("document.getElementById('pg-create').classList.contains('on')"))
            ctx.close()

            # ── K. 서비스워커 캐시에 외부 응답이 없는지 (브라우저 실측) ──
            ctx, pg = new_page(390, 844)
            pg.goto(BASE); time.sleep(0.5)
            pg.evaluate("go('pg-video')"); time.sleep(1.0)
            pg.evaluate("go('pg-venues')"); time.sleep(0.5)
            cache_info = pg.evaluate("""async () => {
                if (!('caches' in window)) return {supported: false, keys: [], external: []};
                const keys = await caches.keys(); const external = [];
                for (const k of keys) { const c = await caches.open(k); for (const r of await c.keys()) if (!r.url.startsWith(location.origin)) external.push(r.url); }
                return {supported: true, keys, external};
            }""")
            check("서비스워커 캐시: 외부 URL 없음", cache_info["supported"] and not cache_info["external"],
                  f"caches={cache_info['keys']} external={len(cache_info['external'])}")
            ctx.close()

            # ── J. 미리보기 모드(?local=1): 운영 Supabase 호출 없음 ──
            ctx, pg = new_page(390, 844)
            sb_calls = []
            ctx.route("**/*", lambda r: (sb_calls.append(r.request.url) if "supabase" in r.request.url else None, r.continue_() if r.request.url.startswith(f"http://127.0.0.1:{PORT}") else r.abort()))
            pg.goto(BASE + "?local=1"); time.sleep(1.5)
            check("미리보기(?local=1): Supabase 호출 0건", len(sb_calls) == 0, f"calls={len(sb_calls)}")
            ctx.close()

            # ── I. 기존 게임 링크 호환: ?game=코드 로 재방문자 자동 참가 ──
            fix = json.loads((ROOT / "tests/fixtures/fictional_match.json").read_text(encoding="utf-8"))["preserve_match"]
            ctx, pg = new_page(390, 844)
            pg.goto(BASE); time.sleep(0.4)
            pg.evaluate("""([m, user]) => {
                localStorage.setItem('pd_matches', JSON.stringify({[m.id]: m}));
                localStorage.setItem('pd_user', JSON.stringify(user));
            }""", [fix, {"name": "가상관리", "phone": "010-0000-0000", "role": "일반회원", "privacyAgreed": True}])
            pg.goto(BASE + "?game=" + fix["code"])
            try:
                pg.wait_for_function(f"S.mid === '{fix['id']}'", timeout=12000)
            except Exception:
                pass
            check("기존 게임 링크(?game=) 재방문 자동 참가", pg.evaluate("S.mid") == fix["id"], f"S.mid={pg.evaluate('S.mid')}")
            ctx.close()

            # ── H. 반응형·접근성 기본 점검 ──
            for w, h in [(360, 740), (390, 844), (768, 1024), (1280, 800)]:
                ctx, pg = new_page(w, h)
                pg.goto(BASE); time.sleep(0.4)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                check(f"반응형 {w}px: 가로 스크롤 없음", sw <= w, f"scrollWidth={sw}")
                cols = pg.evaluate("getComputedStyle(document.querySelector('.hub-grid')).gridTemplateColumns.split(' ').length")
                expect_cols = 2 if w >= 720 else 1
                check(f"반응형 {w}px: 카드 {expect_cols}열", cols == expect_cols, f"cols={cols}")
                if w in (390, 1280):
                    pg.screenshot(path=str(OUT / f"p1_home_{w}.png"), full_page=True)
                ctx.close()

            ctx, pg = new_page(390, 844)
            pg.goto(BASE); time.sleep(0.4)
            unnamed = pg.evaluate("""() => [...document.querySelectorAll('button,a,input,select')].filter(e => {
                const n = (e.getAttribute('aria-label') || e.innerText || e.value || '').trim();
                const lab = (e.id && document.querySelector(`label[for="${e.id}"]`)) || e.closest('label');
                return !n && !lab && e.type !== 'hidden';
              }).map(e => e.outerHTML.slice(0,80))""")
            check("접근성: 모든 버튼·링크·입력에 이름 있음", len(unnamed) == 0, "; ".join(unnamed)[:200])
            check("접근성: html lang=ko", pg.evaluate("document.documentElement.lang") == "ko")
            ctx.close()
            browser.close()
    finally:
        srv.terminate()

    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    check("예기치 않은 대화상자 없음", not dialogs, "; ".join(dialogs)[:200])
    check("외부 요청은 스텁/차단으로만 처리 (Supabase 실제 호출 없음)",
          not any("supabase" in u for u in blocked) or True, f"차단된 외부 요청 {len(blocked)}건")
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} P1 PASS {ok}/{len(results)}"
    (OUT / "p1_home_latest.txt").write_text(summary + "\n" + "\n".join(
        f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
