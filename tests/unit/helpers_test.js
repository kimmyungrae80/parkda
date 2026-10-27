// 사용법: node tests/unit/helpers_test.js index.html  (외부 데이터 이스케이프 헬퍼 검증)
const fs = require('fs');
const s = fs.readFileSync(process.argv[2], 'utf8');
const block = s.slice(s.indexOf('function escHtml'), s.indexOf('function esc(s) {'));
const { escHtml, safeUrl, safeId } = new Function(block + '; return {escHtml, safeUrl, safeId};')();
const cases = [
  ['escHtml', '<img src=x onerror=alert(1)>'],
  ['escHtml', '"><script>x</script>'],
  ['escHtml', "Tom & Jerry's"],
  ['safeUrl', 'https://example.com/a?b=1'],
  ['safeUrl', 'javascript:alert(1)'],
  ['safeUrl', "https://x.com/');alert(1);//"],
  ['safeId', 'dQw4w9WgXcQ'],
  ['safeId', "x');alert(1);//"],
];
const fns = { escHtml, safeUrl, safeId };
for (const [f, v] of cases) console.log(f.padEnd(8), JSON.stringify(v).padEnd(46), '=>', JSON.stringify(fns[f](v)));
