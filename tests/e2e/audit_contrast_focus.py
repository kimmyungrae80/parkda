"""대비·키보드 점검 (Playwright). 글자 있는 요소의 전경·배경 대비(WCAG 2.2 AA: 일반 4.5:1, 큰 글씨 3:1)와
키보드 Tab 이동 시 포커스 표시 여부를 확인한다. 실행: python3 tests/e2e/audit_contrast_focus.py"""
import json, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]
PORT = 8779; BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results/design"; OUT.mkdir(parents=True, exist_ok=True)
PAGES = ["pg-home", "pg-venues", "pg-together", "pg-clubs", "pg-club", "pg-my", "pg-tournaments", "pg-mgmt", "pg-login"]
CONTRAST_JS = """() => {
  const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = ({ r, g, b }) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0.99) return c; } return { r: 255, g: 255, b: 255, a: 1 }; };
  const root = document.querySelector('.pg.on') || document.body;
  const out = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const t = walker.currentNode; if (!t.textContent.trim()) continue;
    const el = t.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || el.closest('[hidden]')) continue;
    if (el.closest('.tabbar') && false) continue;
    const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0) continue;
    const fg = parse(cs.color); const bg = bgOf(el); if (!fg) continue;
    const L1 = lum(fg), L2 = lum(bg); const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight, 10);
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const need = large ? 3 : 4.5;
    if (ratio < need) out.push({ text: t.textContent.trim().slice(0, 24), ratio: Math.round(ratio * 100) / 100, need, size, color: cs.color, bg: `rgb(${bg.r},${bg.g},${bg.b})` });
  }
  return out;
}"""
FOCUS_JS = """() => { const a = document.activeElement; if (!a || a === document.body) return null; const cs = getComputedStyle(a); return { tag: a.tagName, id: a.id, outline: cs.outlineStyle + ' ' + cs.outlineWidth }; }"""
def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); contrast = {}; focus = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            ctx = b.new_context(viewport={"width": 390, "height": 844}, locale="ko-KR")
            ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(f"http://127.0.0.1:{PORT}") else r.abort())
            pg = ctx.new_page(); pg.goto(BASE); time.sleep(0.6)
            pg.evaluate("localStorage.clear()"); pg.reload(); time.sleep(0.8)
            for name in PAGES:
                pg.evaluate(f"go('{name}')"); time.sleep(0.4)
                contrast[name] = pg.evaluate(CONTRAST_JS)
            pg.evaluate("go('pg-home')"); time.sleep(0.4); pg.evaluate("document.activeElement && document.activeElement.blur()")
            for _ in range(14):
                pg.keyboard.press("Tab"); time.sleep(0.05)
                focus.append(pg.evaluate(FOCUS_JS))
            ctx.close(); b.close()
    finally:
        srv.terminate()
    (OUT / "contrast_focus_latest.json").write_text(json.dumps({"contrast": contrast, "focus": focus}, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in contrast.values())
    print("대비 미달 글자 요소 합계:", total)
    for name, items in contrast.items():
        for it in items[:4]: print(name, it)
    nofocus = [f for f in focus if f and f["outline"].startswith("none")]
    print("Tab 14회 중 포커스 표시 없음:", len(nofocus), "/", sum(1 for f in focus if f))
main()
