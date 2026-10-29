"""디자인 스크린샷 생성 (390 / 768 / 1280). 외부 요청 차단. 실행: python3 tests/e2e/shots_design.py"""
import os, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
PORT = 8777; BASE = f"http://127.0.0.1:{PORT}/index.html"
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))  # 변경 전 비교용으로 다른 폴더를 가리킬 수 있다
OUT = pathlib.Path(os.environ.get("PARKDA_SHOT_OUT", ROOT / "tests/results/design")); OUT.mkdir(parents=True, exist_ok=True)
PAGES = ["pg-home", "pg-venues", "pg-together", "pg-clubs", "pg-club", "pg-my", "pg-tournaments", "pg-mgmt", "pg-login", "pg-video", "pg-food"]
def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for vw in (390, 768, 1280):
                ctx = b.new_context(viewport={"width": vw, "height": 844}, locale="ko-KR")
                ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(f"http://127.0.0.1:{PORT}") else r.abort())
                pg = ctx.new_page(); pg.goto(BASE); time.sleep(0.6)
                pg.evaluate("localStorage.clear()"); pg.reload(); time.sleep(0.8)
                for name in PAGES:
                    pg.evaluate(f"go('{name}')"); time.sleep(0.6)
                    pg.screenshot(path=str(OUT / f"{name}_{vw}.png"), full_page=True)
                    overflow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                    print(vw, name, "overflow_px=", overflow)
                # 관리자 콘솔 (?dev=1 에서만 열림, 데모)
                pg.goto(BASE + "?dev=1"); time.sleep(0.8)
                pg.evaluate("go('pg-console')"); time.sleep(0.8)
                pg.wait_for_function("document.getElementById('console-quality') && !document.getElementById('console-quality').textContent.includes('불러오는')", timeout=10000)
                pg.screenshot(path=str(OUT / f"pg-console_{vw}.png"), full_page=True)
                print(vw, "pg-console overflow_px=", pg.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
                ctx.close()
            b.close()
    finally:
        srv.terminate()
main()
