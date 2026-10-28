"""P3~P6 UI 통합 흐름 테스트 (Playwright, PC·모바일). 데이터는 이 브라우저(localStorage)에만 있다.
흐름: 동호회 생성 → 가입 신청 → 승인 → 역할·정기모임·출석 → 모임 생성 → 참가 → 조편성 → 점수 입력 → 결과 확정 → Club Pro 통계
추가: 탈퇴, 대기 승격(P4), 신고 중복 방지, 차단, 경기 중단·재개, 확정 후 승인, 관리자 콘솔 접근 제한, 가로 넘침 없음.
외부 요청은 차단한다 (폰트·카카오 SDK 제외). 운영 Supabase 호출 없음.
실행: python3 tests/e2e/test_p5_integration.py   (PARKDA_SERVE_DIR 로 미리보기 검사 가능)
"""
import os, pathlib, subprocess, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVE = pathlib.Path(os.environ.get("PARKDA_SERVE_DIR", ROOT))
PORT = 8776
BASE = f"http://127.0.0.1:{PORT}/index.html"
OUT = ROOT / "tests/results"; OUT.mkdir(parents=True, exist_ok=True)
PHONE = "010-0000-0000"  # 가상 번호 (테스트 전용)
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

A, B, C = "가나다", "라마바", "마바사"
CLUB = "통합테스트회"
MEET = "통합 아침 모임"

def login(pg, name, url=None, to=None):
    pg.evaluate("""([n, p]) => localStorage.setItem('pd_user', JSON.stringify({name: n, phone: p, role: '일반회원', privacyAgreed: true}))""", [name, PHONE])
    pg.goto(url or BASE); pg.wait_for_function("document.getElementById('pg-home') && document.getElementById('pg-home').classList.contains('on')", timeout=20000)
    if to: pg.evaluate(f"go('{to}')"); time.sleep(0.3)

def go(pg, page):
    pg.evaluate(f"go('{page}')"); time.sleep(0.3)

def no_overflow(pg):
    return pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

