#!/usr/bin/env python3
"""수집한 공공데이터셋 전체를 세 가지로 분류한다.

- success   : 다운로드 성공 + 파크골프 구장 행이 1개 이상
- unrelated : 다운로드 성공(또는 제외 대상)이나 파크골프 구장 행이 없음 (사진DB·골프장 내장객·동호회 등 포함)
- failed    : 파일을 받지 못함 (파일 링크 없음, 인증·로그인 필요, 기타 오류). 인증은 우회하지 않음.

결과: data/processed/dataset_classification.json, docs/DATASET_CLASSIFICATION.md
"""
import csv, collections, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "public"
OUT = ROOT / "data" / "processed" / "dataset_classification.json"
DOC = ROOT / "docs" / "DATASET_CLASSIFICATION.md"
REASON = {
    "no_file": "다운로드 파일 링크 없음", "captcha_or_login_required": "인증·로그인 필요 (우회하지 않음)",
    "excluded_topic": "구장 정보가 아닌 주제 (사진DB·내장객·동호회·강좌 등)", "error": "수집 오류",
}


def read_text(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def park_rows(path):
    try:
        rows = list(csv.reader(io.StringIO(read_text(path), newline="")))
    except csv.Error:  # 깨진 행이 있어도 가능한 만큼 센다
        return 0
    if not rows:
        return 0
    return sum(1 for r in rows[1:] if any("파크골프" in c for c in r))


def main():
    # 실제로 구장 레코드가 만들어진 데이터셋만 성공으로 본다 (정규화 결과 기준)
    venue_rows = collections.Counter()
    norm = ROOT / "data" / "processed" / "courses_normalized.jsonl"
    if norm.exists():
        for line in norm.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("source_type") == "public":
                venue_rows[r["source_key"].split(":")[1]] += 1
    out = []
    for meta_path in sorted(RAW.glob("*.meta.json")):
        m = json.loads(meta_path.read_text(encoding="utf-8"))
        rec = {"id": m["id"], "title": (m.get("source_name") or m.get("title") or "").replace("공공데이터포털 - ", ""),
               "publisher": m.get("publisher"), "source_url": m.get("source_url"), "collected_at": m.get("collected_at")}
        st = m.get("status")
        if st == "ok":
            n = venue_rows.get(m["id"], 0)
            if n > 0:
                rec.update(outcome="success", reason=f"구장 레코드 {n}개 생성")
            else:
                rec.update(outcome="unrelated", reason="구장 레코드 없음 (동호회·교실·사업자 현황 등 구장 목록이 아님)")
        elif st == "excluded_topic":
            rec.update(outcome="unrelated", reason=REASON[st])
        else:
            rec.update(outcome="failed", reason=REASON.get(st, st))
        out.append(rec)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    cnt = collections.Counter(r["outcome"] for r in out)
    lines = ["# 공공데이터 수집 분류 (DATASET_CLASSIFICATION)", "",
             f"수집 후보 {len(out)}개 중 성공 {cnt['success']} · 관련 없음 {cnt['unrelated']} · 실패 {cnt['failed']}", "",
             "| 결과 | 데이터셋 | 제공기관 | 사유 | 출처 |", "|---|---|---|---|---|"]
    for r in sorted(out, key=lambda x: (x["outcome"], x["publisher"] or "")):
        lines.append(f"| {r['outcome']} | {r['title']} | {r.get('publisher') or '-'} | {r['reason']} | [링크]({r.get('source_url') or ''}) |")
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"분류 {len(out)}개: {dict(cnt)} → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
