"""사용자 흐름 테스트 (실제 브라우저): 비회원 → 경기 → 로그인 → 자동 복귀 → 경기 생성 → 조편성 → 점수 → 홈 → 재진입 → 결과 → 로그아웃 → 게임코드 → 뒤로가기.
외부 요청 차단. 데이터는 이 브라우저(localStorage)에만 있다. 실행: python3 tests/e2e/test_nav_flow.py"""
import os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8783; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
def on(pg, pid): return pg.evaluate(f"document.getElementById('{pid}').classList.contains('on')")
def wait_on(pg, pid, t=8000): pg.wait_for_function(f"document.getElementById('{pid}').classList.contains('on')", timeout=t)

def flow(pg, label, vw):
    pg.goto(BASE); time.sleep(0.5); pg.evaluate("localStorage.clear()"); pg.reload(); time.sleep(0.6)
    # 1. 비회원 홈
    check(f"[{label}] 1 비회원 홈 접속", on(pg, 'pg-home'))
    # 2. 경기 메뉴 → 3. 로그인 화면
    pg.click("#tab-mgmt"); time.sleep(0.3)
    check(f"[{label}] 2-3 경기 메뉴 선택 시 로그인 화면", on(pg, 'pg-login'))
    # 4. 로그인 완료 → 5. 원래 화면(경기관리)으로 자동 이동
    pg.check("#privacy-agree"); pg.fill("#l-name", "가나다"); pg.fill("#l-phone", "010-0000-0000")
    pg.click("button[onclick='doLogin()']"); time.sleep(0.5)
    check(f"[{label}] 4-5 로그인 후 경기관리로 자동 이동", on(pg, 'pg-mgmt'), str([p for p in ['pg-home','pg-mgmt','pg-login'] if on(pg,p)]))
    # 6. 경기 생성
    pg.click("button:has-text('새 경기 만들기')"); time.sleep(0.3)
    pg.fill("#c-title", f"흐름 테스트 {label}"); pg.fill("#c-players", "가나다\n라마바")
    pg.click("button:has-text('경기 만들고 코드 받기')"); time.sleep(0.6)
    check(f"[{label}] 6-7 경기 생성 후 조편성 화면", on(pg, 'pg-groups'))
    # 9. 홈으로 (조편성 화면의 홈 버튼)
    pg.click("#pg-groups .bar-home"); time.sleep(0.3)
    check(f"[{label}] 9 조편성 화면에서 홈으로 이동", on(pg, 'pg-home'))
    # 로그인 상태에서는 경기관리 재진입 시 로그인 화면이 나오지 않는다
    pg.click("#tab-mgmt"); time.sleep(0.3)
    check(f"[{label}] 10 로그인 상태에서 경기관리 재진입 (추가 로그인 없음)", on(pg, 'pg-mgmt'))
    pg.click("#pg-mgmt button:has-text('경기 목록')"); time.sleep(0.4)
    pg.click("#pg-matches button:has-text('점수')"); time.sleep(0.5)
    # 8. 점수 입력 (+ 버튼) 후 홈으로: 저장 대기 중인 입력도 저장되어야 한다
    pg.click("#score-focus .sf-row >> nth=0 >> button[data-sf='1']"); time.sleep(0.1)
    pname = pg.inner_text("#score-focus .sf-row >> nth=0 >> .sf-name").strip()
    val = pg.inner_text("#score-focus .sf-row >> nth=0 >> .sf-num").split("타")[0].strip()
    pg.click("#pg-score .bar-home"); time.sleep(0.4)
    check(f"[{label}] 9 점수 입력 중 홈으로 이동", on(pg, 'pg-home'))
    stored = pg.evaluate(f"(() => {{ const m = S.matches[Object.keys(S.matches)[0]]; return m && m.sd && m.sd[{pname!r}] ? m.sd[{pname!r}][0] : null; }})()")
    check(f"[{label}] 9 홈 이동 시 점수 저장됨", str(stored) == val, f"stored={stored} shown={val}")
    # 11. 다시 경기 진입: 기존 점수 유지
    pg.click("#tab-mgmt"); time.sleep(0.3)
    pg.click("#pg-mgmt button:has-text('경기 목록')"); time.sleep(0.4)
    pg.click("#pg-matches button:has-text('점수')"); time.sleep(0.5)
    again = pg.inner_text("#score-focus .sf-row >> nth=0 >> .sf-num").split("타")[0].strip()
    check(f"[{label}] 11 재진입 후 기존 점수 유지", again == val, f"{again} vs {val}")
    # 12. 결과 확정: 전 홀 입력 후 확정
    par = int(pg.inner_text(".sf-hole small").split()[-1])
    for p in pg.evaluate("S.matches[S.mid].groups[S.cg].players"):
        for h in range(9):
            pg.fill(f"input[data-p='{p}'][data-h='{h}']", str(par))
    pg.click("#pg-score .btn-wrap button:has-text('저장')"); time.sleep(0.5)
    pg.click("#pg-score .btn-wrap button:has-text('포인트 결과')"); time.sleep(0.6)
    pg.click("#final-area button:has-text('결과 확정')"); time.sleep(0.4)
    check(f"[{label}] 12 결과 확정", "1위" in pg.inner_text("#final-area"))
    # 13. 결과 공유 버튼 존재
    check(f"[{label}] 13 결과 공유 기능 존재", pg.locator("#pg-result button:has-text('공유'), #pg-result [onclick*='share']").count() >= 1)
    # 9b. 결과 화면의 내 경기로 / 홈으로
    pg.click("#pg-result .nav-two button:has-text('내 경기로')"); time.sleep(0.4)
    check(f"[{label}] 결과 → 내 경기로 이동", on(pg, 'pg-matches'))
    pg.click("#pg-matches .bar-home"); time.sleep(0.3)
    check(f"[{label}] 목록 → 홈 이동", on(pg, 'pg-home'))
    # 14-15. 로그아웃 → 공개 홈
    pg.click("#tab-my"); time.sleep(0.3)
    pg.once("dialog", lambda d: d.accept())
    pg.click("#pg-my button:has-text('로그아웃')"); time.sleep(0.5)
    check(f"[{label}] 14-15 로그아웃 후 공개 홈 (로그인 화면 아님)", on(pg, 'pg-home') and not on(pg, 'pg-login'))
    # 공개 정보는 로그인 없이 열람
    pg.click("#tab-venues"); time.sleep(0.3)
    check(f"[{label}] 공개 구장 화면은 로그인 없이 열람", on(pg, 'pg-venues'))
    # 16. 게임코드로 직접 접속 → 홈으로 이동 가능
    pg.goto(BASE + "?game=ABCD"); time.sleep(0.8)
    pg.click("#pg-home .hub-brand") if on(pg, 'pg-home') else None
    pg.evaluate("go('pg-matches')"); time.sleep(0.3)
    pg.click("#pg-matches .bar-home"); time.sleep(0.3)
    check(f"[{label}] 16 게임코드 직접 접속 후 홈 이동", on(pg, 'pg-home'))
    # 17. 브라우저 뒤로가기
    pg.click("#tab-venues"); time.sleep(0.3)
    pg.go_back(); time.sleep(0.4)
    check(f"[{label}] 17 브라우저 뒤로가기 → 이전 화면(홈)", on(pg, 'pg-home'))
    check(f"[{label}] 가로 넘침 없음", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); errors = []; blocked = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for label, vw, vh in (("모바일", 390, 844), ("태블릿", 768, 1024), ("PC", 1280, 800)):
                ctx = b.new_context(viewport={"width": vw, "height": vh}, locale="ko-KR")
                def route(r):
                    u = r.request.url
                    if u.startswith(f"http://127.0.0.1:{PORT}"): return r.continue_()
                    blocked.append(u.split("?")[0]); return r.abort()
                ctx.route("**/*", route)
                pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
                flow(pg, label, vw)
                pg.screenshot(path=str(OUT / "design" / f"nav_flow_{label}.png"), full_page=True)
                ctx.close()
            b.close()
    finally:
        srv.terminate()
    other = [u for u in blocked if "fonts.googleapis.com" not in u and "kakao" not in u]
    check("외부 요청 없음", not other, str(other[:3]))
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} NAV PASS {ok}/{len(results)}"
    (OUT / "nav_flow_latest.txt").write_text(summary + "\n" + "\n".join(f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary); return 0 if ok == len(results) else 1
if __name__ == "__main__":
    sys.exit(main())