def run(pg, label, vw):
    # ── 1. 동호회 생성 ──
    login(pg, A); go(pg, 'pg-clubs')
    pg.fill("#club-name", CLUB); pg.select_option("#club-region", "부산"); pg.fill("#club-intro", "통합 테스트 동호회")
    pg.click("form:has(#club-name) button[type=submit]"); time.sleep(0.5)
    check(f"[{label}] 동호회 생성", CLUB in pg.inner_text("#club-list"))
    check(f"[{label}] 가로 넘침 없음 (동호회)", no_overflow(pg))

    # ── 2. 가입 신청 → 3. 승인 ──
    login(pg, B); go(pg, 'pg-clubs')
    pg.click("#club-list button:has-text('가입 신청')"); time.sleep(0.4)
    check(f"[{label}] 가입 신청 → 승인 대기", "승인 대기" in pg.inner_text("#club-list"))
    check(f"[{label}] 일반 회원: 승인·내보내기 버튼 없음", pg.locator("#club-list button:has-text('승인')").count() == 0 and pg.locator("#club-list button:has-text('내보내기')").count() == 0)

    login(pg, A); go(pg, 'pg-clubs')
    pg.click("#club-list button:has-text('승인')"); time.sleep(0.4)
    check(f"[{label}] 운영자 승인 → 회원 2명", "회원 2명" in pg.inner_text("#club-list"))

    # ── 역할·정기모임·출석 ──
    pg.select_option("#club-list select[data-dm-chg='club-role']", "treasurer"); time.sleep(0.4)
    check(f"[{label}] 운영자 역할 지정 → 총무", "총무" in pg.inner_text("#club-list"))
    pg.fill("#mt-" + pg.evaluate(f"clubsAll().find(c => c.name === '{CLUB}').id"), "정기 모임 1")
    cid = pg.evaluate(f"clubsAll().find(c => c.name === '{CLUB}').id")
    pg.fill("#md-" + cid, "2026-11-01"); pg.fill("#mp-" + cid, "테스트 구장")
    pg.click("#club-list button:has-text('정기모임 등록')"); time.sleep(0.4)
    pg.check("#club-list input[type=checkbox][data-name='라마바']"); time.sleep(0.4)
    check(f"[{label}] 출석 체크 → 출석 1명", "출석 1명" in pg.inner_text("#club-list"))

    # ── 탈퇴 (일반 회원) ──
    login(pg, B); go(pg, 'pg-clubs')
    pg.click("#club-list button:has-text('탈퇴')"); time.sleep(0.4)
    check(f"[{label}] 회원 탈퇴 → 다시 가입 신청 가능", pg.locator("#club-list button:has-text('가입 신청')").count() == 1)
    pg.click("#club-list button:has-text('가입 신청')"); time.sleep(0.3)
    login(pg, A); go(pg, 'pg-clubs')
    pg.click("#club-list button:has-text('승인')"); time.sleep(0.4)
    check(f"[{label}] 재가입 후 다시 승인 → 회원 2명", "회원 2명" in pg.inner_text("#club-list"))

    # ── 4. 모임 생성 → 5. 참가 ──
    login(pg, A); go(pg, 'pg-together')
    pg.click("#tg-tab-create"); time.sleep(0.8)
    pg.fill("#tg-title", MEET); pg.fill("#tg-date", "2026-11-05"); pg.fill("#tg-time", "오전 8시"); pg.fill("#tg-cap", "2")
    pg.click("#tg-view-create button[type=submit]"); time.sleep(0.6)
    check(f"[{label}] 모임 생성", MEET in pg.inner_text("#tg-list"))
    login(pg, B, to='pg-together')
    pg.wait_for_selector("#tg-list .hub-venue", timeout=10000)
    pg.click("#tg-list .hub-venue >> nth=0 >> button:has-text('참가 신청')"); time.sleep(0.5)
    check(f"[{label}] 참가 신청 → 모집 2/2명", "모집 2/2명" in pg.inner_text("#tg-list"))

    # ── 신고 중복 방지, 차단 (C 는 참가하지 않은 회원) ──
    login(pg, C, to='pg-together'); pg.wait_for_selector("#tg-list .hub-venue", timeout=10000)
    pg.click("#tg-list .hub-venue >> nth=0 >> button:has-text('모임 신고')"); time.sleep(0.4)
    pg.click("#tg-list .hub-venue >> nth=0 >> button:has-text('모임 신고')"); time.sleep(0.4)
    check(f"[{label}] 같은 사람 중복 신고 방지 (1건)", "신고 1건" in pg.inner_text("#tg-list"))
    pg.click("#tg-list .hub-venue >> nth=0 >> button:has-text('모임장 차단')"); time.sleep(0.4)
    check(f"[{label}] 차단한 모임장의 모임은 목록에서 숨김", MEET not in pg.inner_text("#tg-list"))
    login(pg, C, to='pg-together'); pg.wait_for_selector("#tg-list", timeout=10000)
    check(f"[{label}] 차단은 이 사용자 기준으로 유지", MEET not in pg.inner_text("#tg-list"))
    pg.evaluate("setMyBlocks([])")  # 데모 차단 해제 (차단 해제 UI 는 아직 없음: 테스트는 저장소를 직접 비움)
    # ── 참가자 확정 → 조편성 ──
    login(pg, A); go(pg, 'pg-together')
    pg.wait_for_selector("#tg-list .hub-venue", timeout=10000)
    pg.click("#tg-list button:has-text('참가자 확정')"); time.sleep(0.4)
    check(f"[{label}] 참가자 확정 → 참가 확정 표시", "참가 확정" in pg.inner_text("#tg-list"))
    pg.click("#tg-list button:has-text('자동 조편성 시작')")
    pg.wait_for_function("document.getElementById('pg-groups').classList.contains('on')", timeout=20000)
    check(f"[{label}] 자동 조편성 완료", True)

    # ── 6. 점수 입력 (일시 중단 → 재개 → 저장) ──
    go(pg, 'pg-matches'); pg.click("#pg-matches button:has-text('점수')"); time.sleep(0.6)
    pg.click("#score-controls button:has-text('경기 중단')"); time.sleep(0.3)
    check(f"[{label}] 경기 중단 표시", "중단된 경기" in pg.inner_text("#score-controls"))
    pg.click("#score-controls button:has-text('경기 재개')"); time.sleep(0.3)
    for p in (A, B):
        for h in range(9):
            pg.fill(f"input[data-p='{p}'][data-h='{h}']", "4")
    pg.click("#pg-score .btn-wrap button:has-text('저장')"); time.sleep(0.6)
    check(f"[{label}] 점수 저장 후 이력 기록됨", pg.evaluate("(S.matches[S.mid].scoreLog||[]).length") >= 18)

    # ── 7. 결과 확정 → 8. 동점 순위 ──
    pg.click("#pg-score .btn-wrap button:has-text('포인트 결과')"); time.sleep(0.8)
    pg.click("#final-area button:has-text('결과 확정')"); time.sleep(0.5)
    fin = pg.inner_text("#final-area")
    check(f"[{label}] 결과 확정 → 순위 표시 (동점 공동 1위)", "1위" in fin and fin.count("1위") == 2, fin[:120])
    pg.evaluate("openScore(S.mid)"); time.sleep(0.3)
    pg.click("#pg-score .btn-wrap button:has-text('저장')"); time.sleep(0.2)
    check(f"[{label}] 확정 후 점수 저장은 승인 없이 차단", "확정된 결과" in pg.inner_text("#toast"), pg.inner_text("#toast")[:60])

    # ── 9. 확정 후 수정 승인 ──
    pg.evaluate("openResult(S.mid)"); time.sleep(0.4)
    pg.click("#final-area button:has-text('확정 후 수정 승인')"); time.sleep(0.4)
    check(f"[{label}] 확정 후 수정 승인 표시", "수정 승인됨" in pg.inner_text("#final-area"))

    # ── 10. Club Pro 통계 (무료 → Pro 체험) ──
    login(pg, A); go(pg, 'pg-club')
    check(f"[{label}] 무료 화면: 통계 잠김 안내", "Pro 기능입니다" in pg.inner_text("#pro-body"))
    pg.click("#pro-body button:has-text('Pro 체험 켜기')"); time.sleep(0.4)
    body = pg.inner_text("#pro-body")
    check(f"[{label}] Pro 체험: 회원별 경기 통계에 경기 기록 반영", f"{A} · 1경기" in body, body[:200])
    check(f"[{label}] Pro 체험: 구장별 통계 표시", "구장별 통계" in body and "평균" in body)
    check(f"[{label}] Pro 체험: 회비 장부·CSV 메뉴 표시 (총무 역할)", "회비 장부" in body and "CSV" in body)
    check(f"[{label}] 가로 넘침 없음 (Club Pro)", no_overflow(pg))
    go(pg, 'pg-together')
    check(f"[{label}] 가로 넘침 없음 (함께 치기)", no_overflow(pg))

