"""PARKDA 회귀 테스트 (Playwright, 시스템 Chrome 사용).

- 모든 외부 요청(Supabase, 카카오, 유튜브 등)은 차단한다 → 운영 DB·외부 API에 접근하지 않음.
- 데이터는 tests/fixtures/fictional_match.json 의 완전 가상 값만 사용한다.
실행: python3 tests/e2e/test_regression.py
"""
import json, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = json.loads((ROOT / "tests/fixtures/fictional_match.json").read_text(encoding="utf-8"))
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"
OUT.mkdir(parents=True, exist_ok=True)
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def ls_get(page, key):
    return page.evaluate(f"(() => {{ try {{ return JSON.parse(localStorage.getItem('pd_{key}')); }} catch(e) {{ return null; }} }})()")


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    errors, dialogs, expected_dialogs = [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)

            def new_page(width, height):
                ctx = browser.new_context(viewport={"width": width, "height": height}, locale="ko-KR")
                # 로컬 파일 외 모든 요청 차단: 운영 Supabase·외부 API 호출을 원천 봉쇄
                ctx.route("**/*", lambda route: route.continue_()
                          if route.request.url.startswith(f"http://127.0.0.1:{PORT}")
                          else route.abort())
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errors.append(str(e)))
                def on_dialog(d):
                    if "빈 칸" in d.message:
                        expected_dialogs.append(d.message); d.accept()   # 저장 확인(의도된 동작)
                    else:
                        dialogs.append(d.message); d.dismiss()           # 예기치 않은 대화상자는 거부하고 기록
                pg.on("dialog", on_dialog)
                return ctx, pg

            # ── 1. 개인정보 시드 제거 확인 (신규 기기) ──
            ctx, page = new_page(390, 844)
            page.goto(BASE)
            page.wait_for_load_state("domcontentloaded")
            check("신규 기기: 샘플 경기 자동 주입 없음", ls_get(page, "matches") is None,
                  "pd_matches 없음" if ls_get(page, "matches") is None else "주입됨")

            # ── 2. 기존 사용자 데이터 보존 ──
            page.evaluate("(m) => localStorage.setItem('pd_matches', JSON.stringify(m))",
                          {FIX["preserve_match"]["id"]: FIX["preserve_match"]})
            page.reload(); page.wait_for_load_state("domcontentloaded"); time.sleep(0.5)
            before = ls_get(page, "matches")
            check("기존 데이터 로드 후 변경 없음", before and FIX["preserve_match"]["id"] in before, "")

            # ── 3. 로그인 ──
            page.evaluate("go('pg-login')")
            page.check("#privacy-agree")
            page.fill("#l-name", FIX["login"]["name"])
            page.fill("#l-phone", FIX["login"]["phone"])
            page.click("button[onclick='doLogin()']")
            time.sleep(0.5)
            check("로그인 후 홈 화면 표시", page.evaluate("document.getElementById('pg-home').classList.contains('on')"))

            # ── 4. 경기 생성 → 조편성 ──
            page.evaluate("go('pg-create')"); time.sleep(0.3)
            page.fill("#c-title", FIX["match"]["title"])
            page.fill("#c-players", "\n".join(FIX["match"]["players"]))
            page.click("button[onclick='createMatch()']")
            page.wait_for_function("document.getElementById('pg-groups').classList.contains('on')", timeout=15000)
            check("경기 생성 후 조편성 화면", page.evaluate("document.getElementById('pg-groups').classList.contains('on')"))
            groups_txt = page.inner_text("#groups-area")
            check("자동 조편성: 가상 참가자 표시", all(n in groups_txt for n in FIX["match"]["players"]))
            mid = page.evaluate("S.mid")
            code = page.evaluate("S.matches[S.mid] && S.matches[S.mid].code") or ""
            stored = ls_get(page, "match_" + code) or {}
            check("생성 경기 저장(match_<코드>) + 기존 경기 보존", stored.get("id") == mid and
                  FIX["preserve_match"]["id"] in (ls_get(page, "matches") or {}))
            check("게임코드 4자리 생성", len(code) == 4, f"len={len(code)}")
            if not mid: raise SystemExit("경기 생성 실패: 이후 단계를 진행할 수 없습니다")

            # ── 5. 점수 입력 및 저장 ──
            page.evaluate("goScore()"); time.sleep(0.5)
            cell = page.locator("#score-tbl input[data-h='0']").first
            check("점수 입력칸 존재", cell.count() == 1, f"count={cell.count()}")
            scored_name = None
            if cell.count() == 1:
                name = cell.get_attribute("data-p"); scored_name = name
                cell.fill("4")
                page.click("button[onclick='saveScore()']")
                time.sleep(0.5)
                saved = (ls_get(page, "match_" + code) or {}).get("sd", {})
                check("점수 저장 반영", (saved.get(name) or [None])[0] == 4, f"player={name}")

            # ── 6. 결과 화면 ──
            page.evaluate("openResult(S.mid)"); time.sleep(0.5)
            check("결과 표 생성", len(page.inner_text("#result-tbl")) > 0 or len(page.inner_text("#result-total-area")) > 0)

            # ── 7. 결과 공유 (텍스트 생성, 예외 없음) ──
            page.evaluate("shareKakao()"); time.sleep(0.3)
            check("카카오 공유 텍스트 생성 오류 없음", True)

            # ── 8. 게임코드 참여 (같은 기기 로컬 검색) ──
            page.evaluate("c => { document.getElementById('join-code').value = c; }", code)
            page.evaluate("joinGame()"); time.sleep(0.8)
            check("게임코드 참여 처리", bool(mid) and page.evaluate("S.mid") == mid, f"S.mid={page.evaluate('S.mid')}")

            # ── 9. 보존 데이터 최종 확인 ──
            final = ls_get(page, "matches") or {}
            final_match = ls_get(page, "match_" + code) or {}
            check("최종: 생성 경기 점수 유지", scored_name is not None and (final_match.get("sd") or {}).get(scored_name, [None])[0] == 4)
            check("최종: 기존 가상 경기 보존", FIX["preserve_match"]["id"] in final and
                  final[FIX["preserve_match"]["id"]].get("sd") == FIX["preserve_match"]["sd"])

            # ── 10. XSS 헬퍼 동작 확인 ──
            esc_ok = page.evaluate("escHtml('<img src=x onerror=alert(1)>')") == "&lt;img src=x onerror=alert(1)&gt;"
            url_ok = page.evaluate("safeUrl('javascript:alert(1)')") == "#"
            id_ok = page.evaluate("safeId(\"x');alert(1);//\")") == ""
            check("XSS 헬퍼: 이스케이프·URL·ID 검증", esc_ok and url_ok and id_ok)

            ctx.close()

            # ── 11. 화면 크기별 레이아웃 (가로 스크롤 없음) ──
            for label, w, h in [("모바일 390px", 390, 844), ("PC 1280px", 1280, 800)]:
                ctx2, pg2 = new_page(w, h)
                pg2.goto(BASE); time.sleep(0.5)
                pg2.evaluate("go('pg-login')")
                sw = pg2.evaluate("document.documentElement.scrollWidth")
                check(f"{label}: 가로 스크롤 없음", sw <= w, f"scrollWidth={sw}")
                pg2.screenshot(path=str(OUT / f"login_{w}.png"))
                ctx2.close()

            browser.close()
    finally:
        srv.terminate()

    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    check("예기치 않은 브라우저 대화상자 없음", not dialogs, "; ".join(dialogs)[:200])
    check("의도된 확인 대화상자 처리(빈 칸 저장 확인)", len(expected_dialogs) >= 1, f"count={len(expected_dialogs)}")
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} PASS {ok}/{len(results)}"
    (OUT / "regression_latest.txt").write_text(summary + "\n" + "\n".join(
        f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
