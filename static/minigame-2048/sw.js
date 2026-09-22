/* 休闲花园 · 2048 的**局部**离线缓存。

   只缓存这一页需要的静态资源（页面外壳 / CSS / JS / 字体 / 图标）：
   不缓存登录响应、令牌、账号资料、管理页面、奖励接口，也不接管 GTN 的其他页面。
   接口请求一律直连网络：断网时由页面自己显示"离线，本地已保存"，
   收到真实 401/403 时页面走身份/权限处理——**不会**拿缓存假装成功。

   注意：页面是 ES module，`minigame_2048_core.js` 必须一起缓存，否则断网时
   整段脚本都跑不起来（棋盘、合成顺序、排行榜全空）。所以这里不再逐个写死文件名，
   而是覆盖这一页会用到的静态资源类型，避免以后新加文件又漏。 */

const CACHE = 'gtn-mg2048-v2';
const SHELL = [
  '/minigame/2048',
  '/static/css/minigame_2048.css',
  '/static/css/shared-lobby-chat.css',
  '/static/js/minigame_2048.js',
  '/static/js/minigame_2048_core.js',
  '/static/assets/favicon.ico',
];

/* 页面会用到的静态资源类型（script/style/字体/图片等） */
const ASSET_DESTINATIONS = new Set(['script', 'style', 'image', 'font', 'manifest']);

/* 统一按"路径"存与取：带 ?v= 的资源在线时永远拿新版，离线时用最近一次存下的那份，
   不会因为版本串不同而在缓存里留一堆过期副本。 */
const cacheKeyFor = (request) => {
  const url = new URL(request.url);
  return new Request(`${url.origin}${url.pathname}`, { method: 'GET' });
};

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all(SHELL.map(async (path) => {
      try {
        const response = await fetch(path, { credentials: 'same-origin' });
        if (response.ok) {
          await cache.put(new Request(`${self.location.origin}${path}`, { method: 'GET' }), response.clone());
        }
      } catch (_) { /* 首次就离线：能缓存多少算多少 */ }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // 接口直连：离线时交给页面处理，绝不返回缓存伪造成功
  if (url.pathname.startsWith('/api/')) return;
  const isShell = url.pathname === '/minigame/2048';
  const isAsset = url.pathname.startsWith('/static/')
    || url.pathname.startsWith('/fonts/')
    || ASSET_DESTINATIONS.has(request.destination);
  if (!isShell && !isAsset) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const key = cacheKeyFor(request);
    try {
      const response = await fetch(request, { credentials: 'same-origin' });
      if (response.ok) cache.put(key, response.clone());
      return response;                       // 联网优先：身份变化立刻生效
    } catch (error) {
      const cached = await cache.match(key, { ignoreSearch: true });
      if (cached) return cached;
      throw error;
    }
  })());
});
