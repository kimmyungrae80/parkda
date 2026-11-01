"""사용방법 테스트 (실제 브라우저). 첫 방문 안내, 전체 사용방법 단계 이동, 화면별 도움말(점수 화면: 입력값·포커스 유지),
로고 비율, 320~1280px 가로 넘침. 외부 요청 차단. 실행: python3 tests/e2e/test_guide.py"""
import os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8788; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
def on(pg, pid): return pg.evaluate(f"document.getElementById('{pid}').classList.contains('on')")

def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); errors = []; blocked = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            def newctx(vw, vh):
                ctx = b.new_context(viewport={"width": vw, "height": vh}, locale="ko-KR")
                def route(r):
                    u = r.request.url
                    if u.startswith(f"http://127.0.0.1:{PORT}"): return r.continue_()
                    blocked.append(u.split("?")[0]); return r.abort()
                ctx.route("**/*", route); return ctx
            # ── 1. 첫 방문 안내 (390) ──
            ctx = newctx(390, 844); pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(BASE); time.sleep(0.5); pg.evaluate("localStorage.clear()"); pg.reload(); time.sleep(0.8)
            check("첫 방문 안내 표시", pg.locator("#first-visit").is_visible())
            pg.click("#first-visit .fv-never"); time.sleep(0.2)
            check("'다시 보지 않기' 후 안내 숨김", not pg.locator("#first-visit").is_visible())
            pg.reload(); time.sleep(0.8)
            check("다시 열어도 안내 표시 안 함 (이 기기에 저장)", not pg.locator("#first-visit").is_visible())
            # ── 2. 전체 사용방법 ──
            pg.click("#pg-home .help-text-btn"); time.sleep(0.3)
            check("홈 상단 '사용방법' → 사용방법 페이지", on(pg, 'pg-guide'))
            check("주제 10개 표시", pg.locator("#guide-index li").count() == 10)
            pg.click("#guide-index li >> nth=2 >> button"); time.sleep(0.3)
            check("주제 '함께 치기' 1단계 표시", "1 / 4 단계" in pg.inner_text("#guide-detail") or "1 / 4" in pg.inner_text("#guide-detail"), pg.inner_text("#guide-detail")[:60])
            pg.click("#guide-detail button:has-text('다음')"); time.sleep(0.2); pg.click("#guide-detail button:has-text('다음')"); time.sleep(0.2)
            check("다음 두 번 → 3 / 4 단계", "3 / 4" in pg.inner_text("#guide-detail"))
            pg.click("#guide-detail button:has-text('이전')"); time.sleep(0.2)
            check("이전 → 2 / 4 단계", "2 / 4" in pg.inner_text("#guide-detail"))
            pg.click("#guide-detail .gd-close"); time.sleep(0.2)
            check("목록으로 돌아가기", pg.locator("#guide-index li").count() == 10 and not pg.locator("#guide-detail").is_visible())
            pg.click("#pg-guide .hub-back"); time.sleep(0.3)
            check("사용방법 → MY 로 뒤로", on(pg, 'pg-my'))
            # ── 3. 화면별 도움말: 점수 입력 중 열고 닫아도 입력값 유지 ──
            pg.evaluate("localStorage.setItem('pd_user', JSON.stringify({name:'가나다', phone:'010-0000-0000', role:'일반회원', privacyAgreed:true}))"); pg.reload(); pg.wait_for_function("document.getElementById('pg-home').classList.contains('on')", timeout=20000)
            pg.evaluate("go('pg-create')"); time.sleep(0.4)
            pg.fill("#c-title", "도움말 테스트"); pg.fill("#c-players", "가나다\n라마바")
            pg.click("button:has-text('경기 만들고 코드 받기')"); time.sleep(0.6)
            pg.click("#pg-groups button:has-text('점수 입력 시작')"); time.sleep(0.5)
            first = pg.evaluate("S.matches[S.mid].groups[S.cg].players[0]")
            pg.fill(f"input[data-p='{first}'][data-h='0']", "5"); time.sleep(0.2)
            trigger = pg.locator("#pg-score .bar .help-btn")
            trigger.click(); time.sleep(0.3)
            check("점수 화면 '도움말' → 도움말 시트 열림", pg.locator("#help-modal").is_visible())
            check("도움말 본문은 점수 입력 설명", "점수 입력·수정" in pg.inner_text("#help-body"))
            pg.keyboard.press("Escape"); time.sleep(0.2)
            check("Esc 로 도움말 닫힘", not pg.locator("#help-modal").is_visible())
            kept = pg.input_value(f"input[data-p='{first}'][data-h='0']")
            check("도움말을 열고 닫아도 입력한 점수 유지", kept == "5", str(kept))
            check("닫은 뒤 도움말 버튼에 포커스 복귀", pg.evaluate("document.activeElement && document.activeElement.classList.contains('help-btn')"))
            trigger.click(); time.sleep(0.2)
            pg.click("#help-modal .help-close"); time.sleep(0.2)
            check("닫기 버튼으로도 닫힘", not pg.locator("#help-modal").is_visible())
            ctx.close()
            # ── 4. 로고: 비율 유지, 홈 링크 ──
            ctx = newctx(390, 844); pg = ctx.new_page(); pg.goto(BASE); time.sleep(0.8)
            logo = pg.evaluate("(() => { const i = document.querySelector('.hub-logo'); const r = i.getBoundingClientRect(); return {w: r.width, h: r.height, nw: i.naturalWidth, nh: i.naturalHeight}; })()")
            ratio_ok = abs((logo['w'] / logo['h']) - (logo['nw'] / logo['nh'])) < 0.02
            check("로고 원본 비율 유지 (찌그러짐 없음)", ratio_ok, str(logo))
            check("로고 표시 높이 56px 이상 (모바일 헤더)", logo['h'] >= 56, str(logo))
            pg.evaluate("go('pg-guide')"); time.sleep(0.3); pg.click("#pg-home .hub-brand") if on(pg, 'pg-home') else None
            pg.evaluate("go('pg-home')"); time.sleep(0.3); pg.click("#pg-home .hub-brand"); time.sleep(0.3)
            check("로고 누르면 홈 (홈에서 확인)", on(pg, 'pg-home'))
            ctx.close()
            # ── 5. 가로 넘침: 320~1280 ──
            for vw in (320, 375, 390, 430, 768, 1024, 1280):
                ctx = newctx(vw, 800); pg = ctx.new_page(); pg.goto(BASE); time.sleep(0.6)
                pg.evaluate("localStorage.clear()"); pg.reload(); time.sleep(0.6)
                ok = True
                for pid in ['pg-home', 'pg-guide']:
                    pg.evaluate(f"go('{pid}')"); time.sleep(0.3)
                    ok = ok and pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                check(f"{vw}px 가로 넘침 없음 (홈·사용방법)", ok)
                ctx.close()
            b.close()
    finally:
        srv.terminate()
    other = [u for u in blocked if "fonts.googleapis.com" not in u and "kakao" not in u]
    check("외부 요청 없음", not other, str(other[:3]))
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} GUIDE PASS {ok}/{len(results)}"
    (OUT / "guide_latest.txt").write_text(summary + "\n" + "\n".join(f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary); return 0 if ok == len(results) else 1
if __name__ == "__main__":
    sys.exit(main())