def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd=SERVE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    blocked, errors = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            for label, vw, vh in (("PC", 1280, 800), ("모바일", 390, 844)):
                ctx = browser.new_context(viewport={"width": vw, "height": vh}, locale="ko-KR")
                def route(r):
                    u = r.request.url
                    if u.startswith(f"http://127.0.0.1:{PORT}"): return r.continue_()
                    blocked.append(u.split("?")[0]); return r.abort()
                ctx.route("**/*", route)
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(BASE); time.sleep(0.4)
                pg.evaluate("localStorage.clear()")
                run(pg, label, vw)
                # 관리자 콘솔: 일반 접근 차단 → ?dev=1 에서만 열림
                if label == "PC":
                    go(pg, 'pg-console')
                    check("관리자 콘솔: 일반 접근 차단", not pg.evaluate("document.getElementById('pg-console').classList.contains('on')"))
                    login(pg, A, BASE + "?dev=1")
                    go(pg, 'pg-console')
                    console = pg.inner_text("#console-body")
                    check("관리자 콘솔(개발용): 신고 관리 표시 + 신고 1건", "신고 관리" in console and "신고 1건" in console, console[:160])
                    check("관리자 콘솔: 서비스 오류 현황 표시", "서비스 오류 현황" in console)
                    pg.wait_for_function("!document.getElementById('console-quality').textContent.includes('불러오는')", timeout=10000)
                    check("관리자 콘솔: 데이터 품질 현황 로드", "구장 381곳" in pg.inner_text("#console-quality"), pg.inner_text("#console-quality")[:80])
                ctx.close()
            browser.close()
    finally:
        srv.terminate()
    other = [u for u in blocked if "fonts.googleapis.com" not in u and "kakaocdn" not in u and "kakao" not in u]
    check("외부 요청 없음 (폰트·카카오 SDK 제외)", not other, str(other[:3]))
    check("JavaScript 오류 없음", not errors, "; ".join(errors)[:300])
    ok = sum(1 for _, c, _ in results if c)
    summary = f"{datetime.datetime.now().isoformat(timespec='seconds')} P5 PASS {ok}/{len(results)}"
    (OUT / "p5_integration_latest.txt").write_text(summary + "\n" + "\n".join(
        f"{'PASS' if c else 'FAIL'} {n} {d}" for n, c, d in results) + "\n", encoding="utf-8")
    print(summary)
    return 0 if ok == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
