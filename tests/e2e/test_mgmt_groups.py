"""경기관리 통합 테스트: 허브(진행 중·완료), 조편성 수동 이동·조장 변경·확정, 점수 화면 이동 버튼. 390·768·1280 실제 브라우저.
외부 요청 차단. 실행: python3 tests/e2e/test_mgmt_groups.py"""
import os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8784; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
def on(pg, pid): return pg.evaluate(f"document.getElementById('{pid}').classList.contains('on')")

def flow(pg, label):
    pg.goto(BASE); time.sleep(0.5); pg.evaluate("localStorage.clear()")
    pg.evaluate("localStorage.setItem('pd_user', JSON.stringify({name:'가나다', phone:'010-0000-0000', role:'일반회원', privacyAgreed:true}))")
    pg.reload(); pg.wait_for_function("document.getElementById('pg-home').classList.contains('on')", timeout=20000)
    pg.evaluate("go('pg-create')"); time.sleep(0.4)
    pg.fill("#c-title", f"조편성 테스트 {label}")
    pg.fill("#c-players", "가나다\n라마바\n마바사\n사아자")
    pg.click("button:has-text('경기 만들고 코드 받기')"); time.sleep(0.8)
    check(f"[{label}] 조편성 화면 진입", on(pg, 'pg-groups'))
    check(f"[{label}] 조편성 수정 패널 표시", pg.locator("#group-edit .gedit-row:not(.gedit-leader)").count() == 4)
    # 참가자 한 명을 다른 조로 이동
    before = pg.evaluate("S.matches[S.mid].groups.map(g => g.players.slice())")
    if len(before) >= 2:
        p = before[0][0]
        pg.select_option(f"#mv-{p}", str(1)); time.sleep(0.4)
        after = pg.evaluate("S.matches[S.mid].groups.map(g => g.players.slice())")
        check(f"[{label}] 참가자 조 이동 반영", p in after[1] and p not in after[0], f"{before} -> {after}")
        check(f"[{label}] 이동 후 전체 인원 유지", sorted(sum(after, [])) == sorted(sum(before, [])))
        # 저장 확인 (새로고침 뒤에도 조편성 유지)
        pg.reload(); pg.wait_for_function("document.getElementById('pg-home').classList.contains('on')", timeout=20000)
        kept = pg.evaluate("(() => { const m = S.matches[Object.keys(S.matches)[0]]; return m.groups.map(g => g.players.slice()); })()")
        check(f"[{label}] 새로고침 후 조편성 유지", kept == after, str(kept))
    # 조장 변경 & 확정
    pg.evaluate("openScore(Object.keys(S.matches)[0])"); time.sleep(0.4)
    pg.evaluate("go('pg-groups')"); time.sleep(0.3)
    gid = pg.evaluate("S.matches[Object.keys(S.matches)[0]].groups[0].players")
    if len(gid) >= 2:
        pg.select_option("#ld-0", gid[1]); time.sleep(0.3)
        check(f"[{label}] 조장 변경", pg.evaluate("S.matches[Object.keys(S.matches)[0]].groups[0].leader") == gid[1])
    pg.click("#group-edit button:has-text('조편성 확정')"); time.sleep(0.4)
    check(f"[{label}] 조편성 확정 후 이동 잠금", pg.locator("#group-edit select:not([disabled])").count() == 0)
    pg.click("#group-edit button:has-text('확정 취소')"); time.sleep(0.3)
    check(f"[{label}] 확정 취소 후 다시 수정 가능", pg.locator("#group-edit select:not([disabled])").count() > 0)
    # 점수 화면 이동 버튼
    pg.evaluate("openScore(Object.keys(S.matches)[0])"); time.sleep(0.4)
    check(f"[{label}] 점수 화면: 이전 화면·경기 목록·홈 버튼", pg.locator("#score-controls .score-nav button").count() == 3)
    pg.click("#score-controls .score-nav button:has-text('경기 목록')"); time.sleep(0.4)
    check(f"[{label}] 점수 화면 → 경기 목록(경기관리 허브)", on(pg, 'pg-mgmt'))
    check(f"[{label}] 허브: 진행 중 경기 카드 표시", "조편성 테스트" in pg.inner_text("#mgmt-running"))
    check(f"[{label}] 허브: 게임코드 참가 폼 1개", pg.locator("#pg-mgmt form").count() == 1)
    check(f"[{label}] 허브: 경기 만들기 버튼 1개", pg.locator("#pg-mgmt .hub-act-big").count() == 1)
    pg.click("#pg-mgmt .hub-back"); time.sleep(0.3)
    check(f"[{label}] 허브 → 홈", on(pg, 'pg-home'))
    check(f"[{label}] 가로 넘침 없음", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
    pg.screenshot(path=str(OUT / "design" / f"mgmt_groups_{label}.png"), full_page=True)

def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); errors = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for label, vw, vh in (("모바일", 390, 844), ("태블릿", 768, 1024), ("PC", 1280, 800)):
                ctx = b.new_context(viewport={"width": vw, "height": vh}, locale="ko-KR")
                ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(f"http://127.0.0.1:{PORT}") else r.abort())
                pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
                flow(pg, label); ctx.close()
            b.close()
    finally:
        srv.terminate()
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} MGMT PASS {ok}/{len(results)}"
    (OUT / "mgmt_groups_latest.txt").write_text(summary + "\n" + "\n".join(f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary); return 0 if ok == len(results) else 1
if __name__ == "__main__":
    sys.exit(main())
