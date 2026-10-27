#!/usr/bin/env python3
"""기존 parkda.v2 저장소의 Excel 자료(park_data.xlsx, 경기장_정보.xlsx)를 읽어 원본 레코드로 저장한다.

- 두 파일은 같은 구장 목록(383행, kpgaID 동일)이며 내용이 일치함을 확인했다. 둘 다 읽어 비교한다.
- 출처: GitHub 저장소 kimmyungrae80/parkda.v2 (라이선스 파일 없음 → 재이용 조건 미확인으로 표시).
- 결과: data/processed/excel_records.json (원본 값 보존, 정규화는 normalize_courses.py 에서 수행).
"""
import datetime as dt, json, sys
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "github"
OUT = ROOT / "data" / "processed" / "excel_records.json"
REPO_URL = "https://github.com/kimmyungrae80/parkda.v2"

# 두 파일의 열 이름이 다르므로 위치가 아니라 이름으로 매핑한다
COLUMN_ALIASES = {
    "kpga_id": ["kpgaID"], "local_code": ["local"], "name": ["구장명", "name"],
    "address": ["주소", "address"], "holes": ["홀수", "홀"], "gps": ["gps"],
    "phone": ["phone"], "manager": ["manager"], "reg_date": ["reg_date"], "size": ["size"],
}


def read_rows(path):
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    idx = {}
    for key, names in COLUMN_ALIASES.items():
        for n in names:
            if n in header:
                idx[key] = header.index(n)
                break
    out = []
    for r in rows[1:]:
        if not any(c not in (None, "") for c in r):
            continue
        rec = {k: (r[i] if i is not None and i < len(r) else None) for k, i in idx.items()}
        out.append(rec)
    return out, header


def main():
    collected = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sources = {}
    for fname in ["park_data.xlsx", "경기장_정보.xlsx"]:
        path = RAW / fname
        if not path.exists():
            print(f"없음: {path}", file=sys.stderr)
            continue
        rows, header = read_rows(path)
        sources[fname] = {"rows": rows, "header": header}
        print(f"{fname}: {len(rows)}행, 열 {len(header)}개")
    if not sources:
        sys.exit("읽을 Excel 파일이 없습니다")
    records = []
    for fname, data in sources.items():
        for i, rec in enumerate(data["rows"], start=1):
            rec = {k: (None if (v in (None, "", "NULL", "None")) else v) for k, v in rec.items()}
            rec.update({
                "origin_file": fname, "origin_row": i,
                "source_name": f"parkda.v2 저장소 Excel ({fname})",
                "source_url": f"{REPO_URL}/blob/main/{fname}",
                "collected_at": collected,
                "source_license": "라이선스 파일 없음 (재이용 조건 미확인)",
            })
            records.append(rec)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"저장: {OUT.relative_to(ROOT)} ({len(records)}건)")


if __name__ == "__main__":
    main()
