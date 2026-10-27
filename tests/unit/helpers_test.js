// 사용법: node tests/unit/helpers_test.js index.html
// 외부 데이터 이스케이프 헬퍼(escHtml·safeUrl·safeId)를 기대값과 비교한다. 불일치 시 종료 코드 1.
const fs = require('fs');
const s = fs.readFileSync(process.argv[2], 'utf8');
const block = s.slice(s.indexOf('function escHtml'), s.indexOf('function esc(s) {'));
const { escHtml, safeUrl, safeId } = new Function(block + '; return {escHtml, safeUrl, safeId};')();
const cases = [
  ['escHtml', '<img src=x onerror=alert(1)>', '&lt;img src=x onerror=alert(1)&gt;'],
  ['escHtml', '"><script>x</script>', '&quot;&gt;&lt;script&gt;x&lt;/script&gt;'],
  ['escHtml', "Tom & Jerry's", 'Tom &amp; Jerry&#39;s'],
  ['safeUrl', 'https://example.com/a?b=1', 'https://example.com/a?b=1'],
  ['safeUrl', 'javascript:alert(1)', '#'],
  ['safeUrl', "https://x.com/');alert(1);//", 'https://x.com/%27);alert(1);//'],
  ['safeId', 'dQw4w9WgXcQ', 'dQw4w9WgXcQ'],
  ['safeId', "x');alert(1);//", ''],
];
const fns = { escHtml, safeUrl, safeId };
let fail = 0;
for (const [f, input, expected] of cases) {
  const got = fns[f](input);
  const ok = got === expected;
  if (!ok) fail++;
  console.log((ok ? 'PASS ' : 'FAIL ') + f.padEnd(8) + JSON.stringify(input).padEnd(40) + ' => ' + JSON.stringify(got));
}
console.log(`\nhelper tests: PASS ${cases.length - fail} / FAIL ${fail}`);
process.exit(fail ? 1 : 0);
