# 공식 도메인 전환 전 백업 (2026-10-31, 읽기 전용 조회 결과)

## 현재 연결 (전환 전)
- Vercel 팀: kimmyungrae80's projects (`team_ywPiHGtkFNuVF3liO6Ig4mfM`)
- parkda.co.kr → project `parkda` (`prj_to28fSUJgEOWpRWbrXB5X20PDGoq`), **redirect → www.parkda.co.kr**
- www.parkda.co.kr → project `parkda` (`prj_to28fSUJgEOWpRWbrXB5X20PDGoq`), verified
- parkda.vercel.app → project `parkda`
- 전환 대상: project `parkda-2-preview` (`prj_Lxco0NKmdQO55zsHuAMfc62fjEhY`), 현재 `parkda-2-preview.vercel.app` 만 연결

## DNS (전환 전, 공개 DNS 조회)
- 네임서버: ns1.gabia.co.kr, ns.gabia.co.kr, ns.gabia.net (도메인 등록기관 Gabia)
- parkda.co.kr A → 76.76.21.21 (Vercel)
- www.parkda.co.kr → cname.vercel-dns.com / 81be3b0616e3d930.vercel-dns-017.com (Vercel)
- 전환에 DNS 변경은 필요 없음 (Vercel 측 도메인 소속만 바꾼다).

## 전환 전 배포 상태
- `parkda` 프로젝트 최근 배포는 feature/parkda-2 브랜치 빌드이며 target 이 production 이 아님.
- 공식 도메인 실제 응답: 2026-10-31 조회 시 "⛳ PARKDA / 파크골프 통합" (2.0 표시 없음) — 기존 운영 화면.
- `parkda-2-preview` 프로젝트 production 배포: dpl_6SkbB2zL4cXahfkTTG3JimJs7ksc (ready).

## 롤백 방법
1. Vercel 에서 parkda.co.kr, www.parkda.co.kr 을 `parkda-2-preview` 에서 제거.
2. `parkda` 프로젝트에 parkda.co.kr (redirect → www.parkda.co.kr), www.parkda.co.kr 을 다시 추가.
3. 기존 프로젝트 `parkda` 는 삭제하지 않았으므로 그대로 재배포 가능.
4. DNS 는 바꾸지 않았으므로 복구 불필요.
