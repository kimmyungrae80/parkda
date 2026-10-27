// 카카오 로그인 (Supabase Auth 경유). 카카오는 본인 확인을, Supabase 는 서버가 검증하는 세션을 발급한다.
// - 카카오 프로필(닉네임 등)을 브라우저에서 직접 신뢰하지 않는다. 회원 ID 는 Supabase 세션의 auth.uid() 로만 쓴다.
// - 설정이 없으면(동기화 꺼짐) 로그인을 시작하지 않는다.
// - 기존 이름·전화번호 데이터와 자동으로 연결하지 않는다 (docs/AUTH_MIGRATION.md 의 동의 절차 참고).
(function (global) {
  const cfg = global.PARKDA_CONFIG || {};
  const ready = !!(cfg.supabaseUrl && cfg.supabaseAnonKey);
  // 인증 요청 주소 (테스트 가능하도록 순수 함수로 분리)
  function buildAuthorizeUrl(supabaseUrl, redirectTo) {
    if (!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(supabaseUrl || '')) throw new Error('invalid_supabase_url');
    const u = new URL(supabaseUrl + '/auth/v1/authorize');
    u.searchParams.set('provider', 'kakao');
    u.searchParams.set('redirect_to', redirectTo);
    return u.toString();
  }
  function startKakaoLogin(redirectTo) {
    if (!ready) return { ok: false, reason: 'not_configured' };
    global.location.href = buildAuthorizeUrl(cfg.supabaseUrl, redirectTo);  // 카카오 인증 화면으로 이동
    return { ok: true };
  }
  const api = { ready, buildAuthorizeUrl, startKakaoLogin };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else global.PARKDA_AUTH = api;
})(typeof window !== 'undefined' ? window : globalThis);
