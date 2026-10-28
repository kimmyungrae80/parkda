"""함께 치기 · 동호회 데모 테스트 (Playwright). 모든 데이터는 이 브라우저(localStorage)에만 있다.
- 외부 요청 차단, Supabase 호출 없음. 전화번호는 저장·표시되지 않아야 한다.
실행: python3 tests/e2e/test_p4_together_club.py  (PARKDA_SERVE_DIR 로 미리보기 검사 가능)
"""
import json, os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8775
BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
PHONE = "010-0000-0000"  # 가상 번호 (테스트 전용)
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


def login_as(pg, name):
    pg.evaluate("""([n, p]) => { localStorage.setItem('pd_user', JSON.stringify({name: n, phone: p, role: '일반회원', privacyAgreed: true})); }""", [name, PHONE])
    pg.reload()
    # 재방문자는 데이터 로드(차단된 요청 대기 포함) 후 홈으로 이동한다. 홈이 열릴 때까지 기다린 뒤 전환한다.
    pg.wait_for_function("document.getElementById('pg-home').classList.contains('on')", timeout=20000)
    pg.evaluate("go('pg-together')"); time.sleep(0.3)


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    errors, blocked = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="ko-KR")
            def route(r):
                u = r.request.url
                if u.startswith(f"http://127.0.0.1:{PORT}"): return r.continue_()
                blocked.append(u.split("?")[0]); return r.abort()
            ctx.route("**/*", route)
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(BASE); time.sleep(0.5)
            pg.evaluate("localStorage.clear()"); pg.reload(); time.sleep(0.5)

            # 1. 비회원: 모임 목록 열람 가능, 참가 버튼은 로그인 유도
            pg.evaluate("go('pg-together')"); time.sleep(0.4)
            check("비회원: 함께 치기 목록 열람", pg.evaluate("document.getElementById('pg-together').classList.contains('on')"))
            check("데모 안내 문구 표시", "데모 기능" in pg.inner_text("#pg-together"))

            # 2. 회원 A: 모임 생성 (정원 2)
            login_as(pg, "가나다")
            pg.click("#tg-tab-create"); time.sleep(0.5)
            pg.fill("#tg-title", "가상 아침 모임")
            pg.fill("#tg-date", "2026-11-05"); pg.fill("#tg-time", "오전 8시"); pg.fill("#tg-cap", "2")
            pg.click("#tg-view-create button[type=submit]"); time.sleep(0.6)
            check("모임 생성 후 목록에 표시", "가상 아침 모임" in pg.inner_text("#tg-list"))
            check("모임장 본인 확정 참가 1명", "1/2명" in pg.inner_text("#tg-list") or "모집 1" in pg.inner_text("#tg-list") or "모집 1/2" in pg.inner_text("#tg-list"))

            # 3. 회원 B: 참가 → 정원 2/2 마감
            login_as(pg, "라마바"); time.sleep(0.3)
            pg.click("#tg-list .hub-venue >> nth=0 >> button.hub-act-g"); time.sleep(0.5)
            text = pg.inner_text("#tg-list")
            check("B 참가 신청 → 모집 마감", "모집 2/2명" in text and "모집 마감" in text, text[:120])
            check("정원 찬 모임: B 화면에는 참가 신청 버튼 없음", pg.locator("#tg-list .hub-venue >> nth=0 >> button:has-text('참가 신청')").count() == 0)

            # 3b. 회원 C: 정원이 찼으므로 대기 신청
            login_as(pg, "마바사"); pg.wait_for_selector("#tg-list .hub-venue", timeout=10000)
            check("정원 찬 모임: 대기 신청 버튼 표시", pg.locator("#tg-list .hub-venue >> nth=0 >> button:has-text('대기 신청')").count() == 1)
            pg.click("#tg-list .hub-venue >> nth=0 >> button:has-text('대기 신청')"); time.sleep(0.5)
            check("C 대기 등록 표시", "대기: 마바사" in pg.inner_text("#tg-list"))

            # 3c. B 가 참가 취소 → 대기자 C 자동 승격
            login_as(pg, "라마바"); time.sleep(0.3)
            pg.click("#tg-list .hub-venue >> nth=0 >> button:has-text('참가 취소')"); time.sleep(0.5)
            text = pg.inner_text("#tg-list")
            check("B 취소 → 대기자 C 자동 참가 승격", "모집 2/2명" in text and "마바사" in text and "대기: 마바사" not in text, text[:160])

            # 4. C 가 참가 취소 → 다시 모집 1/2명
            login_as(pg, "마바사"); time.sleep(0.3)
            pg.click("#tg-list .hub-venue >> nth=0 >> button:has-text('참가 취소')"); time.sleep(0.5)
            check("C 참가 취소 → 모집 1/2명", "모집 1/2명" in pg.inner_text("#tg-list"))

            # 5. 다시 신청 후 모임장 A 가 확정 → 조편성 연결
            login_as(pg, "라마바"); time.sleep(0.3)
            pg.click("#tg-list .hub-venue >> nth=0 >> button.hub-act-g"); time.sleep(0.4)
            login_as(pg, "가나다"); time.sleep(0.3)
            pg.evaluate("go('pg-together')"); time.sleep(0.3)
            pg.click("#tg-list button:has-text('참가자 확정')"); time.sleep(0.4)
            check("참가자 확정 → 참가 확정 표시", "참가 확정" in pg.inner_text("#tg-list"))
            pg.click("#tg-list button:has-text('자동 조편성 시작')")
            pg.wait_for_function("document.getElementById('pg-groups').classList.contains('on')", timeout=20000)  # 저장 요청 대기 포함
            check("자동 조편성 화면으로 이동", True)
            meetings = pg.evaluate("JSON.parse(localStorage.getItem('pd_demo_meetings_v2') || '[]')")
            check("게임코드가 모임에 연결됨", bool(meetings and meetings[0].get("gameCode")), str(meetings[0].get("gameCode") if meetings else None))

            # 6. 게임코드로 다른 기기(같은 저장소) 참가 흐름: 기존 joinGame 재사용
            code = meetings[0]["gameCode"]
            pg.evaluate("go('pg-mgmt')"); time.sleep(0.3)
            check("경기관리 화면 존재 (기존 기능)", pg.evaluate("document.getElementById('pg-mgmt').classList.contains('on')"))

            # 7. 동호회: A 생성 → B 신청 → A 승인 → 공지 확인
            pg.evaluate("go('pg-clubs')"); time.sleep(0.4)
            pg.fill("#club-name", "가상 파크골프회"); pg.select_option("#club-region", "부산")
            pg.fill("#club-intro", "가상 동호회 소개")
            pg.click("form:has(#club-name) button[type=submit]"); time.sleep(0.5)
            check("동호회 생성", "가상 파크골프회" in pg.inner_text("#club-list"))
            pg.click("#club-list .hub-venue >> nth=0 >> text=승인", timeout=500) if False else None
            pg.fill("#nt-" + pg.evaluate("JSON.parse(localStorage.getItem('pd_demo_clubs_v2'))[0].id"), "가상 공지")
            pg.fill("#nb-" + pg.evaluate("JSON.parse(localStorage.getItem('pd_demo_clubs_v2'))[0].id"), "정기 모임 안내")
            pg.click("#club-list button:has-text('공지 올리기')"); time.sleep(0.4)
            check("운영자 공지 등록", "가상 공지" in pg.inner_text("#club-list"))
            login_as(pg, "라마바"); pg.evaluate("go('pg-clubs')"); time.sleep(0.4)
            pg.click("#club-list button:has-text('가입 신청')"); time.sleep(0.4)
            check("가입 신청 → 승인 대기 표시", "승인 대기" in pg.inner_text("#club-list"))
            check("일반 회원에게 승인 버튼·운영자 메뉴 없음", pg.locator("#club-list button:has-text('승인')").count() == 0)
            check("일반 회원도 공지는 열람", "가상 공지" in pg.inner_text("#club-list"))
            login_as(pg, "가나다"); pg.evaluate("go('pg-clubs')"); time.sleep(0.4)
            pg.click("#club-list button:has-text('승인')"); time.sleep(0.4)
            check("운영자 승인 → 회원 수 증가", "회원 2명" in pg.inner_text("#club-list"))

            # 8. 전화번호는 어디에도 표시·저장되지 않음
            all_text = pg.inner_text("body") + pg.evaluate("localStorage.getItem('pd_demo_meetings_v2') || ''") + pg.evaluate("localStorage.getItem('pd_demo_clubs_v2') || ''")
            check("전화번호 미표시·미저장", PHONE not in all_text)

            # 9. 외부 API·Supabase 직접 호출 없음
            # 폰트·카카오 로그인 SDK 는 기존 기능이 쓰는 외부 자원 (키 없음). 그 밖의 외부 요청만 실패로 본다.
            other = [u for u in blocked if "fonts.googleapis.com" not in u and "kakaocdn" not in u]
            check("데모 흐름에서 그 밖의 외부 요청 없음", not other, str(other[:3]))
            ctx.close(); browser.close()
    finally:
        srv.terminate()
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} P4 PASS {ok}/{len(results)}"
    (OUT / "p4_together_club_latest.txt").write_text(summary + "\n" + "\n".join(
        f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
