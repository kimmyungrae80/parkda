# PARKDA 2.0 미리보기

- 주소: https://parkda-2-preview.vercel.app/
- 프로젝트: Vercel `kimmyungrae80s-projects/parkda-2-preview` (운영 parkda.co.kr 과 무관)
- 운영 DB: **연결 없음** (Supabase 주소·키 제거, 호출 비활성화)
- 운영 키: 없음 (유튜브·카카오 REST·관리자 비밀번호 제거)
- 카카오 지도: 미리보기 도메인이 카카오 앱에 허용되지 않아 구장·맛집 검색은 안내 메시지만 표시됨 (소유자가 허용 도메인 추가 필요)

## 다시 만들기
```bash
cd ~/Downloads/parkda
node tools/make_preview.js          # preview/ 생성 (운영 값 남아 있으면 실패)
cd preview && vercel --yes          # 미리보기 배포
```
- `preview/` 는 git 에 올리지 않는다 (.gitignore).
- 로컬 확인: `cd preview && python3 -m http.server 8000` → http://127.0.0.1:8000/
- 테스트를 미리보기 빌드에 대해 실행: `PARKDA_SERVE_DIR=$PWD/preview python3 tests/e2e/test_p1_home.py`
