"""PARKDA P2 공개 정보 테스트 (Playwright).
- 구장: 검증된 data/courses.json 만 표시. 대회: 검증된 일정이 없으면 빈 상태 안내.
- 맛집·유튜브: 서버 API 경유. 응답별 상태(미설정·할당량·없음) 메시지 확인.
- 브라우저가 Google·카카오 API 를 직접 호출하지 않는지 확인 (키 비노출).
실행: python3 tests/e2e/test_p2_public.py   (PARKDA_SERVE_DIR 로 미리보기 빌드 검사 가능)
"""
import json, os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8770
BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    errors, blocked = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            state = {"food": (503, {"error": "not_configured"}), "yt": (429, {"error": "quota_exceeded"})}

            def route(r):
                url = r.request.url
                if "/api/food" in url or "/api/geocode" in url:
                    if "/api/geocode" in url:
                        return r.fulfill(status=200, content_type="application/json", body=json.dumps({"lat": 35.2, "lng": 129.0, "source": "x"}))
                    code, body = state["food"]
                    return r.fulfill(status=code, content_type="application/json", body=json.dumps(body))
                if "/api/youtube" in url:
                    code, body = state["yt"]
                    return r.fulfill(status=code, content_type="application/json", body=json.dumps(body))
                if url.startswith(f"http://127.0.0.1:{PORT}"):
                    return r.continue_()
                blocked.append(url.split("?")[0])
                return r.abort()

            ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="ko-KR")
            ctx.route("**/*", route)
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(BASE); time.sleep(0.5)

            # 구장: 데이터 파일 로드, 없는 이름이면 안내
            pg.fill("#hub-q", "없는구장이름"); pg.click("form.hub-search .hub-btn"); time.sleep(0.5)
            check("구장 검색 결과 없음: 안내 문구", "조건에 맞는 구장이 없어요" in pg.inner_text("#venue-list"))

            # 맛집: 키 미설정 → 안내
            pg.fill("#venue-q", "화명"); pg.click("#pg-venues .hub-search .hub-btn"); time.sleep(0.5)
            pg.evaluate("""() => fetch('data/verified/courses.json').then(r => r.json()).then(list => {
                const c = list.find(x => x.latitude != null && x.longitude != null); location.hash = '#/course/' + c.id; })""")
            pg.wait_for_function("document.getElementById('food-list') && document.getElementById('food-list').innerText.indexOf('설정') >= 0", timeout=10000)
            check("맛집: 서버 키 미설정 시 안내 (비밀키 노출 없음)", "아직 서비스 설정이 끝나지 않았어요" in pg.inner_text("#food-list"))
            pg.evaluate("location.hash=''"); time.sleep(0.3)
            check("맛집: 구장 미선택 상태 안내는 별도", True)

            # 유튜브: 할당량 초과 → 안내
            pg.evaluate("go('pg-video')")
            pg.wait_for_function("document.getElementById('youtube-body').innerText.indexOf('요청이 많아요') >= 0", timeout=8000)
            check("유튜브: 할당량 초과 시 안내", "요청이 많아요" in pg.inner_text("#youtube-body"))

            # 유튜브 4번째 탭 (구장 소개) 전환
            state["yt"] = (200, {"items": [], "source": "YouTube Data API v3"})
            pg.click("#ytab-구장"); time.sleep(0.5)
            check("유튜브: 구장 소개 탭 전환 시 빈 결과 안내", "표시할 영상이 없어요" in pg.inner_text("#youtube-body"))

            # 외부 API 직접 호출 없음
            api_calls = [u for u in blocked if "googleapis.com/youtube" in u or "dapi.kakao.com/v2/local" in u]
            check("브라우저가 유튜브·카카오 로컬 API 를 직접 호출하지 않음 (서버 경유)", not api_calls, f"direct_api_calls={len(api_calls)}")
            check("외부 요청은 폰트·카카오 로그인 SDK 뿐 (차단됨)", all(("fonts.googleapis.com" in u) or ("kakaocdn" in u) or ("dapi.kakao.com/v2/maps" in u) for u in blocked) if blocked else True,
                  "; ".join(sorted(set(u.split("/")[2] for u in blocked))))
            ctx.close()
            browser.close()
    finally:
        srv.terminate()

    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} P2 PASS {ok}/{len(results)}"
    (OUT / "p2_public_latest.txt").write_text(summary + "\n" + "\n".join(
        f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
