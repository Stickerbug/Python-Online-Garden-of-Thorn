// 聊天链接化核心逻辑测试：在 Node 里直接加载 shared-chat-actions.js（带极简 DOM 桩）。
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

// --- 极简 DOM 桩：够 appendChatTextWithLinks / chatLinkHtml 跑通 ---
function makeElement(tag) {
  return {
    tagName: String(tag || 'div').toUpperCase(),
    children: [],
    className: '',
    textContent: '',
    href: '',
    target: '',
    rel: '',
    listeners: {},
    appendChild(child) { this.children.push(child); },
    addEventListener(type, fn) { this.listeners[type] = fn; },
    setAttribute(key, value) { this[`attr_${key}`] = value; },
  };
}
const documentStub = {
  createElement: makeElement,
  createTextNode: (text) => ({ tagName: '#text', textContent: String(text), children: [], href: '', className: '' }),
  querySelectorAll: () => [],
};
const windowStub = { document: documentStub, GtnChatActions: undefined, GtnChatRecall: undefined, GtnChatLinks: undefined };

globalThis.document = documentStub;
globalThis.window = windowStub;

const source = readFileSync(new URL('../static/js/shared-chat-actions.js', import.meta.url), 'utf-8');
// 共享模块是 IIFE 经典脚本：用函数包裹后以 window 桩执行。
const run = new Function('window', 'document', `${source}\n;return window;`);
const win = run(windowStub, documentStub);
const links = win.GtnChatLinks;
if (!links) throw new Error('GtnChatLinks not exported');

// appendTextWithLinks 的结果收集
function collect(text, options = {}) {
  const parent = makeElement('div');
  links.appendTextWithLinks(parent, text, options);
  return parent.children.map((child) => ({
    tag: child.tagName,
    text: child.textContent,
    href: child.href || '',
    cls: child.className || '',
  }));
}

let failures = 0;
function normalize(items) {
  if (!Array.isArray(items)) throw new Error('collect() must return an array');
  return items.map((item) => {
    const tag = item.tag === '#text' ? '#text' : (item.tag || '').toUpperCase();
    if (tag === '#TEXT' || tag === '#text') return { tag: '#text', text: item.text };
    return { tag, text: item.text, href: item.href || '', cls: item.cls || '' };
  });
}

function check(name, actual, expected) {
  const a = JSON.stringify(normalize(actual));
  const e = JSON.stringify(expected);
  if (a === e) {
    console.log(`ok - ${name}`);
  } else {
    failures += 1;
    console.log(`FAIL - ${name}\n  actual:   ${a}\n  expected: ${e}`);
  }
}

// 1. 基本识别
check('plain text untouched', collect('你好呀'), [{ tag: '#text', text: '你好呀' }]);
check('http url linked', collect('看这个 https://example.com/a?b=1 谢谢'), [
  { tag: '#text', text: '看这个 ' },
  { tag: 'A', text: 'https://example.com/a?b=1', href: 'https://example.com/a?b=1', cls: 'chat-link' },
  { tag: '#text', text: ' 谢谢' },
]);

// 2. 句尾中文标点不属于链接（正则直接排除了全角区）
check('chinese punct excluded', collect('https://example.com/a。好的'), [
  { tag: 'A', text: 'https://example.com/a', href: 'https://example.com/a', cls: 'chat-link' },
  { tag: '#text', text: '。好的' },
]);

// 3. 英文句尾标点剥离（句号/逗号/右括号无配对时剥离）
check('trailing period stripped', collect('see https://example.com/a.'), [
  { tag: '#text', text: 'see ' },
  { tag: 'A', text: 'https://example.com/a', href: 'https://example.com/a', cls: 'chat-link' },
  { tag: '#text', text: '.' },
]);
check('trailing comma stripped', collect('https://example.com/a, then'), [
  { tag: 'A', text: 'https://example.com/a', href: 'https://example.com/a', cls: 'chat-link' },
  { tag: '#text', text: ', then' },
]);
check('unpaired paren stripped', collect('(see https://example.com/a) end'), [
  { tag: '#text', text: '(see ' },
  { tag: 'A', text: 'https://example.com/a', href: 'https://example.com/a', cls: 'chat-link' },
  { tag: '#text', text: ') end' },
]);
check('paired parens kept', collect('https://en.wikipedia.org/wiki/Tree_(plant) is good'), [
  { tag: 'A', text: 'https://en.wikipedia.org/wiki/Tree_(plant)', href: 'https://en.wikipedia.org/wiki/Tree_(plant)', cls: 'chat-link' },
  { tag: '#text', text: ' is good' },
]);

// 4. 协议白名单：javascript: 不会匹配
check('javascript scheme ignored', collect('click javascript:alert(1) now'), [
  { tag: '#text', text: 'click javascript:alert(1) now' },
]);
check('data scheme ignored', collect('data:text/html,evil'), [
  { tag: '#text', text: 'data:text/html,evil' },
]);

