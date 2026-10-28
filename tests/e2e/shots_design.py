"""디자인 스크린샷 생성 (390 / 768 / 1280). 외부 요청 차단. 실행: python3 tests/e2e/shots_design.py"""
import pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
PORT = 8777; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results/design"; OUT.mkdir(parents=True, exist_ok=True)
PAGES = ["pg-home", "pg-venues", "pg-together", "pg-clubs", "pg-club", "pg-my", "pg-tournaments", "pg-mgmt"]
def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                ctx.close()
            b.close()
    finally:
        srv.terminate()
main()
