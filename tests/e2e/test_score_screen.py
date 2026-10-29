"""점수 입력 화면 테스트 (Playwright). 경기 만들기 → 점수 입력 → +/− · 홀 이동 · 자동 저장 · 중단 시 차단 · 결과 확정까지.
데이터는 이 브라우저(localStorage)에만 있다. 외부 요청 차단. 실행: python3 tests/e2e/test_score_screen.py"""
import os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8780; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
PHONE = "010-0000-0000"
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
def run(pg, label, vw):
    pg.evaluate("""() => localStorage.setItem('pd_user', JSON.stringify({name: '가나다', phone: '010-0000-0000', role: '일반회원', privacyAgreed: true}))""")
    pg.goto(BASE); pg.wait_for_function("document.getElementById('pg-home').classList.contains('on')", timeout=20000)
    pg.evaluate("go('pg-create')"); time.sleep(0.4)
    pg.fill("#c-title", f"점수 테스트 {label}")
    pg.fill("#c-players", "가나다\n라마바")
    pg.click("button:has-text('경기 만들고 코드 받기')"); time.sleep(0.8)
    pg.evaluate("go('pg-matches')"); time.sleep(0.4)
    pg.click("#pg-matches button:has-text('점수')"); time.sleep(0.6)
    focus = pg.inner_text("#score-focus")
    check(f"[{label}] 현재 홀과 참가자 이름 표시", "1" in focus and "홀" in focus and "가나다" in focus and "라마바" in focus)
    par_txt = pg.inner_text(".sf-hole small")
    check(f"[{label}] 파(PAR) 표시", par_txt.startswith("PAR"), par_txt)
    # +/- 큰 버튼: 가나다 1홀을 파 기준으로 두 번 올리고 한 번 내린다
    P = pg.inner_text("#score-focus .sf-row >> nth=0 >> .sf-name").strip()  # 조편성은 무작위 순서이므로 첫 행의 이름을 쓴다
    row = "#score-focus .sf-row >> nth=0"
    pg.click(f"{row} >> button[data-sf='1']"); time.sleep(0.2)
    pg.click(f"{row} >> button[data-sf='1']"); time.sleep(0.2)
    pg.click(f"{row} >> button[data-sf='-1']"); time.sleep(0.2)
    val = pg.inner_text(f"{row} >> .sf-num").split("타")[0].strip()
    par = int(pg.inner_text(".sf-hole small").split()[-1])
    check(f"[{label}] +/- 로 타수 변경 (파+1 기대)", val == str(par + 1), f"val={val} par={par}")
    # 입력창과 패널이 같은 값을 보여준다
    input_val = pg.get_attribute(f"input[data-p='{P}'][data-h='0']", "value")
    check(f"[{label}] 입력창과 패널 값 일치", input_val == val, f"input={input_val} panel={val} sd={pg.evaluate("S.matches[S.mid].sd['가나다']")} cnt={pg.locator('input[data-p="가나다"]').count()} html={pg.inner_html('#score-tbl tbody tr:first-child td:nth-child(2)')[:160]}")
    # 자동 저장 상태
    pg.wait_for_function("document.getElementById('save-status').textContent.includes('자동 저장됨')", timeout=5000)
    check(f"[{label}] 자동 저장 상태 표시", "자동 저장됨" in pg.inner_text("#save-status"))
    check(f"[{label}] 점수 이력 기록", pg.evaluate("(S.matches[S.mid].scoreLog||[]).length") >= 3)
    # 홀 이동
    pg.click("#score-focus button:has-text('다음')"); time.sleep(0.3)
    check(f"[{label}] 다음 홀 이동 (2홀)", pg.inner_text(".sf-hole b").strip() == "2")
    check(f"[{label}] 입력 전 상태 표시", "아직 입력 전" in pg.inner_text("#score-focus"))
    pg.click("#score-focus button:has-text('이전')"); time.sleep(0.2)
    check(f"[{label}] 이전 홀 복귀 (1홀 값 유지)", pg.inner_text(f"{row} >> .sf-num").split("타")[0].strip() == str(par + 1))
    # 경기 중단 → 입력 차단 → 재개
    pg.click("#score-controls button:has-text('경기 중단')"); time.sleep(0.3)
    check(f"[{label}] 중단 중에는 +/- 버튼 비활성", pg.locator("#score-focus .sf-btn:not([disabled])").count() == 0)
    check(f"[{label}] 중단 안내 표시", "중단" in pg.inner_text("#save-status"))
    pg.click("#score-controls button:has-text('경기 재개')"); time.sleep(0.2)
    # 입력창 직접 수정 (잘못 입력 정정)
    pg.fill(f"input[data-p='{P}'][data-h='0']", str(par)); time.sleep(1.0)
    check(f"[{label}] 직접 입력 정정 후 자동 저장", pg.evaluate(f"S.matches[S.mid].sd[{P!r}][0]") == par)
    # 1홀 두 명 채워 결과 확정 가능 상태로 만들기 (9홀 전부)
    for p in [x["name"] for x in []] or pg.evaluate("S.matches[S.mid].groups[S.cg].players"):
        for h in range(9):
            pg.fill(f"input[data-p='{p}'][data-h='{h}']", str(par))
    pg.click("#pg-score .btn-wrap button:has-text('저장')"); time.sleep(0.5)
    pg.click("#pg-score .btn-wrap button:has-text('포인트 결과')"); time.sleep(0.6)
    pg.click("#final-area button:has-text('결과 확정')"); time.sleep(0.4)
    check(f"[{label}] 결과 확정 (순위 표시)", "1위" in pg.inner_text("#final-area"))
    # 확정 후 점수 패널은 입력 불가
    pg.evaluate("openScore(S.mid)"); time.sleep(0.4)
    check(f"[{label}] 확정 후 +/- 버튼 비활성", pg.locator("#score-focus .sf-btn:not([disabled])").count() == 0)
    check(f"[{label}] 확정 후 안내 표시", "확정" in pg.inner_text("#save-status"))
    # 가로 넘침
    check(f"[{label}] 가로 넘침 없음", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
    pg.screenshot(path=str(OUT / "design" / f"score_{label}.png"), full_page=True)

def main():
    (OUT / "design").mkdir(parents=True, exist_ok=True)
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); errors = []; blocked = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for label, vw, vh in (("PC", 1280, 800), ("모바일", 390, 844)):
                ctx = b.new_context(viewport={"width": vw, "height": vh}, locale="ko-KR")
                def route(r):
                    u = r.request.url
                    if u.startswith(f"http://127.0.0.1:{PORT}"): return r.continue_()
                    blocked.append(u.split("?")[0]); return r.abort()
                ctx.route("**/*", route)
                pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(BASE); time.sleep(0.4); pg.evaluate("localStorage.clear()")
                run(pg, label, vw)
                ctx.close()
            b.close()
    finally:
        srv.terminate()
    other = [u for u in blocked if "fonts.googleapis.com" not in u and "kakao" not in u]
    check("외부 요청 없음", not other, str(other[:3]))
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} SCORE PASS {ok}/{len(results)}"
    (OUT / "score_screen_latest.txt").write_text(summary + "\n" + "\n".join(f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary); return 0 if ok == len(results) else 1
if __name__ == "__main__":
    sys.exit(main())