// 5. 站内/站外判定（布尔断言）
function expect(name, actual, expected) {
  const ok = actual === expected;
  if (ok) console.log(`ok - ${name}`);
  else { failures += 1; console.log(`FAIL - ${name}: actual ${JSON.stringify(actual)} expected ${JSON.stringify(expected)}`); }
}
expect('internal domain allowed', links.internalAllowed('https://gtn.stickerbug.top/'), true);
expect('internal subdomain allowed', links.internalAllowed('https://wiki.stickerbug.top/x'), true);
expect('apex allowed', links.internalAllowed('https://stickerbug.top'), true);
expect('external blocked', links.internalAllowed('https://evil.example.com/x'), false);
expect('lookalike rejected', links.internalAllowed('https://stickerbug.top.evil.com/'), false);
expect('http internal allowed', links.internalAllowed('http://gtn.stickerbug.top:8081/a'), true);

// 6. HTML 版
const html = links.html('去 https://example.com/a 看看');
expect('html version creates anchor', /<a href="https:\/\/example\.com\/a" target="_blank" rel="noopener noreferrer" class="chat-link" data-chat-external="1">https:\/\/example\.com\/a<\/a>/.test(html), true);
const htmlInternal = links.html('去 https://gtn.stickerbug.top/ 看看');
expect('html internal no external flag', /class="chat-link">https:\/\/gtn\.stickerbug\.top\/<\/a>/.test(htmlInternal) && !htmlInternal.includes('data-chat-external'), true);

// 7. 转义后的文本里 <script> 不会复活（HTML 版输入是已转义文本）
expect('escaped angle brackets stay inert', links.html('https://a.example.com/&lt;script&gt;').includes('<script>'), false);

// 8. 多链接
expect('multiple links', collect('a https://x.example.com b https://y.example.com c').filter(x => x.tag === 'A').length, 2);

// 9. 裸域名（无协议）识别：白名单 TLD 才认，自动补 https
function urls(text, options) {
  return collect(text, options).filter(x => x.tag === 'A').map(x => ({ tag: x.tag, text: x.text, href: x.href, cls: x.cls }));
}
check('bare domain linked', urls('去 example.com 看看'), [
  { tag: 'A', text: 'example.com', href: 'https://example.com', cls: 'chat-link' },
]);
check('bare domain with path', urls('打开 example.com/play?a=1 哦'), [
  { tag: 'A', text: 'example.com/play?a=1', href: 'https://example.com/play?a=1', cls: 'chat-link' },
]);
check('www always linked', urls('看 www.wikipedia.org 谢谢'), [
  { tag: 'A', text: 'www.wikipedia.org', href: 'https://www.wikipedia.org', cls: 'chat-link' },
]);

// 10. 裸域名误报防护
check('short tld rejected', urls('b.c 和 a.b 不算'), []);
check('version numbers rejected', urls('版本 v1.2 和 3.5寸 屏'), []);
check('filename rejected', urls('下载 setup.exe 文件'), []);
check('email not linked', urls('邮件发我 a@example.com 即可'), []);
check('chinese sentence safe', urls('今天天气不错。_multiple.random'), []);
check('unknown tld rejected', urls('去 example.xyzzy 看看'), []);
check('known tld accepted', urls('去 example.games 吧'), [
  { tag: 'A', text: 'example.games', href: 'https://example.games', cls: 'chat-link' },
]);

// 11. 带协议仍优先，且不再二次匹配裸域名正则
check('schematic url unchanged', urls('https://example.com 好的'), [
  { tag: 'A', text: 'https://example.com', href: 'https://example.com', cls: 'chat-link' },
]);
check('protocol url keeps original text', urls('http://example.com'), [
  { tag: 'A', text: 'http://example.com', href: 'http://example.com', cls: 'chat-link' },
]);

// 12. 混合：带协议 + 纯文本里的裸域名
check('mixed schematic and bare', urls('a https://a.com b example.org c'), [
  { tag: 'A', text: 'https://a.com', href: 'https://a.com', cls: 'chat-link' },
  { tag: 'A', text: 'example.org', href: 'https://example.org', cls: 'chat-link' },
]);

// 13. 站内裸域名不需要确认（internalAllowed 认裸域）
expect('bare internal allowed', links.internalAllowed('gtn.stickerbug.top'), true);
expect('bare external blocked', links.internalAllowed('evil.com'), false);
expect('bare lookalike blocked', links.internalAllowed('stickerbug.top.evil.com'), false);

// 14. 纯文本段不误伤：数字.数字.数字.数字（IP 形态不在 TLD 白名单，不识别）
check('ipv4 not linked by bare rule', urls('服务器 192.168.1.1:5000 联机'), []);

if (failures > 0) {
  console.error(`${failures} FAILURES`);
  process.exit(1);
}
console.log('all chat link tests passed');

process.exit(failures > 0 ? 1 : 0);
