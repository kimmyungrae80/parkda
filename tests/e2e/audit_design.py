"""디자인 접근성·레이아웃 점검 (Playwright). 페이지×폭(195=390의 200% 확대, 390, 768, 1280)별로
가로 넘침, 44px 미만 터치 목표, 이름 없는 버튼·입력창을 센다. 외부 요청 차단.
실행: python3 tests/e2e/audit_design.py"""
import json, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
PORT = 8778; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results/design"; OUT.mkdir(parents=True, exist_ok=True)
PAGES = ["pg-home", "pg-venues", "pg-together", "pg-clubs", "pg-club", "pg-my", "pg-tournaments", "pg-video", "pg-food", "pg-mgmt", "pg-login"]
WIDTHS = [195, 390, 768, 1280]
JS = """() => {
  const vis = e => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const pg = document.querySelector('.pg.on');
  const root = pg || document.body;
  const sel = 'button, a[href], input:not([type=hidden]), select, textarea, [role=button]';
  const els = [...root.querySelectorAll(sel)].filter(vis);
  const small = els.filter(e => { const r = e.getBoundingClientRect(); const min = (e.type === 'checkbox' || e.type === 'radio') ? 24 : 44; return r.width < min || r.height < min; })
    .map(e => (e.id ? '#' + e.id : e.tagName.toLowerCase()) + ':' + (e.textContent || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 20));
  const noName = els.filter(e => {
    if (e.tagName === 'INPUT' || e.tagName === 'SELECT' || e.tagName === 'TEXTAREA') {
      if (e.getAttribute('aria-label') || e.getAttribute('aria-labelledby')) return false;
      if (e.id && document.querySelector('label[for="' + e.id + '"]')) return false;
      return !e.closest('label');
    }
    return !(e.getAttribute('aria-label') || (e.textContent || '').trim());
  }).map(e => (e.id ? '#' + e.id : e.tagName.toLowerCase()));
  return { overflow: document.documentElement.scrollWidth - window.innerWidth, small: small.length, smallSamples: small.slice(0, 6), noName: noName.length, noNameSamples: noName.slice(0, 6) };
}"""
def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); report = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for vw in WIDTHS:
                ctx = b.new_context(viewport={"width": vw, "height": 844}, locale="ko-KR")
                ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(f"http://127.0.0.1:{PORT}") else r.abort())
                pg = ctx.new_page(); pg.goto(BASE); time.sleep(0.6)
                pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("typeof go === 'function'", timeout=20000); time.sleep(0.3)
                for name in PAGES:
                    pg.evaluate(f"go('{name}')"); time.sleep(0.5)
                    r = pg.evaluate(JS); r.update(width=vw, page=name); report.append(r)
                ctx.close()
            b.close()
    finally:
        srv.terminate()
    (OUT / "audit_latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [r for r in report if r["overflow"] > 0 or r["noName"] > 0]
    print("pages x widths:", len(report), "| 가로 넘침:", sum(1 for r in report if r["overflow"] > 0), "| 이름 없는 컨트롤 페이지:", sum(1 for r in report if r["noName"] > 0))
    print("44px 미만 목표 합계:", sum(r["small"] for r in report))
    for r in report:
        if r["overflow"] > 0 or r["noName"] > 0 or r["small"] > 0:
            print(r["width"], r["page"], "overflow", r["overflow"], "small", r["small"], r["smallSamples"][:3], "noName", r["noNameSamples"][:3])
main()
