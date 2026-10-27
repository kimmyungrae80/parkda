#!/usr/bin/env python3
"""대회 정보 정기 갱신 (반복 실행 가능).

1) 공공데이터포털 파크골프 파일을 다시 받는다 (collect_public_data.py, 이어받기 지원)
2) 대회 열이 있는 공식 자료에서 대회를 뽑는다 (normalize_tournaments.py)
3) data/raw/manual/tournaments_manual.json 의 사람이 확인한 공식 공고를 합친다 (출처 URL 필수)
4) 기간을 기준일로 다시 계산한다: 예정 대회 / 지난 대회. 확인되지 않은 항목은 만들지 않는다.
사용법: python3 scripts/update_tournaments.py [--skip-download]
주기 실행 예: 매일 한 번 cron 또는 launchd 로 실행 (설정은 사용자가 직접).
"""
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data" / "raw" / "manual" / "tournaments_manual.json"
OUT = ROOT / "data" / "verified" / "tournaments.json"
PY = sys.executable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()
    if not args.skip_download:
        subprocess.run([PY, str(ROOT / "scripts/collect_public_data.py"), "--keyword", "파크골프", "--max-pages", "2"], check=False)
    subprocess.run([PY, str(ROOT / "scripts/normalize_tournaments.py")], check=True)
    items = json.loads(OUT.read_text(encoding="utf-8"))
    if MANUAL.exists():
        for m in json.loads(MANUAL.read_text(encoding="utf-8")):
            if not (m.get("source_url") and m.get("title") and m.get("date_start")):
                continue  # 출처·대회명·개최일이 없으면 넣지 않음
            items.append({"id": "manual-" + m.get("id", m["title"]), "source_name": m.get("source_name", "공식 공고"), **m,
                          "verification_status": "official_page_checked"})
    today = dt.date.today().isoformat()
    for t in items:
        end = t.get("date_end") or t.get("date_start")
        t["period"] = "예정 대회" if end and end >= today else "지난 대회"
    items.sort(key=lambda t: (t["period"] != "예정 대회", t.get("date_start") or ""))
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    print(f"대회 {len(items)}건 (예정 {sum(1 for t in items if t['period']=='예정 대회')} · 지난 {sum(1 for t in items if t['period']=='지난 대회')}) 기준일 {today}")


if __name__ == "__main__":
    sys.exit(main())
