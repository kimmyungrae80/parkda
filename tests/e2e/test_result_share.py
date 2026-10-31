"""결과·공유·조편성 화면 테스트 (실제 브라우저, 390·768·1280). 카카오 SDK 는 외부 요청이라 차단되므로
공유는 '복사 대체 경로'까지만 검증한다. 실제 카카오톡 앱 공유는 미검증으로 표시한다.
실행: python3 tests/e2e/test_result_share.py"""
import os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8787; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
def on(pg, pid): return pg.evaluate(f"document.getElementById('{pid}').classList.contains('on')")
def login(pg, name):
    pg.evaluate("n => localStorage.setItem('pd_user', JSON.stringify({name: n, phone: '010-0000-0000', role: '일반회원', privacyAgreed: true}))", name)

def flow(pg, label):
    pg.goto(BASE); time.sleep(0.5); pg.evaluate("localStorage.clear()")
    login(pg, "가나다"); pg.reload(); pg.wait_for_function("document.getElementById('pg-home').classList.contains('on')", timeout=20000)
    pg.evaluate("go('pg-create')"); time.sleep(0.4)
    pg.fill("#c-title", f"결과 테스트 {label}"); pg.fill("#c-players", "가나다\n라마바")
    pg.click("button:has-text('경기 만들고 코드 받기')"); time.sleep(0.8)
    # 조편성 화면
    check(f"[{label}] 조편성: 확정 상태 표시 (미확정)", "확정하고" in pg.inner_text("#groups-area") or "확인하고" in pg.inner_text("#groups-area"))
    check(f"[{label}] 조편성: '다시 섞기' 버튼 1개 (중복 없음)", pg.locator("#pg-groups button:has-text('다시 섞기')").count() == 1)
    check(f"[{label}] 조편성: 조마다 인원 표시", "명" in pg.inner_text("#groups-area"))
    pg.click("#group-edit button:has-text('조편성 확정')"); time.sleep(0.3)
    check(f"[{label}] 조편성 확정 후 상태 문구 변경", "확정되었어요" in pg.inner_text("#groups-area"))
    check(f"[{label}] 확정 후 다시 섞기 비활성", pg.locator("#reshuffle-btn").is_disabled())
    pg.click("#group-edit button:has-text('확정 취소')"); time.sleep(0.3)
    check(f"[{label}] 확정 취소 후 다시 섞기 활성", pg.locator("#reshuffle-btn").is_enabled())
    pg.screenshot(path=str(OUT / "design" / f"groups_{label}.png"), full_page=True)
    # 점수 입력 (동점 만들기: 두 명 모두 4타)
    pg.click("#pg-groups button:has-text('점수 입력 시작')"); time.sleep(0.5)
    par = int(pg.inner_text(".sf-hole small").split()[-1])
    for p in pg.evaluate("S.matches[S.mid].groups[S.cg].players"):
        for h in range(9):
            pg.fill(f"input[data-p='{p}'][data-h='{h}']", "4")
    pg.click("#pg-score .btn-wrap button:has-text('저장')"); time.sleep(0.5)
    pg.click("#pg-score .btn-wrap button:has-text('포인트 결과')"); time.sleep(0.8)
    check(f"[{label}] 결과 화면 진입", on(pg, 'pg-result'))
    summ = pg.inner_text("#result-summary")
    check(f"[{label}] 최종 순위 표시", "최종 순위" in summ)
    check(f"[{label}] 동점은 공동 순위로 표시", summ.count("공동 1위") == 2, summ[:120])
    check(f"[{label}] 참가자별 총점 표시", "36타" in summ)
    check(f"[{label}] 홀별 점수 (참가자당 9홀)", pg.locator("#result-summary .rs-holes li").count() == 18)
    check(f"[{label}] 카카오톡 공유 버튼 강조(노란색 클래스)", pg.locator("#result-share-card .result-kakao").count() == 1)
    pg.click("#result-share-card button:has-text('결과 링크 복사')"); time.sleep(0.4)
    st = pg.inner_text("#share-status")
    check(f"[{label}] 결과 링크 복사 안내", "복사" in st, st)
    pg.click("#result-share-card .result-kakao"); time.sleep(0.4)
    st = pg.inner_text("#share-status")
    check(f"[{label}] 카카오 SDK 없음 → 복사 대체 안내 (실제 카카오 공유는 미검증)", "복사" in st and "카카오" in st, st)
    check(f"[{label}] 내 경기로·홈으로 버튼", pg.locator("#pg-result .nav-two button").count() == 2)
    check(f"[{label}] 가로 넘침 없음 (결과)", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
    pg.screenshot(path=str(OUT / "design" / f"result_{label}.png"), full_page=True)
    # 공유 링크 접근: 같은 기기에서 게임코드 링크로 열면 결과 화면
    code = pg.evaluate("S.matches[S.mid].code")
    pg.goto(BASE + f"?game={code}"); time.sleep(0.8)
    pg.wait_for_function("document.getElementById('pg-home').classList.contains('on') || document.getElementById('pg-result').classList.contains('on')", timeout=20000)
    time.sleep(1.8)
    check(f"[{label}] 게임코드 링크 → 끝난 경기는 결과 화면", on(pg, 'pg-result'), str([p for p in ['pg-home','pg-result','pg-score'] if on(pg,p)]))
    # 게임코드 링크 호환: 진행 중 경기 링크는 점수 화면 (새 경기 생성 후)
    pg.evaluate("go('pg-create')"); time.sleep(0.3)
    pg.fill("#c-title", f"진행 중 {label}"); pg.fill("#c-players", "가나다\n라마바")
    pg.click("button:has-text('경기 만들고 코드 받기')"); time.sleep(0.6)
    code2 = pg.evaluate("S.matches[S.mid].code")
    pg.goto(BASE + f"?game={code2}"); time.sleep(0.8)
    pg.wait_for_function("document.getElementById('pg-score').classList.contains('on') || document.getElementById('pg-groups').classList.contains('on') || document.getElementById('pg-result').classList.contains('on') || document.getElementById('pg-home').classList.contains('on')", timeout=20000)
    time.sleep(1.8)
    check(f"[{label}] 게임코드 링크 → 진행 중 경기는 점수 화면", on(pg, 'pg-score'), str([p for p in ['pg-home','pg-score','pg-groups','pg-result'] if on(pg,p)]))

def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); errors = []; blocked = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for label, vw, vh in (("모바일", 390, 844), ("태블릿", 768, 1024), ("PC", 1280, 800)):
                ctx = b.new_context(viewport={"width": vw, "height": vh}, locale="ko-KR", permissions=["clipboard-read", "clipboard-write"])
                def route(r):
                    u = r.request.url
                    if u.startswith(f"http://127.0.0.1:{PORT}"): return r.continue_()
                    blocked.append(u.split("?")[0]); return r.abort()
                ctx.route("**/*", route)
                pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
                flow(pg, label); ctx.close()
            b.close()
    finally:
        srv.terminate()
    other = [u for u in blocked if "fonts.googleapis.com" not in u and "kakao" not in u]
    check("외부 요청 없음 (폰트·카카오 SDK 제외)", not other, str(other[:3]))
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} RESULT PASS {ok}/{len(results)}"
    (OUT / "result_share_latest.txt").write_text(summary + "\n" + "\n".join(f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary); return 0 if ok == len(results) else 1
if __name__ == "__main__":
    sys.exit(main())
