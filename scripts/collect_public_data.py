#!/usr/bin/env python3
"""공공데이터포털(data.go.kr)에서 파크골프 관련 파일데이터를 수집한다.

- 검색 결과 → 데이터셋 상세 페이지 → 파일 다운로드 순서로 진행한다.
- 로그인, CAPTCHA, 활용신청이 필요한 API 는 사용하지 않는다 (파일 다운로드만).
- 요청 간격 1초. 같은 데이터셋은 다시 받아도 같은 파일명으로 덮어쓴다 (중복 생성 없음).
- 각 파일 옆에 메타데이터(JSON)를 저장한다: 출처 이름·URL·수집일·제공기관·수정일·이용허락 문구·파일 해시.

사용법: python3 scripts/collect_public_data.py [--keyword 파크골프] [--max-pages 3]
"""
import argparse, datetime as dt, hashlib, json, re, sys, time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "public"
SEARCH = "https://www.data.go.kr/tcs/dss/selectDataSetList.do"
DETAIL = "https://www.data.go.kr/data/{id}/fileData.do"
DOWNLOAD = "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={fid}&fileDetailSn={sn}&insertDataPrcus=N"
HEADERS = {"User-Agent": "PARKDA-public-data-collector/1.0 (polite; 1 req/s)"}
DELAY = 1.0


def get(url, **kw):
    time.sleep(DELAY)
    headers = {**HEADERS, **kw.pop("headers", {})}
    r = requests.get(url, headers=headers, timeout=60, **kw)
    r.raise_for_status()
    return r


def discover(keyword, max_pages):
    """검색 결과에서 파일데이터셋 ID 를 모은다."""
    ids = []
    for page in range(1, max_pages + 1):
        r = get(SEARCH, params={"keyword": keyword, "dType": "FILE", "perPage": 50, "currentPage": page})
        found = re.findall(r"/data/(\d{6,9})/fileData\.do", r.text)
        new = [i for i in dict.fromkeys(found) if i not in ids]
        if not new:
            break
        ids.extend(new)
    return ids


def parse_detail(html):
    """상세 페이지의 <strong class="key">라벨</strong><div class="value">값</div> 구조에서 메타데이터를 뽑는다."""
    def field(label):
        m = re.search(r'<strong class="key">\s*' + re.escape(label) + r'\s*</strong>\s*<div class="value">(.*?)</div>', html, re.S)
        if not m:
            return None
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        return re.sub(r"\s+", " ", text).strip() or None
    title = re.search(r"<title>\s*([^<]+?)\s*</title>", html)
    files = re.findall(r"fileDownload\.do\?atchFileId=([A-Z0-9_]+)&(?:amp;)?fileDetailSn=(\d+)", html)
    return {
        "title": (title.group(1).split("|")[0].strip() if title else None),
        "publisher": field("제공기관"),
        "updated": field("수정일"),
        "license": field("이용허락범위"),
        "fee": field("비용부과유무"),
        "file": files[0] if files else None,
    }


def sha256(b):
    return hashlib.sha256(b).hexdigest()


EXCLUDE_TOPIC = re.compile(r"사진DB|골프장_내장객|동호회|강좌")  # 구장 정보가 아닌 자료는 받지 않는다


def collect_one(dsid):
    html = get(DETAIL.format(id=dsid)).text
    meta = parse_detail(html)
    if meta["title"] and EXCLUDE_TOPIC.search(meta["title"]):
        return {"id": dsid, "status": "excluded_topic", "source_url": DETAIL.format(id=dsid), **meta}
    if not meta["file"]:
        return {"id": dsid, "status": "no_file", "source_url": DETAIL.format(id=dsid), **meta}
    fid, sn = meta["file"]
    body = get(DOWNLOAD.format(fid=fid, sn=sn), headers={"Referer": DETAIL.format(id=dsid)}).content
    if body[:1] == b"<" or len(body) < 50:
        # 파일 대신 HTML(인증·로그인 화면)이 왔다면 우회하지 않고 공식 페이지 링크만 남긴다.
        return {"id": dsid, "status": "captcha_or_login_required", "source_url": DETAIL.format(id=dsid), **meta}
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{dsid}.csv"
    path.write_bytes(body)
    record = {
        "id": dsid,
        "status": "ok",
        "source_name": f"공공데이터포털 - {meta['title'] or dsid}",
        "source_url": DETAIL.format(id=dsid),
        "publisher": meta["publisher"],
        "dataset_updated": meta["updated"],
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source_license": meta["license"] or "확인 필요",
        "fee_notice": meta["fee"],
        "file": str(path.relative_to(ROOT)),
        "sha256": sha256(body),
        "bytes": len(body),
    }
    (RAW / f"{dsid}.meta.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", default="파크골프")
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--force", action="store_true", help="이미 끝난 데이터셋도 다시 받는다")
    args = ap.parse_args()
    ids = discover(args.keyword, args.max_pages)
    print(f"후보 데이터셋 {len(ids)}개")
    RAW.mkdir(parents=True, exist_ok=True)
    progress_path = RAW / "_progress.json"  # 중단돼도 이어서 실행: 끝난 데이터셋은 건너뜀
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
    DONE = {"ok", "no_file", "excluded_topic", "captcha_or_login_required"}
    results = []
    for dsid in ids:
        if not args.force and progress.get(dsid) in DONE and (RAW / f"{dsid}.meta.json").exists():
            results.append(json.loads((RAW / f"{dsid}.meta.json").read_text(encoding="utf-8")))
            continue
        try:
            rec = collect_one(dsid)
        except Exception as e:  # 한 건 실패가 전체를 멈추지 않도록
            rec = {"id": dsid, "status": "error", "error": str(e)[:200]}
        results.append(rec)
        if rec["status"] != "ok":  # 실패·제외도 사유를 남긴다 (분류 보고서용)
            (RAW / f"{dsid}.meta.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        progress[dsid] = rec["status"]
        progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {dsid}: {rec['status']} {rec.get('publisher') or ''} {rec.get('bytes', '')}", flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    summary = RAW / "_collect_summary.json"
    summary.write_text(json.dumps({"keyword": args.keyword, "run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                   "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"완료: 파일 {ok}개 / 후보 {len(ids)}개 → {summary.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
