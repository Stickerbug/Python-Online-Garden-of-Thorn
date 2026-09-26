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

if (failures > 0) {
  console.error(`${failures} FAILURES`);
  process.exit(1);
}
console.log('all chat link tests passed');

process.exit(failures > 0 ? 1 : 0);
